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

## Architecture
- **Frontend**: Streamlit (Python)
- **Backend**: Ollama API (localhost:11434 on VPS)
- **Database**: SQLite (users.db)
- **Auth**: bcrypt password hashing

## Key Files
- `app.py` - Main application (UI, auth, chat, vision)
- `.streamlit/config.toml` - Theme config
- `users.db` - User database (gitignored)

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
- **IP**: 45.159.230.42
- **SSH Port**: 1511 (not 22!)
- **App Port**: 8501
- **Ollama Port**: 11434 (localhost only)
