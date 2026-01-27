"""
BORAK - Ollama Chat Service
FastAPI Backend with SSE Streaming
"""
import os
import io
import json
import sqlite3
import bcrypt
import base64
import re
import threading
import asyncio
import zipfile
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Response, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import JWTError, jwt

# Local imports
from sandbox import run_sandboxed_python, generate_html_preview, ExecutionResult

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
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
IMAGE_RETENTION_DAYS = int(os.environ.get("IMAGE_RETENTION_DAYS", "1"))  # Auto-delete after 1 day
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen3-coder:30b")
VISION_MODELS = ["deepseek-ocr", "qwen3-vl", "llava", "moondream", "bakllava", "llava-phi", "granite3.2-vision", "minicpm-v"]
TRANSLATION_MODELS = ["translategemma", "nllb", "mbart", "seamless"]

# Model metadata for UI display and tender automation routing
MODEL_METADATA = {
    "qwen3-coder:30b": {
        "name": "Qwen3 Coder 30B",
        "origin": "🇨🇳",
        "size": "18GB",
        "category": "coding",
        "description": "Technical proposal writing, methodology, architecture diagrams",
        "tender_stages": ["compose-technical"],
        "tags": ["code", "technical", "heavy"]
    },
    "qwen2.5-coder:7b": {
        "name": "Qwen2.5 Coder 7B",
        "origin": "🇨🇳",
        "size": "4.7GB",
        "category": "coding",
        "description": "Browser automation, portal navigation, form filling, data extraction",
        "tender_stages": ["scout", "submit", "extract"],
        "tags": ["fast", "tools", "browser"]
    },
    "gemma2:9b": {
        "name": "Gemma 2 9B",
        "origin": "🇺🇸",
        "size": "5.4GB",
        "category": "analysis",
        "description": "Tender qualification, compliance scoring, structured analysis",
        "tender_stages": ["analyze", "review"],
        "tags": ["analysis", "structured", "reasoning"]
    },
    "mistral-nemo": {
        "name": "Mistral Nemo 12B",
        "origin": "🇫🇷",
        "size": "7.1GB",
        "category": "writing",
        "description": "Formal bid documents, executive summaries, cover letters",
        "tender_stages": ["compose-formal", "review"],
        "tags": ["formal", "concise", "professional"]
    },
    "deepseek-ocr": {
        "name": "DeepSeek OCR",
        "origin": "🇨🇳",
        "size": "6.7GB",
        "category": "vision",
        "description": "Scanned document OCR, image-based tender extraction",
        "tender_stages": ["extract-vision"],
        "tags": ["vision", "ocr", "documents"]
    },
    "guardpoint": {
        "name": "Guardpoint Medical",
        "origin": "🇨🇳",
        "size": "15GB",
        "category": "specialist",
        "description": "Healthcare/medical tender analysis, clinical reasoning",
        "tender_stages": ["analyze-medical"],
        "tags": ["medical", "specialist", "reasoning"]
    },
    "translategemma": {
        "name": "TranslateGemma",
        "origin": "🇺🇸",
        "size": "3.3GB",
        "category": "translation",
        "description": "Multi-language tender document translation",
        "tender_stages": ["translate"],
        "tags": ["translation", "multilingual"]
    }
}

# JWT Settings
SECRET_KEY = os.environ.get("SECRET_KEY", "borak-secret-key-change-in-production-" + str(hash(DATA_DIR)))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Ensure directories exist
Path(STREAM_CACHE_DIR).mkdir(exist_ok=True)
Path(DATA_DIR).mkdir(exist_ok=True)
Path(UPLOADS_DIR).mkdir(exist_ok=True)

# Active generations tracking for stop functionality
# Key: "{user_id}_{session_id}", Value: {"cancel": asyncio.Event, "content": str, "msg_id": int}
active_generations: Dict[str, dict] = {}

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
    session_id: Optional[int] = None
    images: Optional[List[str]] = None  # Base64 encoded images


class SessionCreate(BaseModel):
    name: Optional[str] = "New Chat"


class SessionUpdate(BaseModel):
    name: str


class StopRequest(BaseModel):
    session_id: int


class ContinueRequest(BaseModel):
    session_id: int
    model: str


class ExecutionRequest(BaseModel):
    code: str
    language: str = "python"
    timeout_seconds: int = 30
    artifact_id: Optional[int] = None


class PreviewRequest(BaseModel):
    html: str
    css: Optional[str] = None
    javascript: Optional[str] = None
    artifact_id: Optional[int] = None


class SystemPromptUpdate(BaseModel):
    system_prompt: Optional[str] = None
    system_prompt_enabled: bool = True
    model_prompts: Optional[Dict[str, str]] = None


