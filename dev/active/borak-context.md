# BÖRAK Chat Service - Session Context

**Last Updated**: 2026-01-25 00:15 UTC
**Status**: Deployed and functional

## Current State

### Deployment
- **URL**: http://45.159.230.42:8501
- **Health**: OK
- **VPS**: 45.159.230.42, SSH port 1511

### Features Implemented This Session

1. **Streaming Responses** ✅
   - Real-time token streaming with `▌` cursor
   - Uses generator pattern with `chat_with_ollama_stream()`
   - Removed problematic `st.rerun()` that caused loops

2. **Chat Persistence** ✅
   - SQLite: `chat_history` table (fallback)
   - ChromaDB: Vector storage with embeddings at `/opt/ollama-ui/chroma_db`
   - Stream cache: JSON files at `/opt/ollama-ui/stream_cache/`

3. **Crash Recovery** ✅
   - Every token saved to `stream_cache/stream_{user_id}.json`
   - On login, checks for incomplete streams and recovers
   - Shows `*[Recovered from interruption]*` marker

4. **UI Lock During Streaming** ✅
   - Sidebar dims to 50% with "◉ GENERATING..." overlay
   - All widgets disabled via `pointer-events: none`
   - Prevents accidental interruption

5. **JavaScript Panel Toggle** ✅
   - `◀ PANEL` button in top-left corner
   - Pure JS toggle, no Streamlit rerun
   - Safe to use during streaming

## Key Files Modified

| File | Changes |
|------|---------|
| `app.py` | Added ChromaDB, streaming, UI lock, JS toggle |
| `chroma_db/` | New - ChromaDB persistent storage |
| `stream_cache/` | New - Streaming recovery cache |

## Architecture Decisions

### Why ChromaDB?
- Persistent vector storage with embeddings
- Enables future semantic search over chat history
- Self-contained (no external service needed)

### Why Stream Cache?
- Immediate disk write on every token
- Survives crashes, page refreshes, browser closes
- JSON format for easy debugging

### Why JS Panel Toggle?
- Streamlit buttons trigger `st.rerun()`
- Rerun kills streaming generator mid-execution
- Pure JS/CSS toggle doesn't touch Python

## Known Issues

1. **Long generations (6+ min)**: May timeout or lose connection
2. **First load after Chroma install**: Slightly slower (model loading)
3. **File uploader label warning**: Cosmetic warning in logs

## Critical Commands

```bash
# Check health
curl -s http://45.159.230.42:8501/_stcore/health

# Restart service
ssh -p 1511 root@45.159.230.42 "pkill streamlit; fuser -k 8501/tcp; cd /opt/ollama-ui && source venv/bin/activate && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > /tmp/streamlit.log 2>&1 &"

# Deploy changes
scp -P 1511 app.py root@45.159.230.42:/opt/ollama-ui/app.py

# Check logs
ssh -p 1511 root@45.159.230.42 "tail -50 /tmp/streamlit.log"

# Check Ollama
ssh -p 1511 root@45.159.230.42 "journalctl -u ollama -n 30"
```

## Session Summary

Started with: Basic Streamlit chat with vision support, cypherpunk UI
Ended with: Production-ready chat with streaming, persistence, crash recovery, UI lock

### Commits Made
- `1a640f0`: docs: add project context for Claude Code
- `2338276`: fix(ui): force sidebar visible and hide broken icons
- Plus uncommitted changes for streaming/persistence (need to commit)

## Next Steps

1. **Commit current changes** - streaming, ChromaDB, UI lock
2. **Test vision models** - image upload with llava/moondream
3. **Add STOP button** - cancel long-running generations
4. **Semantic search** - use ChromaDB embeddings for "find similar" feature
