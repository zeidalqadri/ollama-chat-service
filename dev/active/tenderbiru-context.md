# TenderBiru n8n Bidding System Context

**Last Updated**: 2026-01-28 00:45 MYT (Session 8)

## Current State

### Deployment Status
- **VPS**: 45.159.230.42:5678 (SSH port 1511)
- **n8n Version**: Running, fully configured
- **Databases**:
  - `alumist_n8n` (n8n data) - schema: `n8n`
  - `tenderbiru` (bid data)
- **BORAK API**: 45.159.230.42:8012 (troubleshooting endpoint)

### Working Workflows
| Workflow | ID | Webhook Path | Version | Status |
|----------|------|--------------|---------|--------|
| Harmony Ingest | `8GdOVgHbGoPaT6mM` | `/webhook/harmony/ingest` | **2.0.0** | ✅ Active + Troubleshoot |
| Harmony Process | `NUdhPAanITYV8hTW` | `/webhook/harmony/process` | 1.x | ✅ Active |
| Bid Submission Intake | `DPJT2MQD4WBj7hue` | `/webhook/bid/submit` | 1.x | ✅ Active |
| AI Completeness Analysis | `l2RiR02qed1XaTzX` | `/webhook/bid/analyze` | **2.0.0** | ✅ Active + Retry/Fallback |
| SmartGEP Scraper | `Y4NSaqZEj7yuzk8k` | (cron 6h) | 1.x | ✅ Active + Harmony |
| ePerolehan Handler | `1EPBBLnShfOwJE00` | `/webhook/scraper-complete` | 1.x | ✅ Active + Harmony |
| ePerolehan Trigger | `q8MVSinIsPIK67GR` | (cron 6h) | 1.x | ✅ Active |

### Pending Workflows (Need Testing)
- Technical Review (03)
- Commercial Review (04)
- Management Approval (05)
- Telegram Callback Handler (06)
- Outcome Tracking (07)
- Scheduled Reports (08)

## Session 8 Implementation: Automated Troubleshooting

### New `/api/troubleshoot` Endpoint (BORAK)
**File**: `main.py:195-450`

Routes pipeline failures to appropriate models for diagnosis and recovery:

| Stage | Model | Use Case |
|-------|-------|----------|
| `scrape` | `qwen2.5-coder:7b` | Extract tender data from raw HTML |
| `extract` | `qwen2.5-coder:7b` | Infer missing fields from partial data |
| `analyze` | `gemma2:9b` | Generate fallback scores when AI fails |
| `document` | `deepseek-ocr` | Retry OCR with different approaches |
| `submit` | `qwen2.5-coder:7b` | Analyze submission errors |

**Endpoints**:
- `POST /api/troubleshoot` - Main troubleshooting endpoint
- `GET /api/troubleshoot/models` - List model assignments

### Workflow 09 - Harmony Ingest (v2.0.0)
**New Nodes Added**:
1. `Needs Troubleshoot?` - Checks if tenders array empty but raw_html present
2. `Troubleshoot Extract` - Calls `/api/troubleshoot` with stage=extract
3. `Process Troubleshoot` - Merges recovered data or flags for manual review
4. `Has Failures?` - Checks if any extractions failed
5. `Alert: Extraction Failures` - Telegram notification for failures

**Flow**:
```
Webhook → Validate → [Needs Troubleshoot?]
                        ├─ Yes → Troubleshoot → Process → Store
                        └─ No → Store
Store → Aggregate → [Has Failures?]
                        ├─ Yes → Telegram Alert
                        └─ No → Done
```

### Workflow 02 - AI Completeness Analysis (v2.0.0)
**New Nodes Added**:
1. `Analysis Failed?` - Checks if AI response missing or errored
2. `Check Retry` - Manages retry count
3. `Should Troubleshoot?` - Routes to retry or fallback
4. `AI Analysis Retry` - Second attempt with 240s timeout
5. `Parse Retry Response` - Handles retry result
6. `Retry Failed?` - Routes success or failure
7. `Troubleshoot Analyze` - Calls `/api/troubleshoot` with stage=analyze
8. `Apply Fallback Scores` - Uses recovered data or defaults (50/50/50)
9. `Needs Manual Review?` - Routes to manual review notification
10. `Notify: Manual Review` - Telegram alert for failed analysis

