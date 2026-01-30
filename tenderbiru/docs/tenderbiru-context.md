# TenderBiru n8n Bidding System Context

**Last Updated**: 2026-01-29 17:30 MYT (Session 18)
**Status**: All workflows operational, 67/67 tests passing

## Current State

### Deployment Status
- **VPS**: 45.159.230.42:5678 (SSH port 1511)
- **n8n Version**: 1.121.3 running via pm2 (`alumist-n8n`)
- **Databases**:
  - `alumist_n8n` (n8n data) - schema: `n8n` (IMPORTANT: not `public`)
  - `tenderbiru` (bid data) - schema: `public`
- **BORAK API**: 45.159.230.42:8012 (troubleshooting endpoint)
- **Analysis Model**: `qwen2.5-coder:7b` (testing) / `qwen3-coder:30b` (production)

### Working Workflows (All Active)
| Workflow | ID | Webhook Path | Tests |
|----------|------|--------------|-------|
| 01-Bid Submission Intake | `DPJT2MQD4WBj7hue` | `/webhook/bid/submit` | 7/7 |
| 02-AI Completeness Analysis | `CB139e0Wa5eD5CPq` | `/webhook/bid/analyze` | 7/7 |
| 03-Technical Review | `pDIbeNqprrxiMEgy` | `/webhook/bid/technical-review` | 10/10 |
| 04-Commercial Review | `KwxxL1JIv4VVx2q8` | `/webhook/bid/commercial-review` | 6/6 |
| 05-Management Approval | `FBritKEXzO0e9Hzt` | `/webhook/bid/management-approval` | 6/6 |
| 06-Telegram Callback | `w0Y4W8pXU7Sendo9` | `/webhook/telegram-callback` | 15/15 |
| 07-Outcome Tracking | `x1YtWN6JwGbuasDh` | `/webhook/bid/outcome` | 8/8 |
| 09-Harmony Ingest | `7fq1nNzavCYeAeYf` | `/webhook/harmony/ingest` | 8/8 |
| 10-Harmony Process | `NUdhPAanITYV8hTW` | `/webhook/harmony/process` | N/A |

---

## Key Technical Patterns

### Code Filter Pattern (n8n v1.121.3 Bug Workaround)

**Problem**: IF/Switch nodes incorrectly route all items to first output in n8n v1.121.3.

**Solution**: Use Code nodes as filters instead:
```javascript
// Code filter - return [] to stop, return $input.all() to continue
const data = $input.first().json;
if (condition) {
  return $input.all();  // Continue to next node
}
return [];  // Stop this branch
```

**Affected workflows**: WF03, WF04, WF06, WF09 (all converted)

### Rate Limiting Pattern (WF09)

Prevents API flooding using workflow static data:
```javascript
const now = Date.now();
const rateLimitWindow = 60000; // 1 minute
const maxCallsPerWindow = 3;

let staticData = $getWorkflowStaticData('global');
if (!staticData.calls) staticData.calls = [];
staticData.calls = staticData.calls.filter(t => now - t < rateLimitWindow);

if (staticData.calls.length >= maxCallsPerWindow) {
  return [{ json: { ...item, status: 'rate_limited' } }];
}
staticData.calls.push(now);
return $input.all();
```

### Empty Query Result Handling

**Problem**: Postgres returning 0 rows means downstream nodes get no input.

**Solution**: Add Normalize node after query:
```javascript
const items = $input.all();
if (items.length === 0 || !items[0].json.id) {
  return [{ json: { id: null, no_reviewer: true } }];
}
return items;
```

### Telegram message_id Reference

n8n Telegram node returns nested structure:
```javascript
// Correct
$('Send Review Request').first().json.result.message_id

// Wrong (undefined)
$json.message_id
```

### Webhook Body After Intermediate Nodes

After UPDATE queries, `$json` is the UPDATE result, not webhook body:
```javascript
// Correct
$('Webhook: Commercial Review').first().json.body?.bid_id

// Wrong (undefined after UPDATE)
$json.body?.bid_id
```

---

## Database Credentials

```bash
# TenderBiru database
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d tenderbiru

# n8n database (NOTE: workflows are in 'n8n' schema, not 'public')
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d alumist_n8n
# Query workflows: SELECT * FROM n8n.workflow_entity;
# Query webhooks: SELECT * FROM n8n.webhook_entity;
```

---

## Test Environment

### VPS Test Setup
```bash
# SSH to VPS
ssh -p 1511 root@45.159.230.42

# Go to test directory
cd /opt/n8n-bidding-system/tests
source .venv-vps/bin/activate
export TEST_DB_DSN='postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/tenderbiru'

# IMPORTANT: Always restart n8n before running tests
pm2 restart alumist-n8n && sleep 15

# Run individual workflow tests (recommended)
pytest integration/test_wf01_bid_submission.py -v --timeout=60
pytest integration/test_wf06_callback_handler.py -v --timeout=90
pytest integration/test_wf09_harmony_ingest.py -v --timeout=120
```

### Test HTTP Client Configuration
```python
# From conftest.py
N8N_WEBHOOK_URL = f"http://{VPS_HOST}:{VPS_N8N_PORT}/webhook/bid"
# n8n_client.post("/submit") → POST http://45.159.230.42:5678/webhook/bid/submit
```

---

## Troubleshooting

### Issue: Webhook Times Out
**Symptoms**: `httpx.ReadTimeout: timed out`
**Solutions**:
```bash
# 1. Check stuck executions
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -U alumist -d alumist_n8n -h localhost -c \
  "SELECT COUNT(*) FROM n8n.execution_entity WHERE status = 'running';"

# 2. Clear stuck executions
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -U alumist -d alumist_n8n -h localhost -c \
  "UPDATE n8n.execution_entity SET status = 'crashed' WHERE status = 'running';"

# 3. Restart n8n
pm2 restart alumist-n8n && sleep 15
```

### Issue: Workflow Registered But Not Responding
**Symptoms**: 404 "webhook not registered" despite showing in database
**Solution**: Restart n8n - webhooks load at startup only

### Issue: Tests Pass Individually But Fail in Suite
**Cause**: Full suite may timeout
**Solution**: Run individual workflow test files

---

## Quick Reference Commands

```bash
# SSH to VPS
ssh -p 1511 root@45.159.230.42

# Check n8n status
pm2 status alumist-n8n
curl -s http://localhost:5678/healthz

# Check workflow registrations
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -U alumist -d alumist_n8n -h localhost -c \
  "SELECT \"webhookPath\", method, \"workflowId\" FROM n8n.webhook_entity WHERE \"webhookPath\" LIKE 'bid%';"

# Test webhook directly
curl -s -m 30 'http://localhost:5678/webhook/bid/submit' -X POST \
  -H 'Content-Type: application/json' \
  -d '{"title": "Test", "client_name": "Test", "submission_deadline": "2026-02-15T00:00:00Z"}'

# Check recent bids
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -U alumist -d tenderbiru -h localhost -c \
  "SELECT id, title, status, reference_number FROM bids ORDER BY created_at DESC LIMIT 5;"

# View n8n logs
pm2 logs alumist-n8n --lines 30

# Sync workflow files to VPS
scp -P 1511 n8n-bidding-system/workflows/*.json root@45.159.230.42:/opt/n8n-bidding-system/workflows/
```

---

## Related Documentation

- **handoffs/**: Detailed session handoffs with implementation specifics
- **tenderbiru-tasks.md**: Task completion history
- **../workflows/**: Workflow JSON files
- **../tests/**: Integration test suite
