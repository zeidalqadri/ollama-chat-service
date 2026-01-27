# TenderBiru n8n Bidding System Context

**Last Updated**: 2026-01-27 18:10 MYT (Session 7)

## Current State

### Deployment Status
- **VPS**: 45.159.230.42:5678 (SSH port 1511)
- **n8n Version**: Running, fully configured
- **Databases**: `alumist_n8n` (n8n data), `tenderbiru` (bid data)

### Working Workflows
| Workflow | ID | Webhook Path | Status |
|----------|------|--------------|--------|
| Harmony Ingest | `8GdOVgHbGoPaT6mM` | `/webhook/harmony/ingest` | ✅ Active |
| Harmony Process | `NUdhPAanITYV8hTW` | `/webhook/harmony/process` | ✅ Active |
| Bid Submission Intake | `DPJT2MQD4WBj7hue` | `/webhook/bid/submit` | ✅ Active |
| AI Completeness Analysis | `l2RiR02qed1XaTzX` | `/webhook/bid/analyze` | ✅ Active |
| SmartGEP Scraper | `Y4NSaqZEj7yuzk8k` | (cron 6h) | ✅ Active + Harmony |
| ePerolehan Handler | `1EPBBLnShfOwJE00` | `/webhook/scraper-complete` | ✅ Active + Harmony |
| ePerolehan Trigger | `q8MVSinIsPIK67GR` | (cron 6h) | ✅ Active |

### Pending Workflows (Need Testing)
- Technical Review (03)
- Commercial Review (04)
- Management Approval (05)
- Telegram Callback Handler (06)
- Outcome Tracking (07)
- Scheduled Reports (08)

## Key Decisions Made

### 1. responseMode Configuration (CRITICAL)
| Workflow Type | responseMode | Reason |
|--------------|--------------|--------|
| With Respond nodes (01, 07) | `responseNode` | Must return structured response |
| Without Respond nodes | **REMOVE** | Default returns `{"message": "Workflow was started"}` |

**Error Symptoms:**
- `responseMode: responseNode` + no Respond node = "No Respond to Webhook node found"
- Respond node + no responseMode = "Unused Respond to Webhook node found"

### 2. Telegram Credential
- **Credential ID**: `tenderbirubot`
- **Bot Username**: @TenderBiruBot
- **Token**: `8215108588:AAFDs0fu70iOOl534I4HLbWtpo70c5zdNqk`
- Credential created directly in DB with encrypted data

### 3. Environment Variables
Added to `/opt/alumist/config/.env`:
```bash
TELEGRAM_INTAKE_GROUP=-1003619116505
TELEGRAM_ESCALATION_GROUP=-1003729943661
TELEGRAM_WINS_GROUP=-1003786299679
```

