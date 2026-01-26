# BORAK - Ollama Chat Service

## Quick Start
```bash
# Development
uvicorn main:app --reload --port 8012

# Production
uvicorn main:app --host 0.0.0.0 --port 8012

# Check health
curl -s http://45.159.230.42:8012/health

# Deploy changes
scp -P 1511 main.py static/* root@45.159.230.42:/opt/ollama-ui/
```

## Architecture
```
+---------------------------------------------------------+
|                    Browser (index.html)                  |
|  +-------------+  +-------------+  +-----------------+  |
|  | Login Page  |  |  Chat Page  |  |  Canvas Panel   |  |
|  +-------------+  +-------------+  +-----------------+  |
+--------------------------+------------------------------+
                           | HTTP/SSE
+--------------------------+------------------------------+
|                  FastAPI Backend (main.py)               |
|  +----------+  +----------+  +----------+  +---------+  |
|  |  Auth    |  |  Chat    |  |  Models  |  | Stream  |  |
|  |  Routes  |  |  Routes  |  |  Routes  |  |  (SSE)  |  |
|  +----------+  +----------+  +----------+  +---------+  |
+--------------------------+------------------------------+
                           |
+--------------------------+------------------------------+
|                    Data Layer                            |
|  +----------+  +----------+  +----------------------+   |
|  |  SQLite  |  | ChromaDB |  |  Ollama API          |   |
|  | (users)  |  | (history)|  |  localhost:11434     |   |
|  +----------+  +----------+  +----------------------+   |
+---------------------------------------------------------+
```

## Key Files
| File | Purpose |
|------|---------|
| `main.py` | FastAPI backend (~500 lines) - Auth, Chat, SSE streaming |
| `static/index.html` | Single-page app - Login/Chat views |
| `static/style.css` | Cypherpunk terminal theme |
| `static/app.js` | Client-side logic - Auth, streaming, UI |
| `app_streamlit.py` | Legacy Streamlit version (reference) |
| `users.db` | User database (gitignored) |
| `chroma_db/` | Vector store for chat history |

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login, sets JWT cookie |
| POST | `/api/auth/register` | Create new user |
| POST | `/api/auth/logout` | Clear session |
| GET | `/api/auth/me` | Get current user |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat/history` | Get chat history |
| POST | `/api/chat/send` | Send message (returns SSE stream) |
| DELETE | `/api/chat/clear` | Clear chat history |

### Models
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | List available Ollama models |

## Vision Models
Vision-capable models are auto-detected by name pattern:
```python
VISION_MODELS = ["deepseek-ocr", "qwen3-vl", "llava", "moondream", ...]
```

## CSS Theme Variables
```css
--bg: #0a0a0a;        /* Main background */
--bg-card: #0d0d0d;   /* Card background */
--accent: #00cc66;    /* Terminal green */
--cyan: #00cccc;      /* Secondary accent */
--muted: #606060;     /* Muted text */
--font: 'JetBrains Mono', monospace;
```

## VPS Info
| Property | Value |
|----------|-------|
| IP | 45.159.230.42 |
| SSH Port | **1511** (not 22!) |
| App Port | 8012 |
| Ollama Port | 11434 (localhost only) |

## Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API URL |
| `DATA_DIR` | `.` | Directory for SQLite and ChromaDB |
| `SECRET_KEY` | auto-generated | JWT signing key (set in production!) |
| `DEFAULT_MODEL` | `qwen3-coder:30b` | Default model selection |
| `IMAGE_RETENTION_DAYS` | `1` | Days to keep uploaded images before auto-cleanup |

## Cookie Security
The `secure` flag in `response.set_cookie()` must match your deployment:
- **HTTP**: `secure=False` (development, local testing)
- **HTTPS**: `secure=True` (production)

If cookies aren't being set (401 errors on all API calls after login), check this setting in `main.py` line ~1102.

## Migration from Streamlit
The app was migrated from Streamlit to FastAPI to eliminate DOM ghost issues.
Key changes:
- `st.session_state` -> JWT cookies
- `st.chat_message()` -> HTML divs with CSS classes
- `st.chat_input()` -> HTML textarea + JS handler
- `st.rerun()` -> Event-driven (no longer needed)
- Streaming via `st.write_stream()` -> Server-Sent Events (SSE)

Legacy Streamlit code preserved in `app_streamlit.py` for reference.
