# BÖRAK01 - Session Context

**Last Updated:** 2026-01-25 07:30 UTC

## Current State

### Deployment
- **URL:** https://alumist.alumga.com/borak01/
- **VPS:** 45.159.230.42 (SSH port 1511)
- **App Port:** 8012 (changed from 8501 to avoid conflict with Polymarket API)
- **Service:** `systemctl restart ollama-ui`

### Model Stack (Final)
| Model | Size | Purpose |
|-------|------|---------|
| qwen3-coder:30b | 18 GB | Main coder |
| stable-beluga:13b | 7.4 GB | Creative writer |
| deepseek-ocr:latest | 6.7 GB | Vision/OCR |
| gnokit/improve-prompt | 1.6 GB | Prompt optimizer |

**Removed this session:**
- qwen2.5-coder:14b (replaced by stable-beluga for writing)
- qwen3-vl:4b (redundant with deepseek-ocr)

## Key Decisions Made

1. **Port Change:** Moved from 8501 → 8012 because Polymarket ML API was occupying 8501
2. **Model Selection:**
   - Chose `gnokit/improve-prompt` for prompt optimization (gemma-2b based, lightweight)
   - Chose `stable-beluga:13b` for writing over mistral:7b (better creative coherence)

## Features Implemented This Session

### Backend (main.py)
- Session CRUD API (create, rename, list, delete)
- Artifacts API (code snippets, thoughts, explanations)
- Stop generation endpoint

### Frontend (static/*)
- Sessions panel with "+ NEW" button
- Artifacts panel (Code/Thoughts/Explanations categories)
- Stop/Continue generation controls
- Image upload for vision models
- Mobile responsive CSS

## Commits

1. `2146f8b` - feat: add session management, artifacts panel, and UI enhancements

## Testing Done

- Playwright tests verified:
  - Login/Registration flow ✅
  - Chat interface loads ✅
  - Model selector shows correct models ✅
  - Prompt optimizer (improve-prompt) works ✅
  - Writer model (stable-beluga) starts generating ✅ (slow, 13B)

## Files Modified

| File | Changes |
|------|---------|
| main.py | +705 lines - Session/Artifacts APIs |
| static/app.js | +872 lines - UI logic |
| static/index.html | +73 lines - UI elements |
| static/style.css | +384 lines - Styling |
| CLAUDE.md | Port 8501 → 8012 |

## Next Steps

1. Test stable-beluga:13b with longer timeout (slow generation)
2. Consider adding model descriptions in dropdown
3. Implement artifact saving from chat responses
4. Add session export/import feature