### 4. Scraper Integration
- SmartGEP: Added parallel Harmony Ingest call after "Transform for Supabase"
- ePerolehan: Added parallel Harmony Ingest call after "04-transform-records"
- Both use `continueOnFail: true` to not block existing Supabase flow

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCRAPERS                                  │
├─────────────────────────────────────────────────────────────────┤
│  SmartGEP (port 8086)          ePerolehan (port 8083)           │
│  └─> Transform                  └─> 04-transform-records        │
│      ├─> Supabase                   ├─> Supabase                │
│      └─> Harmony Ingest             └─> Harmony Ingest          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HARMONY PIPELINE                              │
├─────────────────────────────────────────────────────────────────┤
│  /webhook/harmony/ingest                                         │
│  └─> Validate (smartgep|eperolehan|mytender|manual)             │
│      └─> Store to raw_tenders (UPSERT)                          │
│                                                                  │
│  /webhook/harmony/process                                        │
│  └─> Normalize (parse dates, calc priority)                     │
│      └─> Submit to /webhook/bid/submit                          │
│          └─> Mark raw_tender as processed                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BID PIPELINE                                  │
├─────────────────────────────────────────────────────────────────┤
│  /webhook/bid/submit                                             │
│  └─> Validate → Insert bid → Audit log                          │
│      └─> Trigger /webhook/bid/analyze                           │
│          └─> Notify Telegram (Intake group)                     │
│                                                                  │
│  /webhook/bid/analyze                                            │
│  └─> Get bid → OCR docs (if any) → AI Analysis (qwen3:30b)      │
│      └─> Update scores → Audit log                              │
│          └─> If complete: Trigger technical review              │
│          └─> If needs info: Notify Telegram                     │
└─────────────────────────────────────────────────────────────────┘
```

## Database Tables

### tenderbiru.raw_tenders
```sql
source, source_tender_id, source_url, job_id, raw_data (jsonb),
scraped_at, status (pending|processed), processed_at, bid_id
```

### tenderbiru.bids
```sql
id, reference_number, title, client_name, estimated_value, currency,
submission_deadline, status, priority, completeness_score,
win_probability_score, risk_score, ai_analysis_json, missing_sections,
ai_recommendations, document_urls, source, created_at
```

## Credentials Reference

| Credential ID | Type | Purpose |
|---------------|------|---------|
| `postgres-bidding` | Postgres | TenderBiru database |
| `tenderbirubot` | Telegram | Notification bot |

## Testing Commands

```bash
# SSH to VPS
ssh -p 1511 root@45.159.230.42

# Test Harmony Ingest
curl -X POST "http://45.159.230.42:5678/webhook/harmony/ingest" \
  -H "Content-Type: application/json" \
  -d '{"source":"smartgep","tenders":[{"tender_id":"TEST-001","title":"Test","organization":"Corp","closing_date":"28/02/2026"}]}'

# Test Bid Submission (returns bid_id)
curl -X POST "http://45.159.230.42:5678/webhook/bid/submit" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","client_name":"Corp","submission_deadline":"2026-03-01T00:00:00Z"}'

# Test AI Analysis
curl -X POST "http://45.159.230.42:5678/webhook/bid/analyze" \
  -H "Content-Type: application/json" \
  -d '{"bid_id": "<UUID>"}'

# Trigger ePerolehan scraper
curl -X POST 'http://localhost:8083/api/scrape/start' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: epfcl6pJLk3ZKzLs2WPhzpVq77lZ/yAvcKSEcXZU0UA=' \
  -d '{"source": "eperolehan", "mode": "primary", "max_pages": 1}'

# Check scraper status
curl -H 'X-API-Key: epfcl6pJLk3ZKzLs2WPhzpVq77lZ/yAvcKSEcXZU0UA=' \
  'http://localhost:8083/api/scrape/status/<job_id>'

# Check bids with AI scores
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d tenderbiru \
  -c "SELECT reference_number, title, status, completeness_score FROM bids ORDER BY created_at DESC LIMIT 5;"

# Check raw_tenders
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d tenderbiru \
  -c "SELECT source, source_tender_id, status FROM raw_tenders ORDER BY created_at DESC LIMIT 5;"

# Restart n8n
cd /root && source /opt/alumist/config/.env && pkill -f 'n8n start' && nohup n8n start &
```

## Blockers/Issues

### Resolved (Session 7)
1. ~~AI Analysis webhook silent failure~~ → Removed responseMode
2. ~~Telegram notifications not sending~~ → Fixed env var names (TELEGRAM_* not TENDERBIRU_TELEGRAM_*)
3. ~~Bid submission not returning bid_id~~ → Changed to responseMode: responseNode
4. ~~SmartGEP not feeding Harmony~~ → Added parallel Harmony Ingest node
5. ~~ePerolehan not feeding Harmony~~ → Added parallel Harmony Ingest node

### Open
1. **Scheduled Reports** - Need to test 08-scheduled-reports.json
2. **Review Workflows** - Untested (03, 04, 05 need Telegram setup verification)