# System prompt presets
SYSTEM_PROMPT_PRESETS = [
    {"id": "none", "name": "Default (none)", "prompt": None},
    {"id": "helpful", "name": "Helpful Assistant", "prompt": "You are a helpful, harmless, and honest AI assistant. Provide clear, accurate, and thoughtful responses."},
    {"id": "coder", "name": "Code Expert", "prompt": "You are an expert programmer. Provide clean, efficient, and well-documented code. Explain your reasoning and suggest best practices."},
    {"id": "concise", "name": "Concise", "prompt": "Be brief and to the point. Provide short, direct answers without unnecessary elaboration."},
    {"id": "creative", "name": "Creative Writer", "prompt": "You are a creative writing assistant. Help with storytelling, poetry, and creative content with vivid language and imagination."},
]

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

    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT,
                  created_at TEXT, last_login TEXT, is_admin INTEGER DEFAULT 0)''')

    # Chat sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  name TEXT NOT NULL DEFAULT 'New Chat',
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_sessions_user
                 ON chat_sessions(user_id, updated_at DESC)''')

    # Chat history table (with session support)
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY, user_id INTEGER, role TEXT, content TEXT,
                  model TEXT, created_at TEXT, session_id INTEGER, is_partial INTEGER DEFAULT 0,
                  FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE)''')

    # Artifacts table (legacy - session-bound)
    c.execute('''CREATE TABLE IF NOT EXISTS artifacts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id INTEGER NOT NULL,
                  user_id INTEGER NOT NULL,
                  type TEXT NOT NULL,
                  language TEXT,
                  title TEXT,
                  content TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_artifacts_session
                 ON artifacts(session_id)''')

    # User artifacts table (persistent, user-level, not session-bound)
    c.execute('''CREATE TABLE IF NOT EXISTS user_artifacts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  type TEXT NOT NULL,
                  language TEXT,
                  title TEXT,
                  content TEXT NOT NULL,
                  source_session_id INTEGER,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_user_artifacts_user
                 ON user_artifacts(user_id, created_at DESC)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_user_artifacts_type
                 ON user_artifacts(user_id, type)''')

    # Usage log table
    c.execute('''CREATE TABLE IF NOT EXISTS usage_log
                 (id INTEGER PRIMARY KEY, user_id INTEGER, model TEXT,
                  tokens_in INTEGER, tokens_out INTEGER, created_at TEXT)''')

    # Message attachments table (time-bound image storage)
    c.execute('''CREATE TABLE IF NOT EXISTS message_attachments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  message_id INTEGER,
                  user_id INTEGER NOT NULL,
                  filename TEXT NOT NULL,
                  original_name TEXT,
                  mime_type TEXT,
                  file_size INTEGER,
                  created_at TEXT NOT NULL,
                  expires_at TEXT NOT NULL,
                  FOREIGN KEY (message_id) REFERENCES chat_history(id) ON DELETE SET NULL,
                  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_attachments_message
                 ON message_attachments(message_id)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_attachments_expires
                 ON message_attachments(expires_at)''')

    # Code executions table
    c.execute('''CREATE TABLE IF NOT EXISTS code_executions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  artifact_id INTEGER,
                  language TEXT NOT NULL,
                  code TEXT NOT NULL,
                  status TEXT NOT NULL,
                  stdout TEXT,
                  stderr TEXT,
                  exit_code INTEGER,
                  execution_time_ms INTEGER,
                  created_at TEXT NOT NULL,
                  completed_at TEXT,
                  preview_html TEXT,
                  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                  FOREIGN KEY (artifact_id) REFERENCES user_artifacts(id) ON DELETE SET NULL)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_executions_user
                 ON code_executions(user_id, created_at DESC)''')

    # User settings table (system prompts, preferences)
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL UNIQUE,
                  system_prompt TEXT,
                  system_prompt_enabled INTEGER DEFAULT 1,
                  model_prompts TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)''')

    conn.commit()

    # Run migrations for existing data
    migrate_db(conn)
    conn.close()


def migrate_db(conn):
    """Handle database migrations for schema changes."""
    c = conn.cursor()

    # Check if session_id column exists in chat_history
    c.execute("PRAGMA table_info(chat_history)")
    columns = [col[1] for col in c.fetchall()]

    if 'session_id' not in columns:
        # Add session_id column
        c.execute("ALTER TABLE chat_history ADD COLUMN session_id INTEGER")
        c.execute("ALTER TABLE chat_history ADD COLUMN is_partial INTEGER DEFAULT 0")

        # Create default sessions for users with existing messages
        c.execute("SELECT DISTINCT user_id FROM chat_history WHERE session_id IS NULL")
        users_with_messages = c.fetchall()

        now = datetime.now().isoformat()
        for (user_id,) in users_with_messages:
            # Create a default session for each user
            c.execute(
                "INSERT INTO chat_sessions (user_id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, "Previous Chat", now, now)
            )
            session_id = c.lastrowid

            # Update all messages for this user to use the new session
            c.execute(
                "UPDATE chat_history SET session_id = ? WHERE user_id = ? AND session_id IS NULL",
                (session_id, user_id)
            )

        conn.commit()

    # Migration: Copy artifacts to user_artifacts and rename explanation -> document
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_artifacts'")
    if c.fetchone():
        # Check if migration already done by looking for any user_artifacts
        c.execute("SELECT COUNT(*) FROM user_artifacts")
        if c.fetchone()[0] == 0:
            # Copy existing artifacts to user_artifacts, renaming explanation -> document
            c.execute("""
                INSERT INTO user_artifacts (user_id, type, language, title, content, source_session_id, created_at)
                SELECT user_id,
                       CASE WHEN type = 'explanation' THEN 'document' ELSE type END,
                       language, title, content, session_id, created_at
                FROM artifacts
            """)
            conn.commit()

    # Update any remaining 'explanation' types to 'document' in both tables
    c.execute("UPDATE artifacts SET type = 'document' WHERE type = 'explanation'")
    c.execute("UPDATE user_artifacts SET type = 'document' WHERE type = 'explanation'")
    conn.commit()


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


