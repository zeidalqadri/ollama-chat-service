"""
BORAK - Ollama Chat Service
FastAPI Backend with SSE Streaming
"""
import os
import json
import sqlite3
import bcrypt
import base64
import re
import threading
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Response, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import JWTError, jwt

# ChromaDB for persistent chat storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

# =============================================================================
# Configuration
# =============================================================================

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DATA_DIR, "users.db")
CHROMA_PATH = os.path.join(DATA_DIR, "chroma_db")
STREAM_CACHE_DIR = os.path.join(DATA_DIR, "stream_cache")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen3-coder:30b")
VISION_MODELS = ["deepseek-ocr", "qwen3-vl", "llava", "moondream", "bakllava", "llava-phi", "granite3.2-vision", "minicpm-v"]

# JWT Settings
SECRET_KEY = os.environ.get("SECRET_KEY", "borak-secret-key-change-in-production-" + str(hash(DATA_DIR)))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Ensure directories exist
Path(STREAM_CACHE_DIR).mkdir(exist_ok=True)
Path(DATA_DIR).mkdir(exist_ok=True)

# =============================================================================
# Pydantic Models
# =============================================================================

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    model: str
    images: Optional[List[str]] = None  # Base64 encoded images

# =============================================================================
# Database Functions
# =============================================================================

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT,
                  created_at TEXT, last_login TEXT, is_admin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY, user_id INTEGER, role TEXT, content TEXT,
                  model TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS usage_log
                 (id INTEGER PRIMARY KEY, user_id INTEGER, model TEXT,
                  tokens_in INTEGER, tokens_out INTEGER, created_at TEXT)''')
    conn.commit()
    conn.close()

def register_user(username: str, password: str) -> tuple[bool, str]:
    conn = get_db()
    c = conn.cursor()
    try:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        c.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                  (username, password_hash, datetime.now().isoformat()))
        conn.commit()
        return True, "Registration successful"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    finally:
        conn.close()

def verify_user(username: str, password: str) -> Optional[int]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and bcrypt.checkpw(password.encode(), result["password_hash"].encode()):
        return result["id"]
    return None

def get_username(user_id: int) -> Optional[str]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result["username"] if result else None

def log_usage(user_id: int, model: str, tokens_in: int, tokens_out: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO usage_log (user_id, model, tokens_in, tokens_out, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, model, tokens_in, tokens_out, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def save_message(user_id: int, role: str, content: str, model: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (user_id, role, content, model, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, role, content, model, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def load_chat_history(user_id: int, limit: int = 50) -> List[dict]:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

def clear_chat_history(user_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    # Also clear from Chroma
    if CHROMA_AVAILABLE:
        try:
            chroma_clear_user(user_id)
        except Exception:
            pass

# =============================================================================
# ChromaDB Functions
# =============================================================================

def get_chroma_client():
    if not CHROMA_AVAILABLE:
        return None
    return chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False)
    )

def get_chat_collection(client):
    if not client:
        return None
    return client.get_or_create_collection(
        name="chat_history",
        metadata={"description": "BORAK chat messages"}
    )

def chroma_save_message(user_id: int, role: str, content: str, model: str, msg_id: str = None):
    if not CHROMA_AVAILABLE or not content:
        return
    try:
        client = get_chroma_client()
        collection = get_chat_collection(client)
        if not collection:
            return
        doc_id = msg_id or f"{user_id}_{role}_{datetime.now().timestamp()}"
        collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[{
                "user_id": str(user_id),
                "role": role,
                "model": model,
                "timestamp": datetime.now().isoformat()
            }]
        )
    except Exception as e:
        print(f"Chroma save error: {e}")

def chroma_load_history(user_id: int, limit: int = 50) -> List[dict]:
    if not CHROMA_AVAILABLE:
        return []
    try:
        client = get_chroma_client()
        collection = get_chat_collection(client)
        if not collection:
            return []
        results = collection.get(
            where={"user_id": str(user_id)},
            limit=limit
        )
        if not results["ids"]:
            return []
        messages = []
        for i, doc_id in enumerate(results["ids"]):
            meta = results["metadatas"][i]
            messages.append({
                "role": meta["role"],
                "content": results["documents"][i],
                "timestamp": meta.get("timestamp", "")
            })
        messages.sort(key=lambda x: x.get("timestamp", ""))
        return [{"role": m["role"], "content": m["content"]} for m in messages]
    except Exception as e:
        print(f"Chroma load error: {e}")
        return []

def chroma_clear_user(user_id: int):
    if not CHROMA_AVAILABLE:
        return
    try:
        client = get_chroma_client()
        collection = get_chat_collection(client)
        if collection:
            results = collection.get(where={"user_id": str(user_id)})
            if results["ids"]:
                collection.delete(ids=results["ids"])
    except Exception as e:
        print(f"Chroma clear error: {e}")

# =============================================================================
# Background Generation (survives connection drops)
# =============================================================================

def get_generation_path(user_id: int) -> str:
    return os.path.join(STREAM_CACHE_DIR, f"gen_{user_id}.json")

def start_background_generation(user_id: int, messages: List[dict], model: str, images: List[str] = None):
    gen_path = get_generation_path(user_id)
    state = {
        "status": "running",
        "content": "",
        "error": None,
        "started": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "usage": None
    }
    with open(gen_path, 'w') as f:
        json.dump(state, f)

    def generate():
        nonlocal state
        try:
            payload = {"model": model, "messages": messages, "stream": True}
            if images and messages and messages[-1]["role"] == "user":
                messages[-1]["images"] = images

            with httpx.Client(timeout=600) as client:
                with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
                    if response.status_code == 200:
                        for line in response.iter_lines():
                            if line:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    state["content"] += content
                                    state["updated"] = datetime.now().isoformat()
                                    with open(gen_path, 'w') as f:
                                        json.dump(state, f)
                                if chunk.get("done"):
                                    state["status"] = "complete"
                                    state["usage"] = {
                                        "prompt_tokens": chunk.get("prompt_eval_count", 0),
                                        "completion_tokens": chunk.get("eval_count", 0)
                                    }
                                    with open(gen_path, 'w') as f:
                                        json.dump(state, f)
                    else:
                        state["status"] = "error"
                        state["error"] = f"HTTP {response.status_code}"
                        with open(gen_path, 'w') as f:
                            json.dump(state, f)
        except Exception as e:
            state["status"] = "error"
            state["error"] = str(e)
            with open(gen_path, 'w') as f:
                json.dump(state, f)

    thread = threading.Thread(target=generate, daemon=True)
    thread.start()
    return gen_path

def get_generation_state(user_id: int) -> Optional[dict]:
    gen_path = get_generation_path(user_id)
    try:
        if os.path.exists(gen_path):
            with open(gen_path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None

def clear_generation(user_id: int):
    gen_path = get_generation_path(user_id)
    try:
        if os.path.exists(gen_path):
            os.remove(gen_path)
    except Exception:
        pass

# =============================================================================
# JWT Authentication
# =============================================================================

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(request: Request) -> int:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

# =============================================================================
# Ollama Functions
# =============================================================================

def get_available_models() -> List[str]:
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                return [m["name"] for m in response.json().get("models", [])]
    except Exception:
        pass
    return [DEFAULT_MODEL]

def is_vision_model(model_name: str) -> bool:
    return any(vm in model_name.lower() for vm in VISION_MODELS)

# =============================================================================
# FastAPI App
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown

app = FastAPI(title="BORAK", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Auth Routes
# =============================================================================

@app.post("/api/auth/register")
async def api_register(user: UserCreate):
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    success, message = register_user(user.username, user.password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}

@app.post("/api/auth/login")
async def api_login(user: UserLogin, response: Response):
    user_id = verify_user(user.username, user.password)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"user_id": user_id, "username": user.username})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="lax"
    )
    return {"success": True, "username": user.username}

@app.post("/api/auth/logout")
async def api_logout(response: Response):
    response.delete_cookie("access_token")
    return {"success": True}

@app.get("/api/auth/me")
async def api_me(user_id: int = Depends(get_current_user)):
    username = get_username(user_id)
    if not username:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user_id, "username": username}

# =============================================================================
# Models Routes
# =============================================================================

@app.get("/api/models")
async def api_models():
    models = get_available_models()
    return {
        "models": models,
        "default": DEFAULT_MODEL,
        "vision_models": VISION_MODELS
    }

# =============================================================================
# Chat Routes
# =============================================================================

@app.get("/api/chat/history")
async def api_chat_history(user_id: int = Depends(get_current_user)):
    # Try Chroma first, fall back to SQLite
    if CHROMA_AVAILABLE:
        messages = chroma_load_history(user_id)
        if messages:
            return {"messages": messages}
    messages = load_chat_history(user_id)
    return {"messages": messages}

@app.delete("/api/chat/clear")
async def api_clear_chat(user_id: int = Depends(get_current_user)):
    clear_chat_history(user_id)
    clear_generation(user_id)
    return {"success": True}

@app.post("/api/chat/send")
async def api_chat_send(chat: ChatRequest, user_id: int = Depends(get_current_user)):
    """Send a message and get a streaming response via SSE."""
    # Save user message
    save_message(user_id, "user", chat.message, chat.model)
    chroma_save_message(user_id, "user", chat.message, chat.model)

    # Get chat history for context
    history = load_chat_history(user_id, limit=20)

    # Add current message
    messages = history + [{"role": "user", "content": chat.message}]

    # If vision model with images, add to last message
    if chat.images and is_vision_model(chat.model):
        messages[-1]["images"] = chat.images

    async def generate_stream():
        full_response = ""
        prompt_tokens = 0
        completion_tokens = 0

        try:
            payload = {"model": chat.model, "messages": messages, "stream": True}

            async with httpx.AsyncClient(timeout=600) as client:
                async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    full_response += content
                                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                                if chunk.get("done"):
                                    prompt_tokens = chunk.get("prompt_eval_count", 0)
                                    completion_tokens = chunk.get("eval_count", 0)
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'error': f'HTTP {response.status_code}'})}\n\n"
                        return
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            return

        # Save assistant response
        if full_response:
            save_message(user_id, "assistant", full_response, chat.model)
            chroma_save_message(user_id, "assistant", full_response, chat.model)
            log_usage(user_id, chat.model, prompt_tokens, completion_tokens)

        yield f"data: {json.dumps({'type': 'done', 'usage': {'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens}})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# =============================================================================
# Background Generation Routes (for recovery)
# =============================================================================

@app.get("/api/chat/generation/status")
async def api_generation_status(user_id: int = Depends(get_current_user)):
    state = get_generation_state(user_id)
    if not state:
        return {"status": "none"}
    return state

@app.delete("/api/chat/generation/clear")
async def api_generation_clear(user_id: int = Depends(get_current_user)):
    clear_generation(user_id)
    return {"success": True}

# =============================================================================
# Static Files & SPA
# =============================================================================

# Mount static directory
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def root():
    index_path = os.path.join(static_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "BORAK API", "docs": "/docs"}

# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "ok", "chroma": CHROMA_AVAILABLE}

# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
