import streamlit as st
import requests
import sqlite3
import bcrypt
import os
import base64
import re
from datetime import datetime
from io import BytesIO

# Config
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DATA_DIR, "users.db")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen3-coder:30b")
VISION_MODELS = ["deepseek-ocr", "qwen3-vl", "llava", "moondream", "bakllava", "llava-phi", "granite3.2-vision", "minicpm-v"]

# Theme
CUSTOM_CSS = """
<style>
    :root {
        --bg: #0d0d0d;
        --bg-card: #141414;
        --bg-input: #1a1a1a;
        --bg-canvas: #0a0a0a;
        --text: #e8e8e8;
        --muted: #808080;
        --accent: #a8b5c4;
        --success: #98c4a8;
        --error: #c4a098;
        --border: #2a2a2a;
        --font: 'SF Mono', 'Consolas', monospace;
    }

    .stApp { background: var(--bg); font-family: var(--font); }
    #MainMenu, footer, header, .stDeployButton { display: none; }
    * { font-family: var(--font) !important; }

    /* Form container */
    [data-testid="stForm"] { background: var(--bg-card); border: 1px solid var(--border); padding: 2rem; max-width: 400px; margin: 0 auto; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 1px solid var(--border); }
    .stTabs [data-baseweb="tab"] { background: transparent; color: var(--muted); border: none; padding: 0.75rem 2rem; font-size: 0.85rem; letter-spacing: 0.1em; text-transform: uppercase; }
    .stTabs [aria-selected="true"] { color: var(--accent) !important; border-bottom: 2px solid var(--accent) !important; }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

    /* Inputs */
    .stTextInput > div > div { background: var(--bg-input) !important; border: 1px solid var(--border) !important; border-left: 2px solid var(--muted) !important; border-radius: 0 !important; }
    .stTextInput > div > div:focus-within { border-left-color: var(--accent) !important; outline: 2px solid var(--accent) !important; outline-offset: 1px !important; }
    .stTextInput input { color: var(--text) !important; background: transparent !important; }
    .stTextInput input::placeholder { color: var(--muted) !important; }
    .stTextInput label { color: var(--muted) !important; font-size: 0.75rem !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }

    /* Buttons */
    .stButton > button, .stFormSubmitButton > button { background: transparent !important; border: 1px solid var(--accent) !important; border-radius: 0 !important; color: var(--accent) !important; font-size: 0.8rem !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; padding: 0.75rem 2rem !important; }
    .stButton > button:hover, .stFormSubmitButton > button:hover { background: var(--accent) !important; color: var(--bg) !important; }
    .stButton > button:focus, .stFormSubmitButton > button:focus { outline: 2px solid var(--accent) !important; outline-offset: 2px !important; }
    .stFormSubmitButton > button { width: 100%; margin-top: 1rem; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: var(--bg-card) !important; border-right: 1px solid var(--border) !important; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] { color: var(--muted) !important; }
    [data-testid="stSidebar"] .stSelectbox > div > div, [data-testid="stSidebar"] [data-baseweb="select"] > div { background: var(--bg-input) !important; border: 1px solid var(--border) !important; border-radius: 0 !important; }

    /* File uploader */
    [data-testid="stFileUploader"] { border: 1px dashed var(--border) !important; border-radius: 0 !important; padding: 1rem !important; background: var(--bg-input) !important; }
    [data-testid="stFileUploader"]:hover { border-color: var(--accent) !important; }
    [data-testid="stFileUploader"] label { color: var(--muted) !important; font-size: 0.75rem !important; }
    [data-testid="stFileUploader"] button { background: var(--accent) !important; color: var(--bg) !important; border-radius: 0 !important; }

    /* Chat */
    [data-testid="stChatMessage"] { background: var(--bg-card) !important; border: 1px solid var(--border) !important; border-radius: 0 !important; padding: 1rem !important; margin-bottom: 0.5rem !important; }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { border-left: 2px solid var(--accent) !important; }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) { border-left: 2px solid var(--muted) !important; background: var(--bg-input) !important; }
    [data-testid="stChatInput"] textarea { background: var(--bg-input) !important; color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: 0 !important; }
    [data-testid="stChatInput"] textarea:focus { border-color: var(--accent) !important; }
    [data-testid="stChatInput"] button { background: var(--accent) !important; color: var(--bg) !important; border-radius: 0 !important; }

    /* Canvas/Preview area */
    .preview-canvas { background: var(--bg-canvas); border: 1px solid var(--border); border-radius: 0; padding: 1rem; margin: 1rem 0; min-height: 200px; }
    .preview-header { color: var(--muted); font-size: 0.7rem; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 0.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
    .preview-image { max-width: 100%; border: 1px solid var(--border); }
    .preview-code { background: var(--bg-canvas) !important; border-left: 2px solid var(--accent) !important; }

    /* Expander */
    [data-testid="stExpander"] { background: var(--bg-card) !important; border: 1px solid var(--border) !important; border-radius: 0 !important; }
    [data-testid="stExpander"] summary { color: var(--muted) !important; }

    /* Alerts */
    .stSuccess { background: rgba(152,196,168,0.1) !important; border-left: 3px solid var(--success) !important; color: var(--success) !important; border-radius: 0 !important; }
    .stError { background: rgba(196,160,152,0.1) !important; border-left: 3px solid var(--error) !important; color: var(--error) !important; border-radius: 0 !important; }
    .stWarning { background: rgba(196,184,152,0.1) !important; border-left: 3px solid #c4b898 !important; color: #c4b898 !important; border-radius: 0 !important; }

    /* Code */
    pre { background: var(--bg-canvas) !important; border-left: 2px solid var(--accent) !important; border-radius: 0 !important; padding: 1rem !important; }
    code { color: var(--accent) !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-card); }
    ::-webkit-scrollbar-thumb { background: var(--border); }
    ::-webkit-scrollbar-thumb:hover { background: var(--accent); }

    /* Links */
    a { color: var(--accent) !important; text-decoration: none !important; }
    a:hover { opacity: 0.8; }

    /* Spinner */
    .stSpinner > div > div { border-top-color: var(--accent) !important; }

    /* Image in chat */
    .chat-image { max-width: 300px; border: 1px solid var(--border); margin: 0.5rem 0; }

    /* Download button */
    .stDownloadButton > button { background: var(--bg-input) !important; border: 1px solid var(--accent) !important; }
</style>
"""

