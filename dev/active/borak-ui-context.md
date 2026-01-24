# BÖRAK UI Development Context

**Last Updated**: 2026-01-24 23:15 UTC
**Status**: Active Development - Sidebar Fixed

## Current Implementation State

### Deployed & Working
- **Production URL**: http://45.159.230.42:8501
- **GitHub**: https://github.com/zeidalqadri/ollama-chat-service
- **VPS SSH**: `ssh root@45.159.230.42 -p 1511`

### Features Implemented
1. **Authentication System** - SQLite-backed user registration/login with bcrypt
2. **Chat Interface** - Two-column layout (Terminal | Output)
3. **Vision Model Support** - Image upload with base64 encoding for vision models
4. **Canvas Preview** - Code block extraction, syntax highlighting, download buttons
5. **Cypherpunk UI Theme** - Terminal green (#00cc66), corner brackets, status indicators
6. **Sidebar Always Visible** - Fixed 280px width, no collapse

### Models Available on VPS (Tested & Working)
- `deepseek-ocr:latest` (6.7 GB) - OCR specialist ✅ Tested
- `qwen3-vl:4b` (3.3 GB) - Vision all-rounder ✅ Tested
- `qwen3-coder:30b` (18 GB) - Code generation
- `qwen2.5-coder:14b` (9.0 GB) - Code generation

## Key Decisions This Session

1. **Sidebar Force Visible**: CSS forces sidebar to always show (280px width, no collapse animation)
2. **Hide Collapse Button**: Material Icons font not loading, so hide the broken text icon
3. **Hide Form Tooltip**: CSS hides "Press Enter to submit form" Streamlit tooltip
4. **Vision API Tested**: Both vision models work via API with base64 image encoding

## Issues Fixed This Session

| Issue | Cause | Fix |
|-------|-------|-----|
| Sidebar not visible | `initial_sidebar_state="collapsed"` + user preference | CSS force visible + hide collapse button |
| "Press Enter" tooltip | Streamlit default | CSS hide `[data-testid="InputInstructions"]` |
| "keyboard_double_" text | Material Icons font not loading | CSS hide collapse button entirely |
| White screen on restart | Port 8501 held by zombie process | `fuser -k 8501/tcp` before restart |

## Files Modified

| File | Changes |
|------|---------|
| `app.py` | Main app - sidebar CSS fixes, tooltip hidden |

## CSS Architecture (Sidebar Section)

```css
/* Sidebar - force always visible */
[data-testid="stSidebar"] {
    background: var(--bg-card) !important;
    border-right: 1px solid var(--border) !important;
    transform: none !important;
    width: 280px !important;
    min-width: 280px !important;
}
[data-testid="stSidebar"] > div:first-child { width: 280px !important; }
[data-testid="collapsedControl"] { display: none !important; }
button[kind="header"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
```

## Deployment Commands

```bash
# Deploy to VPS
scp -P 1511 app.py root@45.159.230.42:/opt/ollama-ui/app.py

# Restart Streamlit (kill zombie first)
ssh -p 1511 root@45.159.230.42 "fuser -k 8501/tcp; sleep 2; cd /opt/ollama-ui && source venv/bin/activate && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &"

# Check health
curl -s http://45.159.230.42:8501/_stcore/health

# Test vision API directly
ssh -p 1511 root@45.159.230.42 "curl -s http://localhost:11434/api/chat -d @/tmp/vision_test.json" | jq '.message.content'
```

## Vision Model Test Results

Both models successfully identified an ant image:
- **qwen3-vl:4b**: "black ant carrying a small object with its mandibles"
- **deepseek-ocr**: Detailed description including body segments, coloration, legs, antennae

## Next Steps

1. **Commit sidebar fixes** - CSS changes for forced visibility
2. **Test vision in browser** - User can now upload image and chat
3. **Add streaming responses** - Currently using `stream: False`
4. **Persist chat history** - Database tables exist but unused