def get_user_settings(user_id: int) -> dict:
    """Get user settings, returning defaults if none exist."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT system_prompt, system_prompt_enabled, model_prompts FROM user_settings WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()

    if result:
        return {
            "system_prompt": result["system_prompt"],
            "system_prompt_enabled": bool(result["system_prompt_enabled"]),
            "model_prompts": json.loads(result["model_prompts"]) if result["model_prompts"] else {}
        }

    # Return defaults
    return {
        "system_prompt": None,
        "system_prompt_enabled": True,
        "model_prompts": {}
    }


def update_user_settings(user_id: int, settings: dict) -> bool:
    """Upsert user settings."""
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()

    # Enforce 4000 char limit on system prompt
    system_prompt = settings.get("system_prompt")
    if system_prompt and len(system_prompt) > 4000:
        system_prompt = system_prompt[:4000]

    model_prompts = settings.get("model_prompts", {})
    # Enforce limit on model-specific prompts too
    for key in model_prompts:
        if model_prompts[key] and len(model_prompts[key]) > 4000:
            model_prompts[key] = model_prompts[key][:4000]

    model_prompts_json = json.dumps(model_prompts) if model_prompts else None

    try:
        # Try insert first
        c.execute(
            """INSERT INTO user_settings (user_id, system_prompt, system_prompt_enabled, model_prompts, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               system_prompt = excluded.system_prompt,
               system_prompt_enabled = excluded.system_prompt_enabled,
               model_prompts = excluded.model_prompts,
               updated_at = excluded.updated_at""",
            (user_id, system_prompt, 1 if settings.get("system_prompt_enabled", True) else 0, model_prompts_json, now, now)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user settings: {e}")
        return False
    finally:
        conn.close()


def get_system_prompt_for_model(user_id: int, model: str) -> Optional[str]:
    """Get the effective system prompt for a user and model."""
    settings = get_user_settings(user_id)

    if not settings.get("system_prompt_enabled", True):
        return None

    # Check for model-specific prompt first
    model_prompts = settings.get("model_prompts", {})
    if model in model_prompts and model_prompts[model]:
        return model_prompts[model]

    # Fall back to global prompt
    return settings.get("system_prompt")


def log_usage(user_id: int, model: str, tokens_in: int, tokens_out: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO usage_log (user_id, model, tokens_in, tokens_out, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, model, tokens_in, tokens_out, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def generate_session_title(content: str, max_length: int = 50) -> str:
    """Generate a session title from the first user message."""
    # Clean up the content
    title = content.strip()

    # Remove common prefixes
    for prefix in ["can you ", "could you ", "please ", "i want to ", "i need to ", "help me "]:
        if title.lower().startswith(prefix):
            title = title[len(prefix):]
            break

    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    # Truncate at sentence boundary if possible
    for end in [". ", "? ", "! ", "\n"]:
        if end in title[:max_length]:
            title = title[:title.index(end) + 1]
            break

    # Final truncation with ellipsis
    if len(title) > max_length:
        title = title[:max_length-3].rsplit(" ", 1)[0] + "..."

    return title or "New Chat"


# =============================================================================
# Attachment Management (Time-bound image storage)
# =============================================================================

import uuid
import hashlib

def save_attachment(user_id: int, base64_data: str, message_id: int = None) -> dict:
    """Save a base64 image to disk and record in DB. Returns attachment info."""
    try:
        # Decode base64
        image_data = base64.b64decode(base64_data)

        # Detect mime type from magic bytes
        mime_type = "image/png"  # default
        if image_data[:3] == b'\xff\xd8\xff':
            mime_type = "image/jpeg"
        elif image_data[:8] == b'\x89PNG\r\n\x1a\n':
            mime_type = "image/png"
        elif image_data[:6] in (b'GIF87a', b'GIF89a'):
            mime_type = "image/gif"
        elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
            mime_type = "image/webp"

        # Generate unique filename
        file_hash = hashlib.md5(image_data[:1024]).hexdigest()[:8]
        ext = mime_type.split("/")[1]
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}_{file_hash}.{ext}"

        # Save to disk
        filepath = os.path.join(UPLOADS_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)

        # Record in database
        now = datetime.now()
        expires_at = now + timedelta(days=IMAGE_RETENTION_DAYS)

        conn = get_db()
        c = conn.cursor()
        c.execute(
            """INSERT INTO message_attachments
               (message_id, user_id, filename, mime_type, file_size, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (message_id, user_id, filename, mime_type, len(image_data),
             now.isoformat(), expires_at.isoformat())
        )
        attachment_id = c.lastrowid
        conn.commit()
        conn.close()

        return {
            "id": attachment_id,
            "filename": filename,
            "mime_type": mime_type,
            "size": len(image_data),
            "expires_at": expires_at.isoformat()
        }
    except Exception as e:
        print(f"Error saving attachment: {e}")
        return None


def get_attachment(attachment_id: int, user_id: int = None):
    """Get attachment info by ID, optionally verify user ownership."""
    conn = get_db()
    c = conn.cursor()

    if user_id:
        c.execute("SELECT * FROM message_attachments WHERE id = ? AND user_id = ?",
                  (attachment_id, user_id))
    else:
        c.execute("SELECT * FROM message_attachments WHERE id = ?", (attachment_id,))

    row = c.fetchone()
    conn.close()

    if not row:
        return None

    # Check if expired
    expires_at = datetime.fromisoformat(row["expires_at"])
    if datetime.now() > expires_at:
        return None

    return dict(row)


def get_message_attachments(message_id: int) -> list:
    """Get all attachments for a message."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """SELECT id, filename, mime_type, file_size, created_at, expires_at
           FROM message_attachments
           WHERE message_id = ? AND expires_at > ?""",
        (message_id, datetime.now().isoformat())
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def link_attachment_to_message(attachment_id: int, message_id: int):
    """Link an attachment to a message after the message is created."""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE message_attachments SET message_id = ? WHERE id = ?",
              (message_id, attachment_id))
    conn.commit()
    conn.close()


def cleanup_expired_attachments():
    """Delete expired attachments from disk and database."""
    conn = get_db()
    c = conn.cursor()

    # Find expired attachments
    c.execute("SELECT id, filename FROM message_attachments WHERE expires_at < ?",
              (datetime.now().isoformat(),))
    expired = c.fetchall()

    deleted_count = 0
    for row in expired:
        # Delete file
        filepath = os.path.join(UPLOADS_DIR, row["filename"])
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting file {filepath}: {e}")

    # Delete from database
    c.execute("DELETE FROM message_attachments WHERE expires_at < ?",
              (datetime.now().isoformat(),))
    conn.commit()
    conn.close()

    if deleted_count > 0:
        print(f"Cleaned up {deleted_count} expired attachments")

    return deleted_count


def save_message(user_id: int, role: str, content: str, model: str, session_id: int = None, is_partial: bool = False):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_history (user_id, role, content, model, created_at, session_id, is_partial) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, role, content, model, datetime.now().isoformat(), session_id, 1 if is_partial else 0)
    )
    msg_id = c.lastrowid

    # Update session's updated_at timestamp
    if session_id:
        c.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                  (datetime.now().isoformat(), session_id))

        # Auto-title session from first user message
        if role == "user":
            c.execute("SELECT name, (SELECT COUNT(*) FROM chat_history WHERE session_id = ?) as msg_count FROM chat_sessions WHERE id = ?",
                      (session_id, session_id))
            row = c.fetchone()
            if row and row["name"] == "New Chat" and row["msg_count"] == 1:
                new_title = generate_session_title(content)
                c.execute("UPDATE chat_sessions SET name = ? WHERE id = ?", (new_title, session_id))

    conn.commit()
    conn.close()
    return msg_id


def update_message(msg_id: int, content: str, is_partial: bool = False):
    """Update an existing message's content."""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE chat_history SET content = ?, is_partial = ? WHERE id = ?",
              (content, 1 if is_partial else 0, msg_id))
    conn.commit()
    conn.close()