# Database
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
        return True, "Registration successful"
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

# Ollama
def get_available_models():
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.ok:
            return [m["name"] for m in response.json().get("models", [])]
    except Exception:
        pass
    return [DEFAULT_MODEL]

def is_vision_model(model_name):
    return any(vm in model_name.lower() for vm in VISION_MODELS)

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def chat_with_ollama(messages, model, images=None):
    try:
        payload = {"model": model, "messages": messages, "stream": False}
        if images and is_vision_model(model):
            # Add images to the last user message
            if messages and messages[-1]["role"] == "user":
                messages[-1]["images"] = images
        response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
        if response.ok:
            data = response.json()
            return data.get("message", {}).get("content", "No response"), data
        return f"Error: {response.status_code}", None
    except Exception as e:
        return f"Error: {str(e)}", None

def extract_code_blocks(text):
    """Extract code blocks from markdown text"""
    pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    return [(lang or 'text', code.strip()) for lang, code in matches]

def detect_output_type(text):
    """Detect the type of output for preview"""
    if '```' in text:
        return 'code'
    if text.strip().startswith(('<?xml', '<svg', '<html', '<!DOCTYPE')):
        return 'markup'
    if re.search(r'\.(png|jpg|jpeg|gif|svg|webp)$', text.strip(), re.IGNORECASE):
        return 'image_url'
    return 'text'

# Init
init_db()

st.set_page_config(page_title="BÖRAK", page_icon="", layout="wide", initial_sidebar_state="collapsed")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_images" not in st.session_state:
    st.session_state.uploaded_images = []
if "last_output" not in st.session_state:
    st.session_state.last_output = None

