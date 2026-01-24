# Handoff Document - BÖRAK Session 2026-01-25

## Quick Resume

```bash
# Verify deployment
curl -s http://45.159.230.42:8501/_stcore/health

# SSH to VPS (note: port 1511, NOT 22)
ssh -p 1511 root@45.159.230.42

# Restart service if needed
ssh -p 1511 root@45.159.230.42 "fuser -k 8501/tcp; cd /opt/ollama-ui && source venv/bin/activate && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &"
```

## Current State

| Item | Status |
|------|--------|
| **Latest Commit** | `2ada959` - fix(ui): resolve overlay issues and ghost login panels |
| **Previous Commit** | `cad18df` - docs: expand CLAUDE.md with architecture |
| **Deployed** | Yes, running on VPS with latest code |
| **GitHub** | Pushed, in sync with local |
| **Health** | OK |

## What Changed This Session

### Commit 1: `cad18df` - CLAUDE.md Update
- Added architecture diagram showing background thread pattern
- Added critical warning about canvas_col indentation bug
- Added known issues & fixes table
- Added app.py structure with line references

### Commit 2: `2ada959` - UI Overlay Fixes
| Fix | Details |
|-----|---------|
| Panel toggle position | Changed `left: 0.75rem` → `left: calc(280px + 0.75rem)` to not overlay sidebar |
| CONNECTED badge | Moved from `position: fixed` to inline inside sidebar |
| Ghost login forms | Added `login-page`/`chat-page` body classes via JS |
| Form CSS scoping | Changed from global `[data-testid="stForm"]` to `.login-page [data-testid="stForm"]` |
| Toggle on login | Hidden via `.login-page #panel-toggle { display: none }` |

## Key Code Locations

| Feature | Location | Notes |
|---------|----------|-------|
| Page class JS function | app.py:673-705 | `get_page_js()` returns login-page or chat-page |
| JS injection | app.py:724 | Called after session state init |
| Panel toggle CSS | app.py:147-183 | Includes login-page hiding |
| Form CSS scoping | app.py:61-70 | Only `.login-page` gets form brackets |
| CONNECTED badge | app.py:845-851 | Now inside sidebar, not fixed |
| Column layout | app.py:854 | `chat_col, canvas_col = st.columns([3, 2])` |

## ⚠️ CRITICAL WARNINGS

### 1. Indentation Bug (Fixed Twice!)
```python
# Lines ~856 and ~932 MUST have same indent (4 spaces)
    with chat_col:    # 4 spaces
        ...
    with canvas_col:  # 4 spaces - SAME LEVEL!
        ...
```
If `canvas_col` has 8 spaces, it nests inside `chat_col` and breaks layout.

### 2. SSH Port
VPS uses port **1511**, not 22!

### 3. Page Class Injection
The `get_page_js()` function must be called AFTER session state initialization but BEFORE rendering any content.

## Test Checklist

1. **Login page**: No panel toggle button visible
2. **After login**: Panel toggle appears to right of sidebar (not overlapping)
3. **Chat area**: No ghost login form elements
4. **CONNECTED badge**: At bottom of sidebar content, not floating
5. **Generation**: Messages generate and display correctly

## Architecture Summary

```
Browser ←WebSocket→ Streamlit (port 8501)
                         ↓
                    app.py
                         ├── get_page_js() → Injects login-page/chat-page class
                         ├── Background Thread (daemon)
                         │   └── Writes to gen_{user_id}.json
                         ├── Main Thread
                         │   └── Polls JSON file every 0.5s
                         ├── ChromaDB (chroma_db/)
                         ├── SQLite (users.db)
                         └── Ollama API (localhost:11434)
```

## Pending Work (Next Session)

| Priority | Task |
|----------|------|
| HIGH | Test background generation recovery by refreshing mid-generation |
| MEDIUM | Test vision models with actual image uploads |
| MEDIUM | Add STOP button to cancel long generations |
| LOW | Add conversation export feature |

## Session Stats

- Session: Jan 25, 2026
- Commits: 2 (CLAUDE.md update + UI overlay fixes)
- Files modified: 2 (CLAUDE.md, app.py)
- Bugs fixed: 4 (panel overlay, badge overlay, ghost forms, toggle on login)
- Deployed & pushed: ✅