**Flow**:
```
AI Analysis → [Analysis Failed?]
                ├─ No → Parse Response → Update Scores
                └─ Yes → Check Retry → [Should Troubleshoot?]
                                          ├─ Yes → Troubleshoot → Fallback
                                          └─ No → AI Retry → [Retry Failed?]
                                                               ├─ Yes → Troubleshoot
                                                               └─ No → Update Scores
```

## Key Decisions Made

### 1. responseMode Configuration (CRITICAL)
| Workflow Type | responseMode | Reason |
|--------------|--------------|--------|
| With Respond nodes (01, 07) | `responseNode` | Must return structured response |
| Without Respond nodes | **REMOVE** | Default returns `{"message": "Workflow was started"}` |

### 2. n8n Database Schema
- **Schema**: `n8n` (not `public`)
- **Table**: `n8n.workflow_entity`
- Workflows must be updated in `n8n` schema, not `public`

### 3. Troubleshooting Prompts
Each stage has a specific prompt template:
- **Scrape**: Extracts tender fields from raw HTML
- **Extract**: Infers missing fields from partial data
- **Analyze**: Returns simple 0-100 scores for completeness/win_prob/risk

### 4. Telegram Credential
- **Credential ID**: `tenderbirubot`
- **Bot Username**: @TenderBiruBot
- Groups: Intake, Escalation, Wins

### 5. Environment Variables
Added to `/opt/alumist/config/.env`:
```bash
TELEGRAM_INTAKE_GROUP=-1003619116505
TELEGRAM_ESCALATION_GROUP=-1003729943661
TELEGRAM_WINS_GROUP=-1003786299679
BORAK_URL=http://localhost:8012
```

## Database Reference

### PostgreSQL Connection
```bash
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d <database>
```

### Databases & Schemas
| Database | Schema | Purpose |
|----------|--------|---------|
| `alumist_n8n` | `n8n` | n8n workflow data |
| `alumist_n8n` | `public` | Other data (don't use for workflows) |
| `tenderbiru` | `public` | Bid application data |

### Key Tables
- `n8n.workflow_entity` - n8n workflows
- `tenderbiru.raw_tenders` - Scraped tender data
- `tenderbiru.bids` - Processed bid records

## Testing Commands

```bash
# SSH to VPS
ssh -p 1511 root@45.159.230.42

# Test Troubleshoot Endpoint (scrape)
curl -s -X POST http://45.159.230.42:8012/api/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"stage":"scrape","error_data":{"url":"test","error":"Failed"},"context":{"raw_html":"<table><tr><td>ID:</td><td>TND-001</td></tr></table>"}}'

# Test Troubleshoot Endpoint (analyze)
curl -s -X POST http://45.159.230.42:8012/api/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"stage":"analyze","error_data":{"title":"Test Project","client":"Corp","deadline":"2026-03-01","doc_count":2},"context":{}}'

# Check workflow versions in n8n
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d alumist_n8n \
  -c "SELECT id, name, \"versionId\" FROM n8n.workflow_entity WHERE name LIKE '%Harmony%' OR name LIKE '%Completeness%';"

# Check BORAK health
curl -s http://45.159.230.42:8012/health

# Restart n8n
cd /root && source /opt/alumist/config/.env && pkill -f 'n8n start' && nohup n8n start &

# Restart BORAK
pkill -f 'uvicorn main:app.*8012' && cd /opt/ollama-ui && nohup /opt/ollama-ui/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8012 > /var/log/borak.log 2>&1 &
```

## Files Modified (Session 8)

| File | Change |
|------|--------|
| `main.py` | Added `/api/troubleshoot` endpoint, Pydantic models, prompt templates |
| `n8n-bidding-system/workflows/09-harmony-ingest.json` | v2.0.0 with troubleshoot branch |
| `n8n-bidding-system/workflows/02-ai-completeness-analysis.json` | v2.0.0 with retry + fallback |

## Blockers/Issues

### Resolved (Session 8)
1. ~~Analyze troubleshooter returning empty data~~ → Fixed extraction logic for analyze stage
2. ~~Workflows created in wrong schema~~ → Updated existing workflows in `n8n` schema

### Open
1. **Scheduled Reports** - Need to test 08-scheduled-reports.json
2. **Review Workflows** - Untested (03, 04, 05 need Telegram setup verification)
3. **Document Troubleshooter** - `deepseek-ocr` stage untested
4. **Submit Troubleshooter** - Portal submission recovery untested