# Auth
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            '<div style="text-align:center;margin:4rem 0 3rem">'
            '<h1 style="font-weight:200;letter-spacing:0.3em;color:#e8e8e8">BÖRAK</h1>'
            '<p style="color:#808080;font-size:0.75rem;letter-spacing:0.2em">LOCAL AI CHAT</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
        with tab1:
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="enter username")
                password = st.text_input("Password", type="password", placeholder="enter password")
                if st.form_submit_button("CONNECT"):
                    if username and password:
                        user_id = verify_user(username, password)
                        if user_id:
                            st.session_state.authenticated = True
                            st.session_state.user_id = user_id
                            st.session_state.username = username
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
                    else:
                        st.warning("Enter username and password")
        with tab2:
            with st.form("register_form", clear_on_submit=False):
                new_username = st.text_input("Username", placeholder="choose username", key="reg_user")
                new_password = st.text_input("Password", type="password", placeholder="choose password", key="reg_pass")
                confirm_password = st.text_input("Confirm", type="password", placeholder="confirm password", key="reg_confirm")
                if st.form_submit_button("REGISTER"):
                    if not new_username or not new_password:
                        st.warning("Fill all fields")
                    elif new_password != confirm_password:
                        st.error("Passwords don't match")
                    elif len(new_password) < 6:
                        st.error("Password: 6+ characters")
                    else:
                        success, msg = register_user(new_username, new_password)
                        st.success("Account created. Login now.") if success else st.error(msg)
        st.markdown('<p style="text-align:center;margin-top:3rem;color:#808080;font-size:0.75rem">SECURE LOCAL INFERENCE</p>', unsafe_allow_html=True)