def load_chat_history(user_id: int, limit: int = 50, session_id: int = None, include_attachments: bool = False) -> List[dict]:
    conn = get_db()
    c = conn.cursor()
    if session_id:
        c.execute(
            "SELECT id, role, content, model, is_partial FROM chat_history WHERE user_id = ? AND session_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, session_id, limit)
        )
    else:
        c.execute(
            "SELECT id, role, content, model, is_partial FROM chat_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
    rows = c.fetchall()

    messages = []
    for r in reversed(rows):
        msg = {
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "model": r["model"],
            "is_partial": bool(r["is_partial"])
        }

        # Include attachments if requested
        if include_attachments:
            attachments = get_message_attachments(r["id"])
            if attachments:
                msg["attachments"] = [{
                    "id": a["id"],
                    "url": f"/api/attachments/{a['id']}",
                    "download_url": f"/api/attachments/{a['id']}/download",
                    "mime_type": a["mime_type"],
                    "expires_at": a["expires_at"]
                } for a in attachments]

        messages.append(msg)

    conn.close()
    return messages


def clear_chat_history(user_id: int, session_id: int = None):
    conn = get_db()
    c = conn.cursor()
    if session_id:
        c.execute("DELETE FROM chat_history WHERE user_id = ? AND session_id = ?", (user_id, session_id))
        # Also delete artifacts for this session
        c.execute("DELETE FROM artifacts WHERE user_id = ? AND session_id = ?", (user_id, session_id))
    else:
        c.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM artifacts WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    # Also clear from Chroma
    if CHROMA_AVAILABLE:
        try:
            chroma_clear_user(user_id)
        except Exception:
            pass


# =============================================================================
# Session Functions
# =============================================================================

def create_session(user_id: int, name: str = "New Chat") -> int:
    """Create a new chat session and return its ID."""
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute(
        "INSERT INTO chat_sessions (user_id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, name, now, now)
    )
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id


def get_sessions(user_id: int, limit: int = 20, offset: int = 0) -> tuple[List[dict], bool]:
    """Get user's sessions with preview, ordered by most recent."""
    conn = get_db()
    c = conn.cursor()

    # Get sessions
    c.execute(
        """SELECT id, name, created_at, updated_at
           FROM chat_sessions
           WHERE user_id = ?
           ORDER BY updated_at DESC
           LIMIT ? OFFSET ?""",
        (user_id, limit + 1, offset)  # +1 to check if there are more
    )
    rows = c.fetchall()
    has_more = len(rows) > limit
    sessions = []

    for row in rows[:limit]:
        # Get first message as preview
        c.execute(
            """SELECT content FROM chat_history
               WHERE session_id = ? AND role = 'user'
               ORDER BY id ASC LIMIT 1""",
            (row["id"],)
        )
        preview_row = c.fetchone()
        preview = preview_row["content"][:100] + "..." if preview_row and len(preview_row["content"]) > 100 else (preview_row["content"] if preview_row else "")

        # Get message count
        c.execute("SELECT COUNT(*) as count FROM chat_history WHERE session_id = ?", (row["id"],))
        count = c.fetchone()["count"]

        sessions.append({
            "id": row["id"],
            "name": row["name"],
            "preview": preview,
            "message_count": count,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        })

    conn.close()
    return sessions, has_more


def get_session(user_id: int, session_id: int) -> Optional[dict]:
    """Get a specific session."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, name, created_at, updated_at FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    return None


def rename_session(user_id: int, session_id: int, new_name: str) -> bool:
    """Rename a session."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE chat_sessions SET name = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (new_name, datetime.now().isoformat(), session_id, user_id)
    )
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_session(user_id: int, session_id: int) -> bool:
    """Delete a session and all its messages and artifacts."""
    conn = get_db()
    c = conn.cursor()

    # Delete artifacts first
    c.execute("DELETE FROM artifacts WHERE session_id = ? AND user_id = ?", (session_id, user_id))
    # Delete messages
    c.execute("DELETE FROM chat_history WHERE session_id = ? AND user_id = ?", (session_id, user_id))
    # Delete session
    c.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
    deleted = c.rowcount > 0

    conn.commit()
    conn.close()
    return deleted


def get_or_create_active_session(user_id: int) -> int:
    """Get most recent session or create a new one."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1",
        (user_id,)
    )
    row = c.fetchone()
    conn.close()

    if row:
        return row["id"]
    return create_session(user_id)


# =============================================================================
# Artifact Functions
# =============================================================================

def save_artifact(session_id: int, user_id: int, artifact_type: str, content: str,
                  language: str = None, title: str = None) -> int:
    """Save an artifact to both session-bound and user-level tables."""
    now = datetime.now().isoformat()
    conn = get_db()
    c = conn.cursor()

    # Save to session-bound artifacts (legacy)
    c.execute(
        """INSERT INTO artifacts (session_id, user_id, type, language, title, content, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (session_id, user_id, artifact_type, language, title, content, now)
    )
    artifact_id = c.lastrowid

    # Also save to user-level persistent artifacts
    c.execute(
        """INSERT INTO user_artifacts (user_id, type, language, title, content, source_session_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, artifact_type, language, title, content, session_id, now)
    )

    conn.commit()
    conn.close()
    return artifact_id


def get_artifacts(session_id: int, user_id: int) -> dict:
    """Get artifacts for a session, grouped by type."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """SELECT id, type, language, title, content, created_at
           FROM artifacts
           WHERE session_id = ? AND user_id = ?
           ORDER BY created_at ASC""",
        (session_id, user_id)
    )
    rows = c.fetchall()
    conn.close()

    grouped = {"code": [], "thought": [], "document": []}
    for row in rows:
        item = {
            "id": row["id"],
            "language": row["language"],
            "title": row["title"],
            "content": row["content"],
            "created_at": row["created_at"]
        }
        artifact_type = row["type"]
        # Handle legacy "explanation" type
        if artifact_type == "explanation":
            artifact_type = "document"
        if artifact_type in grouped:
            grouped[artifact_type].append(item)

    return grouped


def get_user_artifacts(user_id: int, artifact_type: str = None) -> dict:
    """Get all persistent artifacts for a user, optionally filtered by type."""
    conn = get_db()
    c = conn.cursor()

    if artifact_type:
        c.execute(
            """SELECT id, type, language, title, content, source_session_id, created_at
               FROM user_artifacts
               WHERE user_id = ? AND type = ?
               ORDER BY created_at DESC""",
            (user_id, artifact_type)
        )
    else:
        c.execute(
            """SELECT id, type, language, title, content, source_session_id, created_at
               FROM user_artifacts
               WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,)
        )
    rows = c.fetchall()
    conn.close()

    grouped = {"code": [], "thought": [], "document": []}
    for row in rows:
        item = {
            "id": row["id"],
            "language": row["language"],
            "title": row["title"],
            "content": row["content"],
            "source_session_id": row["source_session_id"],
            "created_at": row["created_at"]
        }
        atype = row["type"]
        if atype == "explanation":
            atype = "document"
        if atype in grouped:
            grouped[atype].append(item)

    return grouped


