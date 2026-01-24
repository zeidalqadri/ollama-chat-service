# BÖRAK Chat Service - Session Context

**Last Updated**: 2026-01-25 00:35 UTC
**Status**: Deployed and functional

## Current State

### Deployment
- **URL**: http://45.159.230.42:8501
- **Health**: OK
- **VPS**: 45.159.230.42, SSH port 1511

## Major Changes This Session

### 1. Background Generation System ✅
Replaced inline streaming with background thread generation to survive WebSocket drops.

**Architecture:**
```
User submits prompt → Background thread starts → Thread writes to gen_{user_id}.json
                                                          ↓
Streamlit polls file every 0.5s ← Displays progress ← Even if WebSocket drops, thread continues
                                                          ↓
On reconnect → Reads file → Resumes display or shows "[Recovered after reconnect]"
```

**Key Functions (app.py):**
- `start_background_generation()` - Starts daemon thread for Ollama API call
- `get_generation_state()` - Reads current state from JSON file
- `clear_generation()` - Cleans up after completion

### 2. ChromaDB Integration ✅
Vector storage for chat history with embeddings.

**Functions:**
- `chroma_save_message()` - Save with embedding
- `chroma_load_history()` - Load user's history
- `chroma_clear_user()` - Clear user's data

**Storage:** `/opt/ollama-ui/chroma_db/`

### 3. UI Lock During Generation ✅
CSS `.streaming-active` class + JavaScript to lock sidebar during generation.

### 4. JavaScript Panel Toggle ✅
Pure JS toggle button `◀ PANEL` - doesn't trigger Streamlit rerun.

## Critical Bug Fixes

### WebSocket Drop Issue
**Problem:** Streamlit's WebSocket would close during long generations, killing the response.
**Solution:** Background thread generation with file-based state persistence.

### Indentation Bug (Fixed Twice!)
**Problem:** `canvas_col` was nested inside `chat_col` (8 spaces instead of 4).
**Symptom:** Login form appeared in OUTPUT column.
**Solution:** Fixed indentation so both columns are siblings.

### Rerun Loop
**Problem:** `st.rerun()` after streaming caused infinite loop.
**Solution:** Removed unnecessary rerun; use polling pattern instead.

## File Structure

```
app.py (945 lines)
├── Lines 1-30: Imports and config
├── Lines 300-350: Ollama streaming function
├── Lines 400-500: ChromaDB and cache functions
├── Lines 500-600: Background generation functions
├── Lines 700-745: Auth (login/register)
├── Lines 747-905: Chat (else block)
│   ├── 828: chat_col, canvas_col = st.columns([3, 2])
│   ├── 830: with chat_col: (4 spaces indent)
│   ├── 871-904: Polling for generation progress
│   └── 906: with canvas_col: (4 spaces indent - MUST match chat_col!)
└── Lines 906-945: Output panel
```

## Critical Knowledge

### Indentation Rules
```python
# CORRECT - both at 4 spaces (inside else block)
    with chat_col:
        ...
    with canvas_col:  # Same indent level!
        ...

# WRONG - canvas_col nested inside chat_col
    with chat_col:
        ...
        with canvas_col:  # 8 spaces = WRONG!
```

### SSH Port
```
Port 1511 (NOT 22!)
```

### Service Commands
```bash
# Health check
curl -s http://45.159.230.42:8501/_stcore/health

# Restart
ssh -p 1511 root@45.159.230.42 "pkill streamlit; fuser -k 8501/tcp; sleep 1; cd /opt/ollama-ui && source venv/bin/activate && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > /tmp/streamlit.log 2>&1 &"

# Deploy
scp -P 1511 app.py root@45.159.230.42:/opt/ollama-ui/app.py

# Logs
ssh -p 1511 root@45.159.230.42 "tail -50 /tmp/streamlit.log"
```

## Pending Work

1. **Test background generation recovery** - Refresh mid-generation, verify it recovers
2. **Add STOP button** - Cancel long generations
3. **Test vision models** - Upload images with llava/moondream
4. **Commit changes** - Current changes uncommitted

## Known Issues

1. **File uploader label warning** - Cosmetic only, non-blocking
2. **Port 8501 sometimes held** - Use `fuser -k 8501/tcp` before restart
