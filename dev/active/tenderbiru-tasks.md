# TenderBiru n8n Bidding System Tasks

**Last Updated**: 2026-01-27 16:35 MYT

## Completed Tasks

- [x] Deploy Harmony Pipeline SQL schema
- [x] Import Harmony Ingest workflow
- [x] Import Harmony Process workflow
- [x] Fix webhook silent failure issue (remove responseMode)
- [x] Fix N8N_WEBHOOK_BASE_URL environment variable
- [x] Grant database permissions to alumist user
- [x] Test end-to-end pipeline: Scraper → Ingest → Process → Bid
- [x] Commit n8n-bidding-system files to repo

## In Progress

- [ ] **Verify postgres-bidding credential in n8n UI**
  - Status: Working but should be explicitly verified
  - Action: Check Settings > Credentials in n8n UI
  - Verify it points to: `tenderbiru` database, `alumist` user

## Pending Tasks

### High Priority
- [ ] **Set up Telegram Bot credentials**
  - Create bot via @BotFather on Telegram
  - Get bot token
  - Create Telegram groups (Intake, Escalation, Wins)
  - Get chat IDs for each group
  - Add `Bidding Bot` credential in n8n

- [ ] **Activate Review Workflows**
  - After Telegram setup:
    - 03-technical-review.json
    - 04-commercial-review.json
    - 05-management-approval.json
    - 06-telegram-callback-handler.json

### Medium Priority
- [ ] **Test AI Analysis Workflow**
  - Verify Ollama is running: `curl http://45.159.230.42:11434/api/tags`
  - Check models available: `qwen3-coder:30b`, `deepseek-ocr:latest`
  - Activate 02-ai-completeness-analysis.json

- [ ] **Set up Scheduled Reports**
  - Configure timezone in workflow settings
  - Activate 08-scheduled-reports.json

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

# Check n8n executions
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d alumist_n8n \
  -c "SELECT id, \"workflowId\", status FROM n8n.execution_entity ORDER BY \"startedAt\" DESC LIMIT 5;"

# Check bids created
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d tenderbiru \
  -c "SELECT title, status, priority FROM bids ORDER BY created_at DESC LIMIT 5;"

# Restart n8n with proper env
cd /root && source /opt/alumist/config/.env && pkill -f 'n8n start' && nohup n8n start &
```

## Notes

- n8n API Key in env file differs from what was in process - use the one from `/opt/alumist/config/.env`
- When creating new workflows, NEVER use `responseMode: responseNode` unless you're certain the Respond node will be reached
- Workflow updates via API require only: name, nodes, connections, settings