def delete_user_artifact(artifact_id: int, user_id: int) -> bool:
    """Delete a user artifact by ID."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "DELETE FROM user_artifacts WHERE id = ? AND user_id = ?",
        (artifact_id, user_id)
    )
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_artifact(artifact_id: int, user_id: int) -> Optional[dict]:
    """Get a single artifact by ID."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, type, language, title, content, created_at FROM artifacts WHERE id = ? AND user_id = ?",
        (artifact_id, user_id)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "type": row["type"],
            "language": row["language"],
            "title": row["title"],
            "content": row["content"],
            "created_at": row["created_at"]
        }
    return None


# =============================================================================
# Code Execution Functions
# =============================================================================

def create_execution(user_id: int, language: str, code: str, artifact_id: int = None) -> int:
    """Create a new execution record and return its ID."""
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute(
        """INSERT INTO code_executions
           (user_id, artifact_id, language, code, status, created_at)
           VALUES (?, ?, ?, ?, 'pending', ?)""",
        (user_id, artifact_id, language, code, now)
    )
    execution_id = c.lastrowid
    conn.commit()
    conn.close()
    return execution_id


def update_execution(execution_id: int, status: str, stdout: str = None,
                     stderr: str = None, exit_code: int = None,
                     execution_time_ms: int = None, preview_html: str = None):
    """Update an execution record with results."""
    conn = get_db()
    c = conn.cursor()
    completed_at = datetime.now().isoformat() if status in ('completed', 'failed', 'timeout') else None
    c.execute(
        """UPDATE code_executions SET
           status = ?, stdout = ?, stderr = ?, exit_code = ?,
           execution_time_ms = ?, completed_at = ?, preview_html = ?
           WHERE id = ?""",
        (status, stdout, stderr, exit_code, execution_time_ms, completed_at, preview_html, execution_id)
    )
    conn.commit()
    conn.close()


def get_execution(execution_id: int, user_id: int) -> Optional[dict]:
    """Get a single execution by ID."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """SELECT id, user_id, artifact_id, language, code, status,
                  stdout, stderr, exit_code, execution_time_ms,
                  created_at, completed_at, preview_html
           FROM code_executions WHERE id = ? AND user_id = ?""",
        (execution_id, user_id)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_executions_history(user_id: int, limit: int = 20) -> List[dict]:
    """Get execution history for a user."""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """SELECT id, artifact_id, language, status, exit_code,
                  execution_time_ms, created_at, completed_at
           FROM code_executions
           WHERE user_id = ?
           ORDER BY created_at DESC
           LIMIT ?""",
        (user_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

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
    # Cleanup expired attachments on startup
    cleanup_expired_attachments()
    yield
    # Shutdown - final cleanup
    cleanup_expired_attachments()

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
        secure=False,  # Set True for HTTPS/production
        path="/",     # Ensure cookie is sent for all paths
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
    # Enrich with metadata
    models_with_meta = []
    for model in models:
        # Match by prefix (e.g., "qwen3-coder:30b" or "qwen3-coder")
        base_name = model.split(":")[0] if ":" in model else model
        meta = MODEL_METADATA.get(model) or MODEL_METADATA.get(base_name) or {
            "name": model,
            "origin": "🌐",
            "size": "unknown",
            "category": "general",
            "description": "",
            "tender_stages": [],
            "tags": []
        }
        models_with_meta.append({
            "id": model,
            **meta
        })
    return {
        "models": models,
        "models_meta": models_with_meta,
        "default": DEFAULT_MODEL,
        "vision_models": VISION_MODELS,
        "translation_models": TRANSLATION_MODELS,
        "model_metadata": MODEL_METADATA
    }

# =============================================================================
# Session Routes
# =============================================================================

@app.post("/api/sessions")
async def api_create_session(session: SessionCreate, user_id: int = Depends(get_current_user)):
    """Create a new chat session."""
    session_id = create_session(user_id, session.name)
    return {"success": True, "session_id": session_id}


@app.get("/api/sessions")
async def api_list_sessions(
    limit: int = 20,
    offset: int = 0,
    user_id: int = Depends(get_current_user)
):
    """List user's chat sessions with previews."""
    sessions, has_more = get_sessions(user_id, limit, offset)
    return {"sessions": sessions, "has_more": has_more}


@app.get("/api/sessions/{session_id}")
async def api_get_session(session_id: int, user_id: int = Depends(get_current_user)):
    """Get a specific session."""
    session = get_session(user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.patch("/api/sessions/{session_id}")
async def api_update_session(
    session_id: int,
    update: SessionUpdate,
    user_id: int = Depends(get_current_user)
):
    """Rename a session."""
    success = rename_session(user_id, session_id, update.name)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}


@app.delete("/api/sessions/{session_id}")
async def api_delete_session(session_id: int, user_id: int = Depends(get_current_user)):
    """Delete a session and all its messages."""
    success = delete_session(user_id, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}


# =============================================================================
# Chat Routes
# =============================================================================

@app.get("/api/chat/history")
async def api_chat_history(
    session_id: Optional[int] = None,
    user_id: int = Depends(get_current_user)
):
    """Get chat history for a session, including image attachments."""
    messages = load_chat_history(user_id, limit=50, session_id=session_id, include_attachments=True)

    # Get the last used model for this session (from most recent message)
    last_model = None
    if messages:
        # Find the last message that has a model (user messages have the model they were sent with)
        for msg in reversed(messages):
            if msg.get("model"):
                last_model = msg["model"]
                break

    return {"messages": messages, "last_model": last_model}


@app.delete("/api/chat/clear")
async def api_clear_chat(
    session_id: Optional[int] = None,
    user_id: int = Depends(get_current_user)
):
    """Clear chat history for a session."""
    clear_chat_history(user_id, session_id)
    clear_generation(user_id)
    return {"success": True}


