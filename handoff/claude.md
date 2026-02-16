# Handoff - Session Summary

## Session Stats
- Tool calls: ~30
- Duration: ~15 minutes
- Context pressure: 🟢 LOW
- Date: Feb 16, 2026

## Completed This Session

### 1. Removed vLLM, Simplified to Ollama-Only
- vLLM code was already removed from `main.py` (confirmed 0 references)
- Updated CLAUDE.md to reflect Ollama-only architecture
- Removed vLLM environment variables and setup docs

### 2. Systemd Services Configured
Created and deployed service files:
- `systemd/borak.service` - BORAK FastAPI on port 8012
- `systemd/cloudflared.service` - Cloudflare tunnel (not installed via systemd)

### 3. Deployment Scripts Created
- `deploy-gpu-vps.sh` - GPU VPS deployment (192.168.0.251)
- `deploy-new-vps.sh` - Fresh VPS migration script

### 4. VPS Services Running
| Service | Status | Method |
|---------|--------|--------|
| BORAK | Active | systemd |
| Ollama | Active | systemd |
| Cloudflared | Running | Manual + cron @reboot |

### 5. Cloudflared Tunnel Working
- Tunnel ID: `674690a0-0ebc-4a06-9ab4-238940a0fb1f`
- Public URL: https://borak.zeidgeist.com
- Added `@reboot` cron job for auto-start

## Key Decisions

1. **Ollama-only** - Removed vLLM hybrid backend for simplicity. Ollama handles all models.

2. **Manual cloudflared** - User `the_bomb` lacks passwordless sudo, so cloudflared runs via cron instead of systemd.

3. **New VPS IP** - Migrated from 45.159.230.42 to 192.168.0.251 (GPU VPS)

## VPS Info

| Property | Value |
|----------|-------|
| Host | 192.168.0.251 |
| User | the_bomb |
| SSH Port | 22 |
| Tunnel | borak.zeidgeist.com |

## Files Modified

| File | Change |
|------|--------|
| `CLAUDE.md` | Removed vLLM docs, updated architecture |
| `systemd/borak.service` | New - BORAK systemd service |
| `systemd/cloudflared.service` | New - Cloudflare tunnel service |
| `deploy-gpu-vps.sh` | New - GPU VPS deployment |
| `deploy-new-vps.sh` | New - Fresh VPS migration |

## Commands to Verify

```bash
# Check services on VPS
ssh the_bomb@192.168.0.251 "systemctl is-active borak ollama"

# Test tunnel
curl -s https://borak.zeidgeist.com/health | jq

# View BORAK logs
ssh the_bomb@192.168.0.251 "journalctl -u borak -f"

# View cloudflared logs
ssh the_bomb@192.168.0.251 "cat /tmp/cloudflared.log | tail -20"
```

## Next Steps

1. No immediate action needed - deployment complete
2. Consider adding systemd service for cloudflared if user gets sudo access
3. Test image upload/OCR functionality via tunnel

## Git Status

- Commit: `3c887c6` - refactor(deploy): remove vLLM, add systemd services
- Pushed: ✓ origin/master

---
_Run /session-save before next clear to preserve important context._
