# TenderBiru n8n Bidding System Tasks

**Last Updated**: 2026-01-27 17:15 MYT (Session 7)

## Completed Tasks

- [x] Deploy Harmony Pipeline SQL schema
- [x] Import Harmony Ingest workflow
- [x] Import Harmony Process workflow
- [x] Fix webhook silent failure issue (remove responseMode from Harmony workflows)
- [x] Fix N8N_WEBHOOK_BASE_URL environment variable
- [x] Grant database permissions to alumist user
- [x] Test end-to-end pipeline: Scraper → Ingest → Process → Bid
- [x] Commit n8n-bidding-system files to repo
- [x] **Fix AI Completeness Analysis workflow** (Session 7)
  - Removed `responseMode: responseNode` from webhook
  - Tested successfully - bid analyzed in 1m28s
  - AI scoring working: completeness, win_probability, risk_score
- [x] **Fix responseMode across all TenderBiru workflows** (Session 7)
  - Workflows with Respond nodes: use `responseMode: responseNode`
  - Workflows without Respond nodes: no responseMode (use default)
  - Bid Submission now correctly returns bid_id to Harmony Process
- [x] **Verify postgres-bidding credential** (Session 7)
  - Working - successfully creates bids and updates scores

## In Progress

None currently

## Completed Tasks (Session 7 continued)

- [x] **Set up Telegram Bot credentials** ✅
  - Bot: @TenderBiruBot (8215108588)
  - Credential: `tenderbirubot` in n8n database
  - Groups configured:
    - Intake: `-1003619116505`
    - Escalation: `-1003729943661`
    - Wins: `-1003786299679`
  - Environment variables added to `/opt/alumist/config/.env`

## Pending Tasks

### Medium Priority
- [ ] **Set up Scheduled Reports**
  - Configure timezone in workflow settings
  - Verify 08-scheduled-reports.json is working

### Low Priority
- [ ] **Connect SmartGEP Scraper**
  - Configure scraper to POST to `/webhook/harmony/ingest`
  - Test with real tender data

- [ ] **Add ePerolehan Source**
  - Update Validate node to include ePerolehan field mappings
  - Test date parsing for Malaysian date formats

## Quick Commands

```bash
# SSH to VPS
ssh -p 1511 root@45.159.230.42

# Test Harmony Ingest
curl -X POST "http://45.159.230.42:5678/webhook/harmony/ingest" \
  -H "Content-Type: application/json" \
  -d '{"source":"smartgep","tenders":[{"tender_id":"T001","title":"Test"}]}'

# Test AI Analysis
curl -X POST "http://45.159.230.42:5678/webhook/bid/analyze" \
  -H "Content-Type: application/json" \
  -d '{"bid_id": "<UUID>"}'

# Check n8n executions
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d alumist_n8n \
  -c "SELECT id, \"workflowId\", status FROM n8n.execution_entity ORDER BY \"startedAt\" DESC LIMIT 5;"

# Check bids with AI scores
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d tenderbiru \
  -c "SELECT title, status, completeness_score, win_probability_score FROM bids ORDER BY created_at DESC LIMIT 5;"

# Restart n8n with proper env
cd /root && source /opt/alumist/config/.env && pkill -f 'n8n start' && nohup n8n start &
```

## Notes

### responseMode Rules (CRITICAL)
- **Workflows WITH Respond to Webhook nodes**: Use `responseMode: "responseNode"`
  - 01-bid-submission-intake.json
  - 07-outcome-tracking.json
- **Workflows WITHOUT Respond nodes**: Remove `responseMode` entirely
  - 02-ai-completeness-analysis.json
  - 03-technical-review.json
  - 04-commercial-review.json
  - 05-management-approval.json
  - 09-harmony-ingest.json
  - 10-harmony-process.json
- Using wrong mode causes: "Unused Respond to Webhook node" or "No Respond to Webhook node found"

### API Key Note
- n8n process API key may differ from env file
- Check running process: `cat /proc/$(pgrep -f "n8n start" | head -1)/environ | tr "\0" "\n" | grep N8N_API_KEY`
