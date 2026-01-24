# BÖRAK Tasks

**Last Updated**: 2026-01-25 00:35 UTC

## Completed ✅

- [x] Apply cypherpunk terminal aesthetic
- [x] Fix sidebar collapse button issues
- [x] Force sidebar always visible
- [x] Implement streaming responses
- [x] Add chat persistence (SQLite + ChromaDB)
- [x] Add crash recovery (stream cache)
- [x] Fix rerun loop bug
- [x] Add JS-based panel toggle
- [x] Add UI lock during streaming
- [x] Install ChromaDB on VPS
- [x] Implement background generation (survives WebSocket drops)
- [x] Fix indentation bug (canvas_col inside chat_col)
- [x] Add generation recovery on reconnect

## In Progress 🔄

- [ ] Commit and push all changes
  - Status: Ready to commit (significant changes since last push)

## Pending 📋

### High Priority
- [ ] Test background generation recovery (refresh mid-generation)
- [ ] Test vision models with actual images
- [ ] Add STOP button to cancel generation

### Medium Priority
- [ ] Implement semantic search using ChromaDB embeddings
- [ ] Add chat export (JSON/Markdown)
- [ ] Add token count display

### Low Priority
- [ ] Add system prompt customization
- [ ] Add temperature/top_p controls
- [ ] Multiple chat sessions per user

## Bugs Fixed This Session

| Bug | Symptom | Fix |
|-----|---------|-----|
| WebSocket drop | Response lost mid-generation | Background thread + file persistence |
| Rerun loop | Infinite refresh after response | Removed st.rerun(), use polling |
| Panel interrupt | Clicking HIDE killed response | JS toggle instead of Python button |
| Layout broken | Login form in OUTPUT column | Fixed canvas_col indentation (8→4 spaces) |
