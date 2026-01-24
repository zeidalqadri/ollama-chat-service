# Handoff Document - BÖRAK Session 2026-01-25

## Quick Resume

```bash
# Verify deployment
curl -s http://45.159.230.42:8501/_stcore/health

# SSH to VPS
ssh -p 1511 root@45.159.230.42

# View logs
ssh -p 1511 root@45.159.230.42 "tail -50 /tmp/streamlit.log"
```

## What Was Built

| Feature | Implementation | Files |
|---------|---------------|-------|
| Streaming | `chat_with_ollama_stream()` generator | app.py:299-320 |
| ChromaDB | `chroma_save_message()`, `chroma_load_history()` | app.py:330-400 |
| Stream cache | `save_stream_chunk()`, `load_stream_cache()` | app.py:402-440 |
| UI lock | CSS `.streaming-active` class + JS | app.py:145-165 |
| Panel toggle | Pure JS `togglePanel()` | app.py:260-280 |

## Current Production State

- **Commit**: f3766c8 (pushed to GitHub)
- **Deployed**: Yes, running on VPS
- **Health**: OK

## Pending Work

1. **Test vision models** - Upload image, try llava or moondream
2. **Add STOP button** - Cancel long generations via Ollama API
3. **Test crash recovery** - Refresh mid-stream, verify recovery

## Critical Knowledge

### SSH Port
```
Port 1511 (NOT 22!)
```

### Service Restart
```bash
ssh -p 1511 root@45.159.230.42 "pkill streamlit; fuser -k 8501/tcp; cd /opt/ollama-ui && source venv/bin/activate && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > /tmp/streamlit.log 2>&1 &"
```

### Deploy Single File
```bash
scp -P 1511 app.py root@45.159.230.42:/opt/ollama-ui/app.py
```

### Key Paths on VPS
- App: `/opt/ollama-ui/`
- Chroma DB: `/opt/ollama-ui/chroma_db/`
- Stream cache: `/opt/ollama-ui/stream_cache/`
- Users DB: `/opt/ollama-ui/users.db`
- Logs: `/tmp/streamlit.log`

## Architecture Summary

```
User Browser
    ↓
Streamlit (port 8501)
    ↓
app.py
    ├── SQLite (users.db) - auth, fallback chat
    ├── ChromaDB (chroma_db/) - vector chat storage
    ├── Stream cache (stream_cache/) - crash recovery
    └── Ollama API (localhost:11434) - LLM inference
```

## Session Statistics

- Duration: ~2 hours
- Lines changed: 351 added, 22 removed
- Features added: 5 major (streaming, ChromaDB, cache, UI lock, JS toggle)
- Bugs fixed: 3 (rerun loop, panel interrupt, response loss)
