# TenderBiru n8n Bidding System Context

**Last Updated**: 2026-01-27 16:35 MYT

## Current State

### Deployment Status
- **VPS**: 45.159.230.42:5678 (SSH port 1511)
- **n8n Version**: Running, environment configured
- **Databases**: `alumist_n8n` (n8n data), `tenderbiru` (bid data)

### Working Workflows
| Workflow | ID | Webhook Path | Status |
|----------|------|--------------|--------|
| Harmony Ingest | `8GdOVgHbGoPaT6mM` | `/webhook/harmony/ingest` | ✅ Active |
| Harmony Process | `NUdhPAanITYV8hTW` | `/webhook/harmony/process` | ✅ Active |
| Bid Submission Intake | `DPJT2MQD4WBj7hue` | `/webhook/bid/submit` | ✅ Active |

### Pending Workflows (Need Telegram Setup)
- Technical Review
- Commercial Review
- Management Approval
- Telegram Callback Handler

## Key Decisions Made

### 1. Webhook Response Mode (CRITICAL)
- **Decision**: Remove `responseMode: responseNode` from webhook nodes
- **Reason**: Causes silent failures when Respond node isn't reached
- **Impact**: All webhook workflows should NOT use responseNode mode unless response handling is guaranteed

### 2. Environment Configuration
- **N8N_WEBHOOK_BASE_URL**: Set to `http://localhost:5678` (not a specific webhook path)
- **Location**: `/opt/alumist/config/.env`

### 3. Database Access
- Single `alumist` user has access to both `alumist_n8n` and `tenderbiru` databases
- Grants applied directly via PostgreSQL

## Files Modified This Session

| File | Change |
|------|--------|
| `n8n-bidding-system/workflows/09-harmony-ingest.json` | Removed responseMode, Respond node |
| `n8n-bidding-system/workflows/10-harmony-process.json` | Removed responseMode, Respond node |
| `/opt/alumist/config/.env` (VPS) | Fixed N8N_WEBHOOK_BASE_URL |

## Integration Points

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Scraper Module  │────▶│ Harmony Ingest  │────▶│  raw_tenders    │
│ (SmartGEP etc)  │     │ /harmony/ingest │     │  (PostgreSQL)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌───────────────────────────────┘
                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Harmony Process │────▶│ Bid Submission  │────▶│     bids        │
│ /harmony/process│     │ /bid/submit     │     │  (PostgreSQL)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Blockers/Issues

### Resolved
1. ~~Webhook returning 200 but not executing~~ → Fixed by removing responseMode
2. ~~N8N_WEBHOOK_BASE_URL misconfigured~~ → Fixed in .env file
3. ~~Database permissions for alumist~~ → Granted on tenderbiru

### Open
1. **Telegram credentials** - Need bot token and chat IDs configured
2. **AI models** - Need to verify Ollama models available on VPS
3. **Credential verification** - postgres-bidding should be verified in n8n UI

## Credentials Reference

| Credential Name | Type | Purpose |
|-----------------|------|---------|
| `postgres-bidding` | Postgres | TenderBiru database access |
| (TODO) `Bidding Bot` | Telegram | Notification bot |

## Testing Verification

```bash
# Quick health check
curl -s "http://45.159.230.42:5678/webhook/harmony/process" -X POST \
  -H "Content-Type: application/json" \
  -d '{"source":"test","raw_data":{"title":"Quick Test"}}'
# Expected: {"message":"Workflow was started"}
```
