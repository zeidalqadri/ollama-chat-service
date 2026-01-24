# BÖRAK Tasks

**Last Updated**: 2026-01-25 00:15 UTC

## Completed ✅

- [x] Apply cypherpunk terminal aesthetic
- [x] Fix sidebar collapse button issues
- [x] Force sidebar always visible
- [x] Implement streaming responses
- [x] Add chat persistence (SQLite + ChromaDB)
- [x] Add crash recovery (stream cache)
- [x] Fix rerun loop bug (removed st.rerun after streaming)
- [x] Add JS-based panel toggle (no rerun)
- [x] Add UI lock during streaming
- [x] Install ChromaDB on VPS
- [x] Deploy all changes to production

## In Progress 🔄

- [ ] Commit and push all session changes
  - Files: app.py (major changes), dev/ (new docs)
  - Status: Ready to commit

## Pending 📋

### High Priority
- [ ] Test vision models with actual images
- [ ] Add STOP button to cancel generation
- [ ] Test crash recovery (refresh mid-stream)

### Medium Priority
- [ ] Implement semantic search using ChromaDB embeddings
- [ ] Add chat export (JSON/Markdown)
- [ ] Add token count display

### Low Priority
- [ ] VPS disk cleanup (currently 79%, was 97%)
- [ ] Add system prompt customization
- [ ] Add temperature/top_p controls
- [ ] Multiple chat sessions per user

## Bugs to Watch

1. **Ollama API exposed externally** - Should be localhost only, but responding to external requests
2. **Long generation timeouts** - 6+ minute requests may fail
3. **File uploader label warning** - Cosmetic, non-blocking
