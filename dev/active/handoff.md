# Session Handoff - TenderBiru n8n Workflows

**Last Updated**: 2026-01-29 17:30 MYT
**Status**: Session 18 Complete, all priorities addressed

---

## Current Task

**Session 18 Completed:**
1. ✅ WF06 unauthorized reviewer auth validation - **15/15 tests pass**
2. ✅ WF09 Harmony Ingest - Fixed with Code filter + rate limiting, **8/8 tests pass**
3. ✅ n8n upgrade assessment - Documented below

**All commits pushed**: `795581b` on origin/master

---

## Progress (Session 18)

### Completed
| Task | Result |
|------|--------|
| WF06 Auth Validation | **15/15 tests pass** (was 14/15, 1 skip) |
| WF09 Harmony Ingest | **8/8 tests pass** (was disabled) |
| n8n Upgrade Assessment | Documented - upgrade not urgent |

### Test Status (All Workflows)

| Workflow | Pass | Skip | Status |
|----------|------|------|--------|
| WF01 Bid Submission | 7/7 | 0 | ✅ Complete |
| WF02 AI Analysis | 7/7 | 0 | ✅ Complete |
| WF03 Technical Review | 10/10 | 0 | ✅ Complete |
| WF04 Commercial Review | 6/6 | 0 | ✅ Complete |
| WF05 Management Approval | 6/6 | 0 | ✅ Complete |
| WF06 Callback Handler | 15/15 | 0 | ✅ Complete |
| WF07 Outcome Tracking | 8/8 | 0 | ✅ Complete |
| WF09 Harmony Ingest | 8/8 | 0 | ✅ Complete (active) |

**Total: 67/67 pass, 0 skip** - All tests passing!

---

## Session 18 Implementation Details

### WF06 Auth Validation

**Changes made to** `06-telegram-callback-handler.json`:
1. Updated `Get Reviewer Info` query to include permission fields:
   ```sql
   SELECT id, name, email, telegram_username,
          can_review_technical, can_review_commercial, can_approve_management
   FROM reviewers WHERE telegram_chat_id = $1::bigint
   ```
2. Added `Normalize Reviewer` node for empty query handling
3. Added `Filter: Authorized` code filter checking permissions:
   - TECHNICAL reviews → requires `can_review_technical = true`
   - COMMERCIAL reviews → requires `can_review_commercial = true`
   - MANAGEMENT reviews → requires `can_approve_management = true`
4. Added `Filter: Unauthorized` code filter for rejection path
5. Added `Send Unauthorized Error` Telegram node with error message

**Test fix**: `test_callback_unauthorized_reviewer_rejected` now uses unique `telegram_chat_id` to properly test authorization.

### WF09 Harmony Ingest

**Changes made to** `09-harmony-ingest.json`:
1. Replaced `Needs Troubleshoot?` IF node with Code filter pattern
2. Replaced `Has Failures?` IF node with Code filter pattern
3. Added rate limiting in `Filter: Needs Troubleshoot`:
   - Max 3 troubleshoot calls per minute
   - Uses `$getWorkflowStaticData('global')` for state
   - Rate-limited items marked as `status: 'rate_limited'`
4. Added circuit breaker logic in `Process Troubleshoot`:
   - Tracks API failure count
   - Gracefully handles timeouts/errors
5. Increased BORAK API timeout to 90 seconds (was 120s → 30s → 90s)
6. Workflow now `active: true` - enabled and operational

---

## n8n Upgrade Assessment

### Current State
- **Version**: n8n v1.121.3
- **Known Bugs**: IF/Switch nodes incorrectly route all items to first output
- **Status**: All affected workflows converted to Code filter pattern

### Recommendation
**Upgrade not urgent** - workarounds are stable and well-tested.

### Workflows Using Code Filter Pattern
All workflows now use Code filter pattern to avoid IF/Switch bugs:
- WF03 Technical Review (2 filters)
- WF04 Commercial Review (4 filters)
- WF06 Callback Handler (7 filters)
- WF09 Harmony Ingest (3 filters)

### Upgrade Path (When Ready)
1. Check n8n release notes for IF/Switch bug fix (likely v1.40+)
2. Test in staging environment first
3. Verify Code filter pattern still works (backward compatible)
4. Optional: Gradually migrate back to IF/Switch if needed
5. Keep Code filter pattern as reference for future bugs

### Upgrade Command
```bash
# Backup first
ssh -p 1511 root@45.159.230.42 "pg_dump -U alumist alumist_n8n > /opt/backups/n8n_backup_$(date +%Y%m%d).sql"

# Update n8n
npm update -g n8n

# Restart
pm2 restart alumist-n8n && sleep 15

# Verify version
curl -s localhost:5678/api/v1/health | jq '.version'
```

---

## Key Decisions Made

### Code Filter Pattern (n8n v1.121.3 Workaround)
IF/Switch nodes incorrectly route all items to first output.

**Pattern**:
```javascript
// Code filter - return [] to stop, return $input.all() to continue
const data = $input.first().json;
if (condition) {
  return $input.all();  // Continue to next node
}
return [];  // Stop this branch
```

### Rate Limiting Pattern (WF09)
Prevent API flooding using workflow static data:
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
Postgres returning 0 rows means downstream nodes get no input.

**Pattern**: Add Normalize node after query:
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

## Open Issues

1. **Full Test Suite**: Times out when running all tests - run individually
2. No other known issues - all workflows fully operational

---

## Files Modified (Session 18)

All committed and pushed (`795581b`):
- `n8n-bidding-system/workflows/06-telegram-callback-handler.json`
- `n8n-bidding-system/workflows/09-harmony-ingest.json`
- `n8n-bidding-system/tests/integration/test_wf06_callback_handler.py`
- `dev/active/handoff.md`

VPS is synced with workflow changes.

---

## Commands to Run

```bash
# SSH to VPS
ssh -p 1511 root@45.159.230.42

# Activate test environment
cd /opt/n8n-bidding-system/tests && source .venv-vps/bin/activate
export TEST_DB_DSN='postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/tenderbiru'

# Restart n8n (REQUIRED between test batches)
pm2 restart alumist-n8n && sleep 15

# Test WF06 (now: 15/15)
pytest integration/test_wf06_callback_handler.py -v --timeout=90

# Test WF09 Harmony (now: 8/8)
pytest integration/test_wf09_harmony_ingest.py -v --timeout=120

# Enable WF09 Harmony (when ready)
ssh -p 1511 root@45.159.230.42 "psql postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/alumist_n8n -c \"UPDATE n8n.workflow_entity SET active = true WHERE name LIKE '%09 - Harmony%'\" && pm2 restart alumist-n8n"

# Deploy workflow changes
scp -P 1511 n8n-bidding-system/workflows/*.json root@45.159.230.42:/opt/n8n-bidding-system/workflows/
```

---

## VPS Info

| Property | Value |
|----------|-------|
| IP | 45.159.230.42 |
| SSH Port | 1511 |
| n8n Version | 1.121.3 |
| n8n Database | postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/alumist_n8n |
| App Database | postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/tenderbiru |
| n8n Service | pm2 process "alumist-n8n" |
| Telegram Bot | @tenderbirubot (ID: 8215108588) |
| Escalation Group | -1003729943661 |
