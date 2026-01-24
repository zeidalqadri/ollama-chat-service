# BÖRAK01 - Task List

**Last Updated:** 2026-01-25 07:30 UTC

## Completed ✅

- [x] Migrate from Streamlit to FastAPI
- [x] Implement JWT cookie authentication
- [x] Add SSE streaming for chat responses
- [x] Create cypherpunk terminal theme
- [x] Add syntax highlighting for code blocks
- [x] Support reverse proxy subpath deployment
- [x] Add session management API
- [x] Add artifacts panel UI
- [x] Add stop/continue generation controls
- [x] Change port from 8501 to 8012
- [x] Remove qwen2.5-coder:14b, qwen3-vl:4b
- [x] Add gnokit/improve-prompt model
- [x] Add stable-beluga:13b writer model
- [x] Test prompt optimizer - working
- [x] Test writer model - starts generating (slow)

## In Progress 🔄

- [ ] Full testing of stable-beluga:13b (needs longer timeout)

## Pending 📋

### High Priority
- [ ] Implement artifact extraction from responses
- [ ] Add model descriptions/tooltips in selector
- [ ] Add loading indicator for slow models

### Medium Priority
- [ ] Session export/import (JSON)
- [ ] Chat history search
- [ ] Keyboard shortcuts (Ctrl+Enter to send)

### Low Priority
- [ ] Dark/light theme toggle
- [ ] Custom system prompts per model
- [ ] Token usage display

## Deployment Commands

```bash
# Deploy to VPS
scp -P 1511 main.py static/* root@45.159.230.42:/opt/ollama-ui/
ssh -p 1511 root@45.159.230.42 "systemctl restart ollama-ui"

# Check health
curl -s https://alumist.alumga.com/borak01/health

# Check models
curl -s https://alumist.alumga.com/borak01/api/models

# Manage models on VPS
ssh -p 1511 root@45.159.230.42 "ollama list"
ssh -p 1511 root@45.159.230.42 "ollama pull <model>"
ssh -p 1511 root@45.159.230.42 "ollama rm <model>"
```