def extract_code_title(code: str, lang: str) -> str:
    """Extract a meaningful title from code content."""
    lines = code.strip().split('\n')
    if not lines:
        return f"{lang.capitalize()} Code"

    first_line = lines[0].strip()

    # Check for comment-based titles at the start
    comment_patterns = [
        # Single-line comments: # Title, // Title, -- Title
        (r'^#\s*(.+)$', ['python', 'ruby', 'bash', 'shell', 'yaml', 'yml']),
        (r'^//\s*(.+)$', ['javascript', 'typescript', 'java', 'c', 'cpp', 'go', 'rust', 'swift', 'kotlin']),
        (r'^--\s*(.+)$', ['sql', 'lua', 'haskell']),
        # Block comment start: /* Title */ or /** Title */
        (r'^/\*+\s*(.+?)\s*\*?/?$', ['javascript', 'typescript', 'java', 'c', 'cpp', 'css']),
        # HTML/XML comment: <!-- Title -->
        (r'^<!--\s*(.+?)\s*-->$', ['html', 'xml', 'svg']),
        # Shebang with description: #!/usr/bin/env python - Title
        (r'^#!.+?[-–]\s*(.+)$', ['python', 'bash', 'shell']),
    ]

    for pattern, langs in comment_patterns:
        if lang.lower() in langs or not langs:
            match = re.match(pattern, first_line)
            if match:
                title = match.group(1).strip()
                # Clean up common prefixes
                title = re.sub(r'^(file|filename|name|title):\s*', '', title, flags=re.IGNORECASE)
                if title and len(title) > 2 and len(title) < 100:
                    return title

    # Check for function/class definitions
    def_patterns = [
        (r'^(?:async\s+)?def\s+(\w+)', 'function'),  # Python
        (r'^(?:async\s+)?function\s+(\w+)', 'function'),  # JavaScript
        (r'^(?:export\s+)?(?:async\s+)?(?:const|let|var)\s+(\w+)\s*=', 'variable'),  # JS const/let
        (r'^class\s+(\w+)', 'class'),  # Python/JS class
        (r'^(?:public|private|protected)?\s*(?:static\s+)?(?:class|interface)\s+(\w+)', 'class'),  # Java/TS
        (r'^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)', 'function'),  # Rust
        (r'^func\s+(\w+)', 'function'),  # Go
        (r'^(?:export\s+)?(?:default\s+)?(?:const|function)\s+(\w+)', 'component'),  # React
    ]

    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        for pattern, kind in def_patterns:
            match = re.match(pattern, line)
            if match:
                name = match.group(1)
                if name and name not in ('main', 'init', 'constructor', '__init__'):
                    return f"{name} ({kind})"

    # Check if there's a filename pattern in context before the code block
    # Fallback to language-based title
    return f"{lang.capitalize()} Code"


def extract_artifacts_from_response(content: str) -> List[dict]:
    """Extract code blocks, thoughts, and explanations from response."""
    artifacts = []

    # Extract code blocks
    code_pattern = r'```(\w+)?\n([\s\S]*?)```'
    for match in re.finditer(code_pattern, content):
        lang = match.group(1) or 'text'
        code = match.group(2).strip()
        if code:
            title = extract_code_title(code, lang)
            artifacts.append({
                "type": "code",
                "language": lang,
                "title": title,
                "content": code
            })

    # Extract thinking blocks
    think_pattern = r'<think>([\s\S]*?)</think>'
    for match in re.finditer(think_pattern, content):
        thought = match.group(1).strip()
        if thought:
            artifacts.append({
                "type": "thought",
                "language": None,
                "title": "Reasoning",
                "content": thought
            })

    # Extract markdown sections as documents (headers with 50+ char content)
    section_pattern = r'^##\s+(.+?)\n([\s\S]*?)(?=^##|\Z)'
    for match in re.finditer(section_pattern, content, re.MULTILINE):
        title = match.group(1).strip()
        body = match.group(2).strip()
        # Only include substantial sections
        if len(body) >= 50 and not body.startswith('```'):
            artifacts.append({
                "type": "document",
                "language": None,
                "title": title,
                "content": body
            })

    return artifacts


@app.post("/api/chat/send")
async def api_chat_send(chat: ChatRequest, user_id: int = Depends(get_current_user)):
    """Send a message and get a streaming response via SSE."""
    # Get or create session
    session_id = chat.session_id
    if not session_id:
        session_id = create_session(user_id)

    # Save images first (time-bound storage)
    attachment_ids = []
    if chat.images:
        for img_base64 in chat.images:
            attachment = save_attachment(user_id, img_base64)
            if attachment:
                attachment_ids.append(attachment["id"])

    # Save user message
    msg_id = save_message(user_id, "user", chat.message, chat.model, session_id)
    chroma_save_message(user_id, "user", chat.message, chat.model)

    # Link attachments to the message
    for att_id in attachment_ids:
        link_attachment_to_message(att_id, msg_id)

    # Get chat history for context
    history = load_chat_history(user_id, limit=20, session_id=session_id)

    # Build messages for Ollama (only role and content)
    messages = [{"role": m["role"], "content": m["content"]} for m in history]

    # If vision model with images, add to last message
    if chat.images and is_vision_model(chat.model):
        messages[-1]["images"] = chat.images

    # Track this generation for stop functionality
    gen_key = f"{user_id}_{session_id}"
    cancel_event = asyncio.Event()
    active_generations[gen_key] = {
        "cancel": cancel_event,
        "content": "",
        "msg_id": None
    }

    async def generate_stream():
        full_response = ""
        prompt_tokens = 0
        completion_tokens = 0
        msg_id = None

        # First event: session info
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        try:
            payload = {"model": chat.model, "messages": messages, "stream": True}

            # Add system prompt if configured
            system_prompt = get_system_prompt_for_model(user_id, chat.model)
            if system_prompt:
                payload["system"] = system_prompt

            async with httpx.AsyncClient(timeout=600) as client:
                async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            # Check for cancellation
                            if cancel_event.is_set():
                                # Save partial response
                                if full_response:
                                    msg_id = save_message(
                                        user_id, "assistant", full_response, chat.model,
                                        session_id, is_partial=True
                                    )
                                    active_generations[gen_key]["msg_id"] = msg_id
                                yield f"data: {json.dumps({'type': 'stopped', 'partial': True})}\n\n"
                                return

                            if line:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    full_response += content
                                    active_generations[gen_key]["content"] = full_response
                                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                                if chunk.get("done"):
                                    prompt_tokens = chunk.get("prompt_eval_count", 0)
                                    completion_tokens = chunk.get("eval_count", 0)
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'error': f'HTTP {response.status_code}'})}\n\n"
                        return
        except asyncio.CancelledError:
            # Save partial on cancellation
            if full_response:
                save_message(user_id, "assistant", full_response, chat.model, session_id, is_partial=True)
            yield f"data: {json.dumps({'type': 'stopped', 'partial': True})}\n\n"
            return
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            return
        finally:
            # Clean up tracking
            if gen_key in active_generations:
                del active_generations[gen_key]

        # Save complete assistant response
        if full_response:
            msg_id = save_message(user_id, "assistant", full_response, chat.model, session_id)
            chroma_save_message(user_id, "assistant", full_response, chat.model)
            log_usage(user_id, chat.model, prompt_tokens, completion_tokens)

            # Extract and save artifacts
            artifacts = extract_artifacts_from_response(full_response)
            artifact_counts = {"code": 0, "thought": 0, "document": 0}
            for artifact in artifacts:
                save_artifact(
                    session_id, user_id, artifact["type"],
                    artifact["content"], artifact["language"], artifact["title"]
                )
                artifact_counts[artifact["type"]] += 1

            yield f"data: {json.dumps({'type': 'done', 'usage': {'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens}, 'artifacts': artifact_counts})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'done', 'usage': {'prompt_tokens': 0, 'completion_tokens': 0}})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/chat/stop")
