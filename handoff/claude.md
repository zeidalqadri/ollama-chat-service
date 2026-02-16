# Handoff - Session Summary

## Session Stats
- Tool calls: ~45
- Duration: ~25 minutes
- Context pressure: 🟢 LOW
- Date: Feb 16, 2026

## Completed This Session

### 1. Removed vLLM, Simplified to Ollama-Only
- vLLM code already removed from `main.py`
- Updated CLAUDE.md to reflect Ollama-only architecture
- Removed vLLM environment variables and setup docs

### 2. Systemd Services Configured
- `systemd/borak.service` - BORAK FastAPI on port 8012
- `systemd/cloudflared.service` - Cloudflare tunnel service file
- BORAK now runs via systemd (was manual process blocking port)

### 3. Deployment Scripts Created
- `deploy-gpu-vps.sh` - GPU VPS deployment (192.168.0.251)
- `deploy-new-vps.sh` - Fresh VPS migration script

### 4. Cloudflared Tunnel Setup
- Added `@reboot` cron job for auto-start (user lacks sudo for systemd)
- Added borak.roowang.com as main tunnel endpoint
- Kept borak.zeidgeist.com as backup
- Updated cloudflared config with both hostnames

### 5. VPS Services Running
| Service | Status | Method |
|---------|--------|--------|
| BORAK | Active | systemd |
| Ollama | Active | systemd |
| Cloudflared | Running | cron @reboot |

## Key Decisions

1. **Ollama-only** - Removed vLLM hybrid backend for simplicity

2. **roowang.com as main** - borak.roowang.com is primary, zeidgeist.com is backup

3. **Cron for cloudflared** - User `the_bomb` lacks passwordless sudo, so cloudflared runs via cron instead of systemd

4. **Tunnel token limitation** - The cloudflared cert is bound to zeidgeist.com zone, so roowang.com DNS was added manually in Cloudflare dashboard

## VPS Info

| Property | Value |
|----------|-------|
| Host | 192.168.0.251 |
| User | the_bomb |
| SSH Port | 22 |
| Tunnel (main) | borak.roowang.com |
| Tunnel (backup) | borak.zeidgeist.com |
| Tunnel ID | 674690a0-0ebc-4a06-9ab4-238940a0fb1f |

## Files Modified

| File | Change |
|------|--------|
| `CLAUDE.md` | Updated architecture, added roowang.com as main tunnel |
| `systemd/borak.service` | New - BORAK systemd service |
| `systemd/cloudflared.service` | New - Cloudflare tunnel service |
| `deploy-gpu-vps.sh` | New - GPU VPS deployment |
| `deploy-new-vps.sh` | New - Fresh VPS migration |
| `handoff/claude.md` | Session handoff |

## Commands to Verify

```bash
# Check services on VPS
ssh the_bomb@192.168.0.251 "systemctl is-active borak ollama"

# Test main tunnel
curl -s https://borak.roowang.com/health | jq

# Test backup tunnel
curl -s https://borak.zeidgeist.com/health | jq

# View BORAK logs
ssh the_bomb@192.168.0.251 "journalctl -u borak -f"

# View cloudflared logs
ssh the_bomb@192.168.0.251 "tail -20 /tmp/cloudflared.log"
```

## Next Steps

1. No immediate action needed - deployment complete
2. Consider testing image upload/OCR via tunnel
3. If sudo access granted later, convert cloudflared to systemd service

## Git Commits This Session

- `3c887c6` - refactor(deploy): remove vLLM, add systemd services
- `9cc15a0` - docs: handoff for BORAK systemd deployment

---
_Run /session-save before next clear to preserve important context._