# Chat
else:
    # Sidebar
    with st.sidebar:
        st.markdown(f'<p style="color:#808080;font-size:0.75rem;margin:0">USER</p><p style="color:#a8b5c4;margin:0.25rem 0 1rem">{st.session_state.username}</p>', unsafe_allow_html=True)

        models = get_available_models()
        selected_model = st.selectbox("Model", models, label_visibility="collapsed")

        # Show vision badge
        if is_vision_model(selected_model):
            st.markdown('<p style="color:#98c4a8;font-size:0.7rem;margin:0.5rem 0">◉ VISION ENABLED</p>', unsafe_allow_html=True)

        st.markdown('<p style="color:#808080;font-size:0.7rem;margin:1rem 0 0.5rem;letter-spacing:0.1em">ATTACH</p>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("", type=["png", "jpg", "jpeg", "gif", "webp"], label_visibility="collapsed", key="file_upload")

        if uploaded_file:
            st.session_state.uploaded_images = [encode_image(uploaded_file.read())]
            uploaded_file.seek(0)
            st.image(uploaded_file, width=150)
            if st.button("CLEAR IMAGE", use_container_width=True):
                st.session_state.uploaded_images = []
                st.rerun()

        st.markdown("<hr style='border-color:#2a2a2a;margin:1rem 0'>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        if c1.button("CLEAR", use_container_width=True):
            st.session_state.messages = []
            st.session_state.uploaded_images = []
            st.session_state.last_output = None
            st.rerun()
        if c2.button("LOGOUT", use_container_width=True):
            for k in ["authenticated", "user_id", "username", "messages", "uploaded_images", "last_output"]:
                st.session_state[k] = None if k not in ["messages", "uploaded_images"] else []
            st.session_state.authenticated = False
            st.rerun()

        st.markdown('<p style="color:#808080;font-size:0.75rem;position:fixed;bottom:1rem"><span style="color:#98c4a8">●</span> CONNECTED</p>', unsafe_allow_html=True)

    # Main area - two columns: chat and canvas
    chat_col, canvas_col = st.columns([3, 2])

    with chat_col:
        st.markdown('<h1 style="font-weight:200;letter-spacing:0.2em;font-size:1.25rem;border-bottom:1px solid #2a2a2a;padding-bottom:1rem;margin-bottom:1rem">CHAT</h1>', unsafe_allow_html=True)

        # Chat history
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    # Show attached image if present
                    if msg.get("has_image"):
                        st.markdown('<span style="color:#98c4a8;font-size:0.7rem">◉ IMAGE ATTACHED</span>', unsafe_allow_html=True)
                    st.markdown(msg["content"])

        # Chat input
        if prompt := st.chat_input("Enter message..."):
            # Prepare message
            has_image = bool(st.session_state.uploaded_images)
            user_msg = {"role": "user", "content": prompt, "has_image": has_image}
            st.session_state.messages.append(user_msg)

            with chat_container:
                with st.chat_message("user"):
                    if has_image:
                        st.markdown('<span style="color:#98c4a8;font-size:0.7rem">◉ IMAGE ATTACHED</span>', unsafe_allow_html=True)
                    st.markdown(prompt)

            # Get response
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("Processing..."):
                        # Prepare messages for API (without has_image field)
                        api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                        response, data = chat_with_ollama(api_messages, selected_model, st.session_state.uploaded_images if has_image else None)
                        st.markdown(response)
                        st.session_state.last_output = response

                        if data:
                            log_usage(st.session_state.user_id, selected_model, data.get("prompt_eval_count", 0), data.get("eval_count", 0))

            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.uploaded_images = []  # Clear after sending
            st.rerun()

    with canvas_col:
        st.markdown('<h1 style="font-weight:200;letter-spacing:0.2em;font-size:1.25rem;border-bottom:1px solid #2a2a2a;padding-bottom:1rem;margin-bottom:1rem">CANVAS</h1>', unsafe_allow_html=True)

        if st.session_state.last_output:
            output = st.session_state.last_output
            output_type = detect_output_type(output)

            # Code blocks preview
            code_blocks = extract_code_blocks(output)
            if code_blocks:
                st.markdown('<p style="color:#808080;font-size:0.7rem;letter-spacing:0.1em;margin-bottom:0.5rem">CODE OUTPUT</p>', unsafe_allow_html=True)
                for i, (lang, code) in enumerate(code_blocks):
                    with st.expander(f"{lang.upper()} [{i+1}]", expanded=i==0):
                        st.code(code, language=lang if lang != 'text' else None)
                        # Download button
                        ext = {'python': 'py', 'javascript': 'js', 'typescript': 'ts', 'html': 'html', 'css': 'css', 'json': 'json', 'yaml': 'yaml', 'markdown': 'md'}.get(lang.lower(), 'txt')
                        st.download_button(f"DOWNLOAD", code, file_name=f"output_{i+1}.{ext}", mime="text/plain", use_container_width=True)

            # Raw text preview
            elif output_type == 'text':
                st.markdown('<p style="color:#808080;font-size:0.7rem;letter-spacing:0.1em;margin-bottom:0.5rem">TEXT OUTPUT</p>', unsafe_allow_html=True)
                with st.container():
                    st.markdown(f'<div style="background:#0a0a0a;border:1px solid #2a2a2a;padding:1rem;max-height:400px;overflow-y:auto">{output}</div>', unsafe_allow_html=True)
                st.download_button("DOWNLOAD", output, file_name="output.txt", mime="text/plain", use_container_width=True)

            # Markup preview
            elif output_type == 'markup':
                st.markdown('<p style="color:#808080;font-size:0.7rem;letter-spacing:0.1em;margin-bottom:0.5rem">MARKUP OUTPUT</p>', unsafe_allow_html=True)
                tab1, tab2 = st.tabs(["PREVIEW", "SOURCE"])
                with tab1:
                    st.components.v1.html(output, height=400, scrolling=True)
                with tab2:
                    st.code(output, language="html")
        else:
            st.markdown(
                '<div style="background:#0a0a0a;border:1px dashed #2a2a2a;padding:2rem;text-align:center;color:#808080;font-size:0.8rem">'
                'OUTPUT PREVIEW<br><span style="font-size:0.7rem;color:#606060">Code, images, and text will appear here</span>'
                '</div>',
                unsafe_allow_html=True
            )
