# TenderBiru n8n Bidding System Tasks

**Last Updated**: 2026-01-28 00:45 MYT (Session 8)

## Completed Tasks

### Session 7
- [x] Deploy Harmony Pipeline SQL schema
- [x] Import Harmony Ingest workflow
- [x] Import Harmony Process workflow
- [x] Fix webhook silent failure issue (remove responseMode from Harmony workflows)
- [x] Fix N8N_WEBHOOK_BASE_URL environment variable
- [x] Grant database permissions to alumist user
- [x] Test end-to-end pipeline: Scraper → Ingest → Process → Bid
- [x] Commit n8n-bidding-system files to repo
- [x] Fix AI Completeness Analysis workflow
- [x] Fix responseMode across all TenderBiru workflows
- [x] Verify postgres-bidding credential
- [x] Set up Telegram Bot credentials (@TenderBiruBot)
- [x] Connect SmartGEP Scraper to Harmony Pipeline
- [x] Add ePerolehan Source to Harmony Pipeline

### Session 8
- [x] **Implement Automated Troubleshooting Pipeline** ✅
  - Added `/api/troubleshoot` endpoint to BORAK (main.py)
  - 5 troubleshooting stages: scrape, extract, analyze, document, submit
  - Model routing: qwen2.5-coder:7b, gemma2:9b, deepseek-ocr
  - Prompt templates for each failure type

- [x] **Update Workflow 09 - Harmony Ingest to v2.0.0** ✅
  - Added extraction troubleshoot branch
  - Calls `/api/troubleshoot` when tenders empty but raw_html available
  - Merges recovered data or flags for manual review
  - Telegram alerts for extraction failures
  - Updated in `n8n.workflow_entity` (id: `8GdOVgHbGoPaT6mM`)

- [x] **Update Workflow 02 - AI Completeness Analysis to v2.0.0** ✅
  - Added retry logic with 240s timeout
  - Fallback to troubleshoot endpoint if retry fails
  - Default scores (50/50/50) with NEEDS_MANUAL_REVIEW status
  - Separate Telegram alerts for manual review vs needs-info
  - Updated in `n8n.workflow_entity` (id: `l2RiR02qed1XaTzX`)

- [x] **Fix analyze troubleshooter empty data issue** ✅
  - Fixed extraction logic in `run_troubleshoot()` for analyze stage
  - Now correctly returns `{completeness_score, win_probability, risk_score}`

- [x] **Deploy and test on VPS** ✅
  - BORAK service restarted with new endpoint
  - Workflows updated directly in n8n PostgreSQL (`n8n` schema)
  - Verified scrape troubleshooter: extracts tender fields from HTML
  - Verified analyze troubleshooter: returns fallback scores

## In Progress

None currently

## Pending Tasks

### High Priority
- [ ] **Test end-to-end troubleshooting flow**
  - Send request with empty tenders + raw_html to Harmony Ingest
  - Verify troubleshooter extracts data
  - Confirm recovered tender proceeds through pipeline

### Medium Priority
- [ ] **Set up Scheduled Reports**
  - Configure timezone in workflow settings
  - Verify 08-scheduled-reports.json is working

- [ ] **Test Document Troubleshooter**
  - Test deepseek-ocr stage with failed OCR scenario
  - Verify retry logic works

- [ ] **Test Submit Troubleshooter**
  - Test qwen2.5-coder:7b for portal error analysis
  - Verify suggested corrections are useful

### Low Priority
- [ ] **Add BORAK_URL to n8n environment**
  - Currently hardcoded as fallback `http://localhost:8012`
  - Should be in `/opt/alumist/config/.env`

- [ ] **Test Review Workflows (03, 04, 05)**
  - Verify Telegram notification routing
  - Test callback handling

## Quick Commands

```bash
# SSH to VPS
ssh -p 1511 root@45.159.230.42

# Test Troubleshoot - Scrape
curl -s -X POST http://45.159.230.42:8012/api/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"stage":"scrape","error_data":{"url":"test","error":"Failed"},"context":{"raw_html":"<table><tr><td>ID:</td><td>TND-001</td></tr><tr><td>Title:</td><td>Road Works</td></tr></table>"}}'

# Test Troubleshoot - Analyze
curl -s -X POST http://45.159.230.42:8012/api/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"stage":"analyze","error_data":{"title":"Test","client":"Corp","deadline":"2026-03-01","doc_count":2},"context":{}}'

# Check workflow versions
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d alumist_n8n \
  -c "SELECT id, name, \"versionId\", json_array_length(nodes) as nodes FROM n8n.workflow_entity WHERE name LIKE '%Harmony Ingest%' OR name LIKE '%Completeness%';"

# Check BORAK logs
tail -50 /var/log/borak.log

# Restart BORAK
pkill -f 'uvicorn main:app.*8012' && cd /opt/ollama-ui && nohup /opt/ollama-ui/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8012 > /var/log/borak.log 2>&1 &
```

## Notes

### n8n Database Schema (CRITICAL)
- Workflows are in `n8n.workflow_entity` NOT `public.workflow_entity`
- Always use `n8n.` prefix when querying or updating workflows
- Workflow IDs:
  - `8GdOVgHbGoPaT6mM` = 09 - Harmony Ingest
  - `l2RiR02qed1XaTzX` = 02 - AI Completeness Analysis

### Troubleshoot Endpoint Response Format
```json
{
  "success": true,
  "stage": "scrape",
  "model_used": "qwen2.5-coder:7b",
  "data": {"tender_id": "...", "title": "..."},
  "diagnosis": "...",
  "confidence": 0.9,
  "needs_manual": false,
  "recovered": true
}
```

### responseMode Rules (CRITICAL)
- **WITH Respond nodes**: Use `responseMode: "responseNode"`
- **WITHOUT Respond nodes**: Remove `responseMode` entirely
