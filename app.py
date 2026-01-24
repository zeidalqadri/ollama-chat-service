import streamlit as st
import requests
import json
import sqlite3
import bcrypt
import os
from datetime import datetime

# Config
OLLAMA_URL = "http://localhost:11434"
DB_PATH = "/opt/ollama-ui/users.db"
DEFAULT_MODEL = "qwen3-coder:30b"

# Database setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
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

def register_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        c.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                  (username, password_hash, datetime.now().isoformat()))
        conn.commit()
        return True, "Registration successful!"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and bcrypt.checkpw(password.encode(), result[1].encode()):
        return result[0]
    return None

def log_usage(user_id, model, tokens_in, tokens_out):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO usage_log (user_id, model, tokens_in, tokens_out, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, model, tokens_in, tokens_out, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_available_models():
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.ok:
            return [m["name"] for m in response.json().get("models", [])]
    except:
        pass
    return [DEFAULT_MODEL]

def chat_with_ollama(messages, model):
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=300
        )
        if response.ok:
            data = response.json()
            return data.get("message", {}).get("content", "No response"), data
        return f"Error: {response.status_code}", None
    except Exception as e:
        return f"Error: {str(e)}", None

# Initialize
init_db()

# Page config
st.set_page_config(page_title="Ollama Chat", page_icon="🤖", layout="wide")

# Session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Auth UI
if not st.session_state.authenticated:
    st.title("🤖 Ollama Chat")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user_id = verify_user(username, password)
                if user_id:
                    st.session_state.authenticated = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Choose username")
            new_password = st.text_input("Choose password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            if st.form_submit_button("Register"):
                if new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    success, msg = register_user(new_username, new_password)
                    if success:
                        st.success(msg + " Please login.")
                    else:
                        st.error(msg)
else:
    # Main chat UI
    st.sidebar.title(f"👤 {st.session_state.username}")
    
    # Model selection
    models = get_available_models()
    selected_model = st.sidebar.selectbox("Model", models, index=0)
    
    # Clear chat
    if st.sidebar.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    
    # Logout
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.messages = []
        st.rerun()
    
    st.title("🤖 Ollama Chat")
    
    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Message..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response, data = chat_with_ollama(st.session_state.messages, selected_model)
                st.markdown(response)
                
                # Log usage
                if data:
                    log_usage(
                        st.session_state.user_id,
                        selected_model,
                        data.get("prompt_eval_count", 0),
                        data.get("eval_count", 0)
                    )
        
        st.session_state.messages.append({"role": "assistant", "content": response})