async def api_chat_stop(stop: StopRequest, user_id: int = Depends(get_current_user)):
    """Stop an active generation."""
    gen_key = f"{user_id}_{stop.session_id}"
    if gen_key in active_generations:
        active_generations[gen_key]["cancel"].set()
        return {
            "success": True,
            "partial_content": active_generations[gen_key].get("content", "")
        }
    return {"success": False, "error": "No active generation"}


@app.post("/api/chat/continue")
async def api_chat_continue(cont: ContinueRequest, user_id: int = Depends(get_current_user)):
    """Continue from a partial response via SSE."""
    session_id = cont.session_id

    # Get the last message (should be partial assistant message)
    history = load_chat_history(user_id, limit=50, session_id=session_id)
    if not history:
        raise HTTPException(status_code=400, detail="No messages to continue from")

    last_msg = history[-1]
    if last_msg["role"] != "assistant" or not last_msg.get("is_partial"):
        raise HTTPException(status_code=400, detail="Last message is not a partial response")

    # Build messages with the partial response as context
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    # Add a continue prompt
    messages.append({"role": "user", "content": "Continue from where you left off."})

    # Track this generation
    gen_key = f"{user_id}_{session_id}"
    cancel_event = asyncio.Event()
    active_generations[gen_key] = {
        "cancel": cancel_event,
        "content": last_msg["content"],
        "msg_id": last_msg["id"]
    }

    async def generate_stream():
        full_response = last_msg["content"]  # Start from partial
        prompt_tokens = 0
        completion_tokens = 0

        try:
            payload = {"model": cont.model, "messages": messages, "stream": True}

            # Add system prompt if configured
            system_prompt = get_system_prompt_for_model(user_id, cont.model)
            if system_prompt:
                payload["system"] = system_prompt

            async with httpx.AsyncClient(timeout=600) as client:
                async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if cancel_event.is_set():
                                # Update partial
                                update_message(last_msg["id"], full_response, is_partial=True)
                                yield f"data: {json.dumps({'type': 'stopped', 'partial': True})}\n\n"
                                return

                            if line:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    full_response += content
                                    active_generations[gen_key]["content"] = full_response
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
        finally:
            if gen_key in active_generations:
                del active_generations[gen_key]

        # Update message to complete (not partial)
        if full_response:
            update_message(last_msg["id"], full_response, is_partial=False)
            log_usage(user_id, cont.model, prompt_tokens, completion_tokens)

            # Extract and save new artifacts
            artifacts = extract_artifacts_from_response(full_response)
            artifact_counts = {"code": 0, "thought": 0, "document": 0}
            for artifact in artifacts:
                save_artifact(
                    session_id, user_id, artifact["type"],
                    artifact["content"], artifact["language"], artifact["title"]
                )
                artifact_counts[artifact["type"]] += 1

            yield f"data: {json.dumps({'type': 'done', 'usage': {'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens}, 'artifacts': artifact_counts})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'done', 'usage': {'prompt_tokens': 0, 'completion_tokens': 0}})}\n\n"

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
# Artifact Routes
# =============================================================================

@app.get("/api/sessions/{session_id}/artifacts")
async def api_get_artifacts(session_id: int, user_id: int = Depends(get_current_user)):
    """Get artifacts for a session, grouped by type."""
    artifacts = get_artifacts(session_id, user_id)
    return artifacts


