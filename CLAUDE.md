# BÖRAK - Ollama Chat Service

## Quick Start
```bash
# Check deployment
curl -s http://45.159.230.42:8501/_stcore/health

# Restart if needed
ssh -p 1511 root@45.159.230.42 "fuser -k 8501/tcp; cd /opt/ollama-ui && source venv/bin/activate && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &"

# Deploy changes
scp -P 1511 app.py root@45.159.230.42:/opt/ollama-ui/app.py
```

## Critical Warning ⚠️
**Canvas column indentation**: `canvas_col` MUST be at **4 spaces** (same level as `chat_col`).
Using 8 spaces nests it inside `chat_col` and breaks the layout. This bug was fixed twice.

## Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                    │
├─────────────────────────────────────────────────────────┤
│  Main Thread (polling)  │  Background Thread (daemon)   │
│  - Renders UI           │  - Calls Ollama API           │
│  - Polls gen_*.json     │  - Writes to gen_{user}.json  │
│  - Updates chat display │  - Survives WebSocket drops   │
└─────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
┌─────────────────┐       ┌─────────────────┐
│  ChromaDB       │       │  Ollama API     │
│  (vector store) │       │  localhost:11434│
└─────────────────┘       └─────────────────┘
         │
         ▼
┌─────────────────┐
│  SQLite         │
│  (users.db)     │
└─────────────────┘
```

- **Frontend**: Streamlit (Python)
- **LLM Backend**: Ollama API (localhost:11434 on VPS)
- **Auth DB**: SQLite (users.db)
- **Vector Store**: ChromaDB (chat persistence)
- **State Persistence**: File-based (`gen_{user_id}.json`)
- **Auth**: bcrypt password hashing

## Key Files
| File | Purpose |
|------|---------|
| `app.py` | Main application (~945 lines) - UI, auth, chat, vision |
| `.streamlit/config.toml` | Theme configuration |
| `users.db` | User database (gitignored) |
| `dev/active/handoff.md` | Session continuity documentation |
| `dev/active/borak-context.md` | Architecture and context |
| `dev/active/borak-tasks.md` | Task tracking |

## App.py Structure
```
Lines 1-50:     Imports, constants, VISION_MODELS list
Lines 51-150:   CSS styling (cypherpunk theme)
Lines 151-250:  Auth functions (login, register, bcrypt)
Lines 251-400:  ChromaDB integration, chat persistence
Lines 401-550:  Background generation (daemon threads, polling)
Lines 551-700:  UI components (sidebar, chat display)
Lines 701-945:  Main layout (chat_col, canvas_col at SAME indent)
```

## Vision Models
Vision-capable models are auto-detected by name pattern:
```python
VISION_MODELS = ["deepseek-ocr", "qwen3-vl", "llava", "moondream", ...]
```
When a vision model is selected, image upload is enabled in sidebar.

## CSS Customization
Cypherpunk terminal theme with:
- `--accent: #00cc66` (terminal green)
- `--cyan: #00cccc` (secondary)
- Forced sidebar visibility (no collapse)
- Hidden Streamlit branding

## VPS Info
| Property | Value |
|----------|-------|
| IP | 45.159.230.42 |
| SSH Port | **1511** (not 22!) |
| App Port | 8501 |
| Ollama Port | 11434 (localhost only) |

## Known Issues & Fixes
| Issue | Symptom | Fix |
|-------|---------|-----|
| WebSocket drops | Response lost mid-generation | Background thread + file persistence |
| Infinite rerun loops | Page keeps refreshing | Remove `st.rerun()`, use polling |
| Panel toggle interrupts | Generation stops on sidebar click | JS toggle instead of Python button |
| Layout broken | Login form in wrong column | Fix canvas_col indent to 4 spaces |
