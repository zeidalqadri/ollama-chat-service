# Session Handoff - TenderBiru n8n Workflows

**Last Updated**: 2026-01-29 15:50 MYT
**Status**: Session 17 Complete, ready for Session 18

---

## Current Task

**Next session priorities:**
1. WF06 unauthorized reviewer auth validation
2. WF09 Harmony Ingest (apply Code filter + rate limiting)
3. n8n upgrade assessment

**All commits pushed**: `16a51a2` on origin/master

---

## Progress (Session 17)

### Completed
| Task | Result |
|------|--------|
| WF03 Technical Review | **10/10 tests pass** (+2 from skipped) |
| WF04 Commercial Review | **6/6 tests pass** (+2 from skipped) |
| WF09 Harmony diagnosis | Root cause identified, disabled |

### Test Status (All Workflows)

| Workflow | Pass | Skip | Status |
|----------|------|------|--------|
| WF01 Bid Submission | 7/7 | 0 | ✅ Complete |
| WF02 AI Analysis | 7/7 | 0 | ✅ Complete |
| WF03 Technical Review | 10/10 | 0 | ✅ Complete |
| WF04 Commercial Review | 6/6 | 0 | ✅ Complete |
| WF05 Management Approval | 5/6 | 1 | ✅ Working |
| WF06 Callback Handler | 14/15 | 1 | 🔶 Auth pending |
| WF07 Outcome Tracking | 8/8 | 0 | ✅ Complete |
| WF09 Harmony Ingest | - | - | ⚠️ Disabled |

**Total: 57/59 pass, 2 skip** (run tests individually, not as full suite)

---

## Next Steps (Session 18 Priorities)

### 1. WF06 Auth Validation (Medium Priority)
**Goal**: Verify reviewer is authorized to approve the specific review type

**Location**: `n8n-bidding-system/workflows/06-telegram-callback-handler.json`

**Required changes**:
- After `Get Reviewer Info` node, add authorization check
- Verify reviewer.can_review_technical/commercial/management matches review_type
- If unauthorized, send error response via Telegram, skip approval

**Test file**: `test_wf06_callback_handler.py` line 820
```python
@pytest.mark.skip(reason="Authorization validation not yet implemented")
def test_callback_unauthorized_reviewer_rejected(...)
```

### 2. WF09 Harmony Ingest Fix (Low Priority)
**Goal**: Re-enable with flooding prevention

**Location**: `n8n-bidding-system/workflows/09-harmony-ingest.json`

**Root cause identified**:
- IF node "Needs Troubleshoot?" (line 29-53) has n8n v1.121.3 bug
- BORAK troubleshoot API calls timing out (120s timeout)
- All items routed to troubleshoot path → flooding

**Required changes**:
1. Replace IF node with Code filter pattern
2. Add rate limiting (debounce multiple calls)
3. Add circuit breaker for BORAK API failures
4. Test thoroughly before enabling (`active: true`)

### 3. n8n Upgrade Assessment (Low Priority)
**Current**: v1.121.3 with known IF/Switch routing bugs

**Decision**: Workaround pattern established (Code filter), upgrade not urgent
- Document upgrade path when ready
- Test workarounds work on newer versions

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

1. **WF06 Auth Skip**: `test_callback_unauthorized_reviewer_rejected` skipped
2. **WF05 AI Skip**: `test_mgmt_ai_assessment_timeout` skipped (timeout handling)
3. **WF09 Disabled**: Harmony Ingest flooding not yet fixed
4. **Full Test Suite**: Times out when running all tests - run individually

---

## Files Modified (Session 17)

All committed and pushed (`43af47b`, `16a51a2`):
- `n8n-bidding-system/workflows/03-technical-review.json`
- `n8n-bidding-system/workflows/04-commercial-review.json`
- `n8n-bidding-system/tests/integration/test_wf03_technical_review.py`
- `n8n-bidding-system/tests/integration/test_wf04_commercial_review.py`
- `dev/active/handoff.md`

VPS is synced with these changes.

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

# Test WF06 (current: 14/15, 1 skip for auth)
pytest integration/test_wf06_callback_handler.py -v --timeout=90

# Test WF09 Harmony (disabled, needs fix first)
pytest integration/test_wf09_harmony_ingest.py -v --timeout=90

# Deploy workflow changes
scp -P 1511 n8n-bidding-system/workflows/*.json root@45.159.230.42:/opt/n8n-bidding-system/workflows/

# Update workflow in n8n database
ssh -p 1511 root@45.159.230.42 "cat /opt/n8n-bidding-system/workflows/06-telegram-callback-handler.json | python3 -c \"
import sys, json, psycopg2
wf = json.load(sys.stdin)
conn = psycopg2.connect('postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/alumist_n8n')
cur = conn.cursor()
cur.execute('''UPDATE n8n.workflow_entity SET nodes = %s, connections = %s, \\\"updatedAt\\\" = NOW() WHERE name LIKE %s''',
    (json.dumps(wf['nodes']), json.dumps(wf['connections']), '%06 - Telegram%'))
conn.commit()
print(f'Updated: {cur.rowcount}')
\" && pm2 restart alumist-n8n"
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