@app.get("/api/artifacts/{artifact_id}")
async def api_get_artifact(artifact_id: int, user_id: int = Depends(get_current_user)):
    """Get a single artifact."""
    artifact = get_artifact(artifact_id, user_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@app.get("/api/sessions/{session_id}/artifacts/download")
async def api_download_artifacts(session_id: int, user_id: int = Depends(get_current_user)):
    """Download all artifacts for a session as a ZIP file."""
    artifacts = get_artifacts(session_id, user_id)

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for artifact_type, items in artifacts.items():
            folder = artifact_type + "s"  # code -> codes, thought -> thoughts
            for i, item in enumerate(items):
                ext = item.get("language", "txt") or "txt"
                ext_map = {
                    "python": "py", "javascript": "js", "typescript": "ts",
                    "html": "html", "css": "css", "json": "json", "yaml": "yaml",
                    "java": "java", "cpp": "cpp", "c": "c", "go": "go", "rust": "rs"
                }
                ext = ext_map.get(ext, ext)
                filename = f"{folder}/{i+1}_{item.get('title', 'artifact')[:30].replace(' ', '_')}.{ext}"
                zf.writestr(filename, item["content"])

    zip_buffer.seek(0)
    return StreamingResponse(
        iter([zip_buffer.read()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=session_{session_id}_artifacts.zip"}
    )


# =============================================================================
# User Artifacts Routes (Persistent, User-Level)
# =============================================================================

@app.get("/api/user/artifacts")
async def api_get_user_artifacts(
    artifact_type: Optional[str] = None,
    user_id: int = Depends(get_current_user)
):
    """Get all persistent artifacts for a user, optionally filtered by type."""
    artifacts = get_user_artifacts(user_id, artifact_type)
    return artifacts


@app.delete("/api/user/artifacts/{artifact_id}")
async def api_delete_user_artifact(artifact_id: int, user_id: int = Depends(get_current_user)):
    """Delete a persistent user artifact."""
    deleted = delete_user_artifact(artifact_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"success": True}


@app.get("/api/user/artifacts/download")
async def api_download_user_artifacts(user_id: int = Depends(get_current_user)):
    """Download all user artifacts as a ZIP file."""
    artifacts = get_user_artifacts(user_id)

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for artifact_type, items in artifacts.items():
            folder = artifact_type + "s"  # code -> codes, thought -> thoughts, document -> documents
            for i, item in enumerate(items):
                ext = item.get("language", "txt") or "txt"
                ext_map = {
                    "python": "py", "javascript": "js", "typescript": "ts",
                    "markdown": "md", "yaml": "yml", "thought": "md", "document": "md"
                }
                ext = ext_map.get(ext, ext)
                filename = f"{folder}/{i+1}_{item.get('title', 'artifact')[:30].replace(' ', '_')}.{ext}"
                zf.writestr(filename, item["content"])

    zip_buffer.seek(0)
    return StreamingResponse(
        iter([zip_buffer.read()]),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=my_artifacts.zip"}
    )


# =============================================================================
# User Settings Routes
# =============================================================================

@app.get("/api/user/settings")
async def api_get_user_settings(user_id: int = Depends(get_current_user)):
    """Get user settings including system prompt configuration."""
    settings = get_user_settings(user_id)
    return settings


@app.put("/api/user/settings")
async def api_update_user_settings(
    settings: SystemPromptUpdate,
    user_id: int = Depends(get_current_user)
):
    """Update user settings."""
    success = update_user_settings(user_id, {
        "system_prompt": settings.system_prompt,
        "system_prompt_enabled": settings.system_prompt_enabled,
        "model_prompts": settings.model_prompts or {}
    })
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update settings")
    return {"success": True}


@app.get("/api/prompts/presets")
async def api_get_prompt_presets(user_id: int = Depends(get_current_user)):
    """Get available system prompt presets."""
    return {"presets": SYSTEM_PROMPT_PRESETS}


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
# Attachments API (Time-bound image storage)
# =============================================================================

@app.get("/api/attachments/{attachment_id}")
async def api_get_attachment(attachment_id: int, user_id: int = Depends(get_current_user)):
    """Serve an attachment file (image)."""
    attachment = get_attachment(attachment_id, user_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found or expired")

    filepath = os.path.join(UPLOADS_DIR, attachment["filename"])
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        filepath,
        media_type=attachment["mime_type"],
        headers={
            "Cache-Control": "private, max-age=86400",  # Cache for 1 day
            "X-Expires-At": attachment["expires_at"]
        }
    )


@app.get("/api/attachments/{attachment_id}/download")
async def api_download_attachment(attachment_id: int, user_id: int = Depends(get_current_user)):
    """Download an attachment with original filename."""
    attachment = get_attachment(attachment_id, user_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found or expired")

    filepath = os.path.join(UPLOADS_DIR, attachment["filename"])
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    # Use original name or generate one
    download_name = attachment.get("original_name") or f"image_{attachment_id}.{attachment['mime_type'].split('/')[1]}"

    return FileResponse(
        filepath,
        media_type=attachment["mime_type"],
        filename=download_name
    )


# =============================================================================
# Code Execution Routes
# =============================================================================

@app.post("/api/execute/python")
async def api_execute_python(req: ExecutionRequest, user_id: int = Depends(get_current_user)):
    """Execute Python code in a sandboxed environment and stream results via SSE."""
    # Create execution record
    execution_id = create_execution(user_id, req.language, req.code, req.artifact_id)

    async def generate_stream():
        # Emit started event
        yield f"data: {json.dumps({'type': 'started', 'execution_id': execution_id})}\n\n"

        # Update status to running
        update_execution(execution_id, 'running')

        try:
            # Run the code in sandbox
            result = await run_sandboxed_python(
                req.code,
                timeout_seconds=min(req.timeout_seconds, 60)
            )

            # Stream stdout line by line for real-time output
            if result.stdout:
                for line in result.stdout.split('\n'):
                    yield f"data: {json.dumps({'type': 'stdout', 'content': line + chr(10)})}\n\n"

            # Stream stderr
            if result.stderr:
                for line in result.stderr.split('\n'):
                    yield f"data: {json.dumps({'type': 'stderr', 'content': line + chr(10)})}\n\n"

            # Determine final status
            if result.timed_out:
                status = 'timeout'
                yield f"data: {json.dumps({'type': 'timeout', 'execution_time_ms': result.execution_time_ms})}\n\n"
            elif result.exit_code == 0:
                status = 'completed'
            else:
                status = 'failed'

            # Update execution record with results
            update_execution(
                execution_id,
                status=status,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_code,
                execution_time_ms=result.execution_time_ms
            )

            # Emit completed event
            yield f"data: {json.dumps({'type': 'completed', 'exit_code': result.exit_code, 'execution_time_ms': result.execution_time_ms})}\n\n"

        except Exception as e:
            error_msg = str(e)
            update_execution(execution_id, 'failed', stderr=error_msg, exit_code=-1)
            yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/execute/preview")
async def api_create_preview(req: PreviewRequest, user_id: int = Depends(get_current_user)):
    """Generate an HTML preview and store it for viewing."""
    # Generate the preview HTML
    preview_html = generate_html_preview(
        html=req.html,
        css=req.css or '',
        javascript=req.javascript or ''
    )

    # Create execution record for preview
    execution_id = create_execution(
        user_id,
        language='html',
        code=req.html,
        artifact_id=req.artifact_id
    )

    # Update with preview content
    update_execution(
        execution_id,
        status='completed',
        preview_html=preview_html,
        exit_code=0,
        execution_time_ms=0
    )

    return {
        "success": True,
        "execution_id": execution_id,
        "preview_url": f"/api/executions/{execution_id}/preview"
    }


@app.get("/api/executions/{execution_id}/preview")
async def api_get_preview(execution_id: int, user_id: int = Depends(get_current_user)):
    """Serve the HTML preview for an execution."""
    execution = get_execution(execution_id, user_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if not execution.get("preview_html"):
        raise HTTPException(status_code=400, detail="No preview available for this execution")

    return Response(
        content=execution["preview_html"],
        media_type="text/html",
        headers={
            "Content-Security-Policy": "default-src 'self' 'unsafe-inline' data:; script-src 'unsafe-inline'; style-src 'unsafe-inline';",
            "X-Frame-Options": "SAMEORIGIN"
        }
    )


@app.get("/api/executions")
async def api_get_executions(limit: int = 20, user_id: int = Depends(get_current_user)):
    """Get execution history for the user."""
    executions = get_executions_history(user_id, limit)
    return {"executions": executions}


@app.get("/api/executions/{execution_id}")
async def api_get_execution(execution_id: int, user_id: int = Depends(get_current_user)):
    """Get a specific execution record."""
    execution = get_execution(execution_id, user_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


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
