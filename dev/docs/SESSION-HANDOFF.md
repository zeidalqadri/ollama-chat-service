# BÖRAK01 Web App - Session Handoff

**Last Updated:** 2026-01-26 12:45 UTC
**Session Status:** REQUIRES BACKEND RESTART

## Current State

### What Was Done This Session

1. **Pivoted from iOS Ad-Hoc Distribution to Responsive Web App**
   - User wanted to share BÖRAK01 with colleagues
   - Initially explored iOS Ad Hoc distribution (UDID collection via n8n)
   - User decided web app is simpler - works everywhere, no app store

2. **Redesigned Web App with Jony Ive Design System**
   - Replaced "cypherpunk terminal" aesthetic with clean, minimal design
   - Ported iOS Theme.swift colors and tokens to CSS
   - Created `style-ive.css` with new design system
   - Updated `index.html` with cleaner markup
   - Added message bubbles to chat UI

3. **Added Inline Attachment Button**
   - User couldn't find image upload (was hidden in sidebar on mobile)
   - Added 📎 paperclip button next to chat input
   - Shows inline preview above input when image attached
   - Syncs with sidebar upload state

4. **Implemented Time-Bound Image Storage (1 day retention)**
   - User wanted images downloadable and viewable in chat history
   - Added `message_attachments` table in SQLite
   - Images saved to `/opt/ollama-ui/uploads/`
   - Auto-cleanup of expired attachments on startup
   - API endpoint `/api/attachments/{id}` to serve images
   - Images displayed inline in chat messages

## Files Modified

### Backend (`main.py`)
- Added `UPLOADS_DIR` and `IMAGE_RETENTION_DAYS` (1 day) config
- Added `message_attachments` table schema
- Added functions: `save_attachment()`, `get_attachment()`, `get_message_attachments()`, `link_attachment_to_message()`, `cleanup_expired_attachments()`
- Updated `load_chat_history()` to include attachments
- Updated `/api/chat/send` to save images and link to messages
- Updated `/api/chat/history` to return attachment URLs
- Added `/api/attachments/{id}` and `/api/attachments/{id}/download` endpoints
- Added cleanup on startup via lifespan handler

### Frontend (`static/`)
- `style-ive.css` - New Jony Ive design system (1600+ lines)
- `style-old.css` - Backup of original cypherpunk theme
- `index.html` - Updated with new design, inline attach button
- `index-old.html` - Backup of original HTML
- `app.js` - Added inline attachment handlers, message attachments display

## Critical: Backend Configuration

### Cookie Security Setting
The `secure` cookie flag must match your deployment:
- `secure=False` for HTTP access (development, local testing)
- `secure=True` for HTTPS/production

This was fixed in `main.py` line 1102. Without this, cookies won't be set over HTTP and all authenticated API calls will return 401.

### Firewall
Port 8012 must be open:
```bash
ufw allow 8012/tcp
```

### Backend Restart
```bash
ssh -p 1511 root@45.159.230.42
pkill -f uvicorn
cd /opt/ollama-ui
nohup uvicorn main:app --host 0.0.0.0 --port 8012 > /var/log/ollama-ui.log 2>&1 &
```

This will:
- Create the `message_attachments` table
- Create the `uploads/` directory
- Run `cleanup_expired_attachments()` on startup

## Architecture: Image Storage Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Image Upload Flow                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. User attaches image (click 📎 or sidebar upload)        │
│  2. Browser converts to base64                               │
│  3. Sent with message to /api/chat/send                     │
│  4. Backend:                                                 │
│     a. Decode base64, detect mime type                      │
│     b. Save to /opt/ollama-ui/uploads/{filename}            │
│     c. Record in message_attachments table                  │
│     d. Link attachment to message_id                        │
│     e. Pass base64 to Ollama for vision processing          │
│  5. Response streamed back                                   │
│  6. On /api/chat/history, attachments included with URLs    │
│  7. Frontend displays images inline with download option    │
│                                                              │
│  Auto-cleanup: After 24 hours, file + DB record deleted     │
│                (runs on server startup)                      │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema Addition

```sql
CREATE TABLE message_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,                    -- Links to chat_history.id
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,                -- Unique filename on disk
    original_name TEXT,                    -- User's original filename
    mime_type TEXT,                        -- image/png, image/jpeg, etc.
    file_size INTEGER,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,              -- When to auto-delete
    FOREIGN KEY (message_id) REFERENCES chat_history(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## API Endpoints Added

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/attachments/{id}` | Serve image file (checks ownership + expiry) |
| GET | `/api/attachments/{id}/download` | Download with Content-Disposition header |

## Chat History Response Format (Updated)

```json
{
  "messages": [
    {
      "id": 123,
      "role": "user",
      "content": "What's in this image?",
      "model": "qwen3-vl",
      "is_partial": false,
      "attachments": [
        {
          "id": 45,
          "url": "/api/attachments/45",
          "download_url": "/api/attachments/45/download",
          "mime_type": "image/png",
          "expires_at": "2026-01-27T12:00:00"
        }
      ]
    }
  ]
}
```

## Git Commits This Session

1. `ddbd69e` - feat(web): redesign with Jony Ive design system
2. `811d4dd` - feat(web): add inline attachment button next to chat input
3. `aa79cd2` - feat: add time-bound image storage (1-day retention)

## Configuration Options

| Env Var | Default | Description |
|---------|---------|-------------|
| `IMAGE_RETENTION_DAYS` | 1 | Days to keep uploaded images |

## Next Steps (Suggested)

1. **Restart backend** to apply attachment system
2. **Test image upload** - verify storage and display
3. **Test expiry** - confirm cleanup works (set retention to minutes for testing)
4. Consider adding:
   - File type restrictions (already limited to images)
   - Max file size limit
   - Image compression on upload
   - Periodic cleanup job (currently only on startup)

## Repositories

| Repo | Location | Status |
|------|----------|--------|
| Backend | `https://github.com/zeidalqadri/ollama-chat-service.git` | Pushed (aa79cd2) |
| iOS | `ssh://root@45.159.230.42:1511/opt/BORAK01-iOS.git` | Stable |
| VPS Backend | `/opt/ollama-ui/` | Files deployed, needs restart |

## VPS Access

```bash
ssh -p 1511 root@45.159.230.42
# Backend: /opt/ollama-ui/
# Uploads: /opt/ollama-ui/uploads/
# Logs: /var/log/ollama-ui.log
# Database: /opt/ollama-ui/users.db
```

## No Uncommitted Changes

All changes committed and pushed to GitHub.
