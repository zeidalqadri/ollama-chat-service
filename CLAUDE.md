# BORAK - Ollama Chat Service

## Quick Start
```bash
# Development
uvicorn main:app --reload --port 8012

# Production (use systemd)
sudo systemctl start borak

# Check health
curl -s http://192.168.0.251:8012/health

# Deploy changes
scp -P 22 main.py static/* the_bomb@192.168.0.251:/opt/ollama-ui/
sudo systemctl restart borak
```

## Architecture

### Ollama Backend

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (index.html)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Login Page  │  │  Chat Page  │  │  Canvas Panel   │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP/SSE
┌──────────────────────────┴──────────────────────────────┐
│                  FastAPI Backend (main.py)               │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Ollama Client                        │   │
│  │  - All models via Ollama API                     │   │
│  │  - Vision models auto-detected                   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │       Ollama        │
              │    Port 11434       │
              │ ─────────────────── │
              │ qwen3-coder:30b     │
              │ guardpoint:latest   │
              │ deepseek-ocr        │
              │ translategemma      │
              └─────────────────────┘
```

### Data Layer

```
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │  SQLite  │  │ ChromaDB │  │  Ollama              │   │
│  │ (users)  │  │ (history)│  │  (LLM inference)     │   │
│  └──────────┘  └──────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Key Files
| File | Purpose |
|------|---------|
| `main.py` | FastAPI backend - Auth, Chat, SSE streaming |
| `static/index.html` | Single-page app - Login/Chat views |
| `static/style.css` | Cypherpunk terminal theme |
| `static/app.js` | Client-side logic - Auth, streaming, UI |
| `systemd/borak.service` | Systemd service for BORAK |
| `systemd/cloudflared.service` | Cloudflare tunnel service |
| `deploy-gpu-vps.sh` | GPU VPS deployment script |
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

## Available Models

| Model | Size | Purpose | Notes |
|-------|------|---------|-------|
| `qwen3-coder:30b` | 18 GB | General coding | Default model |
| `guardpoint:latest` | 15 GB | Medical reasoning | Qwen3-14B fine-tuned on medical data |
| `deepseek-ocr:latest` | 6.7 GB | Vision/OCR | Image understanding |
| `translategemma:latest` | 3.3 GB | Translation | Multi-language translation |

### Guardpoint (Medical Specialist)
Based on [Qwen3-14B-Guardpoint](https://huggingface.co/ValiantLabs/Qwen3-14B-Guardpoint) - a medical reasoning model trained on clinical data across multiple disciplines (cardiology, neurology, oncology, radiology, etc.).

Features:
- Extended reasoning via `<think>` blocks (captured as artifacts)
- Structured diagnostic output
- Differential diagnosis support

### Vision Models
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
| Host | 192.168.0.251 (GPU VPS) |
| User | the_bomb |
| SSH Port | 22 |
| App Port | 8012 |
| Ollama Port | 11434 (localhost only) |
| Tunnel (main) | borak.roowang.com |
| Tunnel (backup) | borak.zeidgeist.com |

## Systemd Services

### Install Services
```bash
# Copy service files
sudo cp systemd/borak.service /etc/systemd/system/
sudo cp systemd/cloudflared.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable borak ollama cloudflared
sudo systemctl start borak ollama cloudflared
```

### Service Management
```bash
# Check status
systemctl status borak ollama cloudflared

# View logs
journalctl -u borak -f

# Restart after code changes
sudo systemctl restart borak
```

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
- **HTTPS**: `secure=True` (production via Cloudflare tunnel)

If cookies aren't being set (401 errors on all API calls after login), check this setting in `main.py`.

## Deployment

### Quick Deploy (after code changes)
```bash
# From local machine
scp -P 22 main.py static/* the_bomb@192.168.0.251:/opt/ollama-ui/
ssh the_bomb@192.168.0.251 "sudo systemctl restart borak"
```

### Full Deploy (fresh VPS)
```bash
# Run the deployment script
./deploy-gpu-vps.sh
```

## Migration from Streamlit
The app was migrated from Streamlit to FastAPI to eliminate DOM ghost issues.
Key changes:
- `st.session_state` -> JWT cookies
- `st.chat_message()` -> HTML divs with CSS classes
- `st.chat_input()` -> HTML textarea + JS handler
- `st.rerun()` -> Event-driven (no longer needed)
- Streaming via `st.write_stream()` -> Server-Sent Events (SSE)
