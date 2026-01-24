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

# Theme - Cypherpunk Terminal Aesthetic
CUSTOM_CSS = """
<style>
    :root {
        --bg: #0a0a0a;
        --bg-card: #0d0d0d;
        --bg-input: #111111;
        --bg-canvas: #080808;
        --text: #c0c0c0;
        --muted: #606060;
        --accent: #00cc66;
        --accent-dim: #006633;
        --cyan: #00cccc;
        --amber: #cc9900;
        --error: #cc3333;
        --border: #1a1a1a;
        --border-active: #333333;
        --font: 'JetBrains Mono', 'Fira Code', 'SF Mono', 'Consolas', monospace;
    }

    /* Base reset */
    .stApp { background: var(--bg); font-family: var(--font); color: var(--text); }
    #MainMenu, footer, header, .stDeployButton { display: none !important; }
    * { font-family: var(--font) !important; box-sizing: border-box; }

    /* Form container with corner brackets */
    [data-testid="stForm"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        padding: 2rem;
        max-width: 400px;
        margin: 0 auto;
        position: relative;
    }
    [data-testid="stForm"]::before { content: '┌'; position: absolute; top: -1px; left: -1px; color: var(--accent); font-size: 1rem; }
    [data-testid="stForm"]::after { content: '┘'; position: absolute; bottom: -1px; right: -1px; color: var(--accent); font-size: 1rem; }

    /* Tabs - terminal style */
    .stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 1px solid var(--border); gap: 0; }
    .stTabs [data-baseweb="tab"] { background: transparent; color: var(--muted); border: none; padding: 0.5rem 1.5rem; font-size: 0.8rem; letter-spacing: 0.15em; text-transform: uppercase; }
    .stTabs [data-baseweb="tab"]:hover { color: var(--text); }
    .stTabs [aria-selected="true"] { color: var(--accent) !important; border-bottom: 1px solid var(--accent) !important; background: var(--bg-input) !important; }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

    /* Hide form submit hint */
    .stTextInput div[data-baseweb="tooltip"] { display: none !important; }
    div[data-baseweb="tooltip"] { display: none !important; }
    [data-testid="InputInstructions"] { display: none !important; }

    /* Inputs - command prompt style */
    .stTextInput > div > div {
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-left: 2px solid var(--accent-dim) !important;
        border-radius: 0 !important;
    }
    .stTextInput > div > div:focus-within {
        border-left-color: var(--accent) !important;
        box-shadow: 0 0 8px rgba(0,204,102,0.15) !important;
    }
    .stTextInput input { color: var(--text) !important; background: transparent !important; font-size: 0.9rem !important; }
    .stTextInput input::placeholder { color: var(--muted) !important; font-style: normal !important; }
    .stTextInput label { color: var(--muted) !important; font-size: 0.7rem !important; text-transform: uppercase !important; letter-spacing: 0.15em !important; }

    /* Buttons - bordered, not filled */
    .stButton > button, .stFormSubmitButton > button {
        background: transparent !important;
        border: 1px solid var(--accent) !important;
        border-radius: 0 !important;
        color: var(--accent) !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.15em !important;
        text-transform: uppercase !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        background: var(--accent) !important;
        color: var(--bg) !important;
        box-shadow: 0 0 12px rgba(0,204,102,0.3) !important;
    }
    .stButton > button:focus, .stFormSubmitButton > button:focus { outline: 1px solid var(--accent) !important; outline-offset: 2px !important; }
    .stFormSubmitButton > button { width: 100%; margin-top: 1rem; }

    /* Sidebar - control panel */
    [data-testid="stSidebar"] { background: var(--bg-card) !important; border-right: 1px solid var(--border) !important; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] { color: var(--muted) !important; font-size: 0.7rem !important; letter-spacing: 0.1em !important; }
    [data-testid="stSidebar"] .stSelectbox > div > div,
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        color: var(--text) !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        border: 1px dashed var(--border) !important;
        border-radius: 0 !important;
        padding: 0.75rem !important;
        background: var(--bg-input) !important;
    }
    [data-testid="stFileUploader"]:hover { border-color: var(--accent-dim) !important; }
    [data-testid="stFileUploader"] label { color: var(--muted) !important; font-size: 0.7rem !important; }
    [data-testid="stFileUploader"] button { background: var(--accent-dim) !important; color: var(--text) !important; border-radius: 0 !important; border: none !important; }
    [data-testid="stFileUploader"] button:hover { background: var(--accent) !important; color: var(--bg) !important; }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        padding: 1rem !important;
        margin-bottom: 0.5rem !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        border-left: 2px solid var(--cyan) !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        border-left: 2px solid var(--accent-dim) !important;
        background: var(--bg-input) !important;
    }

    /* Chat input */
    [data-testid="stChatInput"] textarea {
        background: var(--bg-input) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
        font-size: 0.9rem !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: var(--accent-dim) !important;
        box-shadow: 0 0 8px rgba(0,204,102,0.1) !important;
    }
    [data-testid="stChatInput"] button {
        background: var(--accent) !important;
        color: var(--bg) !important;
        border-radius: 0 !important;
    }

    /* Expander - code blocks */
    [data-testid="stExpander"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;
    }
    [data-testid="stExpander"] summary { color: var(--cyan) !important; font-size: 0.8rem !important; }
    [data-testid="stExpander"] summary:hover { color: var(--accent) !important; }

    /* Alerts - status messages */
    .stSuccess { background: rgba(0,204,102,0.05) !important; border: 1px solid var(--accent-dim) !important; border-left: 3px solid var(--accent) !important; color: var(--accent) !important; border-radius: 0 !important; }
    .stError { background: rgba(204,51,51,0.05) !important; border: 1px solid #661a1a !important; border-left: 3px solid var(--error) !important; color: var(--error) !important; border-radius: 0 !important; }
    .stWarning { background: rgba(204,153,0,0.05) !important; border: 1px solid #664d00 !important; border-left: 3px solid var(--amber) !important; color: var(--amber) !important; border-radius: 0 !important; }
    .stInfo { background: rgba(0,204,204,0.05) !important; border: 1px solid #006666 !important; border-left: 3px solid var(--cyan) !important; color: var(--cyan) !important; border-radius: 0 !important; }

    /* Code blocks */
    pre {
        background: var(--bg-canvas) !important;
        border: 1px solid var(--border) !important;
        border-left: 2px solid var(--accent) !important;
        border-radius: 0 !important;
        padding: 1rem !important;
    }
    code { color: var(--accent) !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border-active); }
    ::-webkit-scrollbar-thumb:hover { background: var(--accent-dim); }

    /* Links */
    a { color: var(--cyan) !important; text-decoration: none !important; }
    a:hover { color: var(--accent) !important; }

    /* Spinner */
    .stSpinner > div > div { border-top-color: var(--accent) !important; }

    /* Download button */
    .stDownloadButton > button {
        background: var(--bg-input) !important;
        border: 1px solid var(--accent-dim) !important;
        color: var(--accent) !important;
    }
    .stDownloadButton > button:hover {
        border-color: var(--accent) !important;
        box-shadow: 0 0 8px rgba(0,204,102,0.2) !important;
    }

    /* Image preview */
    [data-testid="stImage"] img { border: 1px solid var(--border) !important; }

    /* Horizontal rule */
    hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

    /* Status indicator glow */
    .status-online { color: var(--accent); text-shadow: 0 0 6px var(--accent); }
    .status-vision { color: var(--cyan); text-shadow: 0 0 6px var(--cyan); }
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

st.set_page_config(page_title="BÖRAK", page_icon="", layout="wide", initial_sidebar_state="expanded")
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
            '<p style="color:#006633;font-size:0.7rem;letter-spacing:0.3em;margin-bottom:1rem">[ SYSTEM ONLINE ]</p>'
            '<h1 style="font-weight:300;letter-spacing:0.4em;color:#c0c0c0;font-size:2rem;margin:0">BÖRAK</h1>'
            '<p style="color:#606060;font-size:0.7rem;letter-spacing:0.2em;margin-top:0.5rem">LOCAL INFERENCE TERMINAL</p>'
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
        st.markdown('<p style="text-align:center;margin-top:3rem;color:#606060;font-size:0.65rem;letter-spacing:0.15em">◉ E2E LOCAL · NO TELEMETRY · YOUR DATA</p>', unsafe_allow_html=True)

# Chat
else:
    # Sidebar - Control Panel
    with st.sidebar:
        st.markdown(
            f'<div style="border-bottom:1px solid #1a1a1a;padding-bottom:1rem;margin-bottom:1rem">'
            f'<p style="color:#606060;font-size:0.65rem;letter-spacing:0.15em;margin:0">┌─ USER</p>'
            f'<p style="color:#00cc66;font-size:0.85rem;margin:0.25rem 0 0 0;font-weight:500">> {st.session_state.username}</p>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown('<p style="color:#606060;font-size:0.65rem;letter-spacing:0.15em;margin-bottom:0.5rem">┌─ MODEL</p>', unsafe_allow_html=True)
        models = get_available_models()
        selected_model = st.selectbox("Model", models, label_visibility="collapsed")

        # Vision capability indicator
        if is_vision_model(selected_model):
            st.markdown('<p style="color:#00cccc;font-size:0.7rem;margin:0.5rem 0" class="status-vision">◉ VISION CAPABLE</p>', unsafe_allow_html=True)

        st.markdown('<p style="color:#606060;font-size:0.65rem;letter-spacing:0.15em;margin:1.5rem 0 0.5rem">┌─ ATTACH</p>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("", type=["png", "jpg", "jpeg", "gif", "webp"], label_visibility="collapsed", key="file_upload")

        if uploaded_file:
            st.session_state.uploaded_images = [encode_image(uploaded_file.read())]
            uploaded_file.seek(0)
            st.image(uploaded_file, width=140)
            if st.button("× REMOVE", use_container_width=True):
                st.session_state.uploaded_images = []
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        st.markdown('<p style="color:#606060;font-size:0.65rem;letter-spacing:0.15em;margin-bottom:0.5rem">┌─ ACTIONS</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("CLEAR", use_container_width=True):
            st.session_state.messages = []
            st.session_state.uploaded_images = []
            st.session_state.last_output = None
            st.rerun()
        if c2.button("EXIT", use_container_width=True):
            for k in ["authenticated", "user_id", "username", "messages", "uploaded_images", "last_output"]:
                st.session_state[k] = None if k not in ["messages", "uploaded_images"] else []
            st.session_state.authenticated = False
            st.rerun()

        st.markdown(
            '<div style="position:fixed;bottom:1rem;left:1rem">'
            '<p style="color:#006633;font-size:0.7rem;letter-spacing:0.1em" class="status-online">● CONNECTED</p>'
            '<p style="color:#606060;font-size:0.6rem;margin-top:0.25rem">LOCAL · SECURE</p>'
            '</div>',
            unsafe_allow_html=True
        )

    # Main area - two columns: chat and canvas
    chat_col, canvas_col = st.columns([3, 2])

    with chat_col:
        st.markdown('<p style="color:#606060;font-size:0.7rem;letter-spacing:0.15em;border-bottom:1px solid #1a1a1a;padding-bottom:0.75rem;margin-bottom:1rem">[ TERMINAL ]</p>', unsafe_allow_html=True)

        # Chat history
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    # Show attached image if present
                    if msg.get("has_image"):
                        st.markdown('<span style="color:#00cccc;font-size:0.65rem;letter-spacing:0.1em">◎ IMAGE ATTACHED</span>', unsafe_allow_html=True)
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
                        st.markdown('<span style="color:#00cccc;font-size:0.65rem;letter-spacing:0.1em">◎ IMAGE ATTACHED</span>', unsafe_allow_html=True)
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
        st.markdown('<p style="color:#606060;font-size:0.7rem;letter-spacing:0.15em;border-bottom:1px solid #1a1a1a;padding-bottom:0.75rem;margin-bottom:1rem">[ OUTPUT ]</p>', unsafe_allow_html=True)

        if st.session_state.last_output:
            output = st.session_state.last_output
            output_type = detect_output_type(output)

            # Code blocks preview
            code_blocks = extract_code_blocks(output)
            if code_blocks:
                st.markdown('<p style="color:#00cccc;font-size:0.65rem;letter-spacing:0.15em;margin-bottom:0.5rem">├─ CODE EXTRACTED</p>', unsafe_allow_html=True)
                for i, (lang, code) in enumerate(code_blocks):
                    with st.expander(f"[{i+1}] {lang.upper()}", expanded=i==0):
                        st.code(code, language=lang if lang != 'text' else None)
                        ext = {'python': 'py', 'javascript': 'js', 'typescript': 'ts', 'html': 'html', 'css': 'css', 'json': 'json', 'yaml': 'yaml', 'markdown': 'md'}.get(lang.lower(), 'txt')
                        st.download_button(f"↓ EXPORT .{ext.upper()}", code, file_name=f"output_{i+1}.{ext}", mime="text/plain", use_container_width=True)

            # Raw text preview
            elif output_type == 'text':
                st.markdown('<p style="color:#00cccc;font-size:0.65rem;letter-spacing:0.15em;margin-bottom:0.5rem">├─ TEXT OUTPUT</p>', unsafe_allow_html=True)
                with st.container():
                    st.markdown(f'<div style="background:#080808;border:1px solid #1a1a1a;border-left:2px solid #006633;padding:1rem;max-height:400px;overflow-y:auto;font-size:0.85rem;color:#c0c0c0">{output}</div>', unsafe_allow_html=True)
                st.download_button("↓ EXPORT .TXT", output, file_name="output.txt", mime="text/plain", use_container_width=True)

            # Markup preview
            elif output_type == 'markup':
                st.markdown('<p style="color:#00cccc;font-size:0.65rem;letter-spacing:0.15em;margin-bottom:0.5rem">├─ MARKUP DETECTED</p>', unsafe_allow_html=True)
                tab1, tab2 = st.tabs(["RENDER", "SOURCE"])
                with tab1:
                    st.components.v1.html(output, height=400, scrolling=True)
                with tab2:
                    st.code(output, language="html")
        else:
            st.markdown(
                '<div style="background:#080808;border:1px dashed #1a1a1a;padding:3rem 2rem;text-align:center">'
                '<p style="color:#606060;font-size:0.7rem;letter-spacing:0.2em;margin:0">AWAITING OUTPUT</p>'
                '<p style="color:#333;font-size:0.65rem;margin-top:0.5rem">Code blocks and text will render here</p>'
                '</div>',
                unsafe_allow_html=True
            )
