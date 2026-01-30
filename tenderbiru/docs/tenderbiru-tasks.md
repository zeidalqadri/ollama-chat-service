# TenderBiru n8n Bidding System Tasks

**Last Updated**: 2026-01-29 17:30 MYT (Session 18)
**Status**: All workflows operational, 67/67 tests passing

## Current State

**All priority tasks completed.** The TenderBiru n8n bidding system is fully operational.

| Workflow | Tests | Status |
|----------|-------|--------|
| WF01 Bid Submission | 7/7 | ✅ Complete |
| WF02 AI Analysis | 7/7 | ✅ Complete |
| WF03 Technical Review | 10/10 | ✅ Complete |
| WF04 Commercial Review | 6/6 | ✅ Complete |
| WF05 Management Approval | 6/6 | ✅ Complete |
| WF06 Callback Handler | 15/15 | ✅ Complete |
| WF07 Outcome Tracking | 8/8 | ✅ Complete |
| WF09 Harmony Ingest | 8/8 | ✅ Complete (active) |
| **Total** | **67/67** | **100%** |

---

## Completed Tasks

### Sessions 11-18 (Jan 28-29, 2026)

#### Session 18
- [x] WF06 unauthorized reviewer auth validation (15/15 tests)
- [x] WF09 Harmony Ingest fix with rate limiting (8/8 tests)
- [x] n8n upgrade assessment (documented - upgrade not urgent)
- [x] All changes committed and pushed (`795581b`)

#### Session 17
- [x] WF03 Technical Review - Code filter pattern (10/10 tests)
- [x] WF04 Commercial Review - Code filter pattern (6/6 tests)
- [x] Notification logging improvements

#### Session 16
- [x] WF05 Management Approval telegram_notifications logging
- [x] WF07 Outcome Tracking completion

#### Sessions 11-15
- [x] Discovered n8n IF/Switch bug (v1.121.3)
- [x] Developed Code filter pattern workaround
- [x] Fixed webhook body reference issues
- [x] Fixed empty query result handling
- [x] Implemented telegram message_id tracking

### Sessions 7-10 (Earlier)
- [x] Deploy Harmony Pipeline SQL schema
- [x] Import all workflows (01-10)
- [x] Fix webhook silent failure issue
- [x] Create TDD test infrastructure (164 tests)
- [x] Deploy tests to VPS
- [x] Fix n8n connectivity issues

---

## Key Patterns Implemented

### Code Filter Pattern (n8n v1.121.3 Workaround)
IF/Switch nodes incorrectly route all items to first output.
```javascript
// Return [] to stop, return $input.all() to continue
const data = $input.first().json;
if (condition) {
  return $input.all();
}
return [];
```

### Rate Limiting (WF09)
```javascript
const now = Date.now();
let staticData = $getWorkflowStaticData('global');
if (!staticData.calls) staticData.calls = [];
staticData.calls = staticData.calls.filter(t => now - t < 60000);
if (staticData.calls.length >= 3) {
  return [{ json: { ...item, status: 'rate_limited' } }];
}
staticData.calls.push(now);
return $input.all();
```

### Empty Query Handling
```javascript
const items = $input.all();
if (items.length === 0 || !items[0].json.id) {
  return [{ json: { id: null, no_reviewer: true } }];
}
return items;
```

---

## Test Commands

```bash
# SSH to VPS
ssh -p 1511 root@45.159.230.42

# Activate test environment
cd /opt/n8n-bidding-system/tests && source .venv-vps/bin/activate
export TEST_DB_DSN='postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/tenderbiru'

# ALWAYS restart n8n before tests
pm2 restart alumist-n8n && sleep 15

# Run individual workflow tests
pytest integration/test_wf01_bid_submission.py -v --timeout=60
pytest integration/test_wf06_callback_handler.py -v --timeout=90
pytest integration/test_wf09_harmony_ingest.py -v --timeout=120

# Note: Full suite may timeout - run workflows individually
```

---

## Future Considerations

### n8n Upgrade (When Ready)
- Current: v1.121.3 with IF/Switch bug
- Code filter pattern is stable workaround
- Upgrade not urgent - test in staging first
- See handoff.md for upgrade commands

### Model Configuration
- Testing: `qwen2.5-coder:7b` (faster)
- Production: `qwen3-coder:30b` (more capable)
- Change in `/home/n8n/.env`: `TENDERBIRU_ANALYSIS_MODEL=...`

---

## VPS Quick Reference

| Property | Value |
|----------|-------|
| IP | 45.159.230.42 |
| SSH Port | 1511 |
| n8n Port | 5678 |
| n8n Service | pm2 `alumist-n8n` |
| App Database | tenderbiru |
| n8n Database | alumist_n8n (schema: `n8n`) |
