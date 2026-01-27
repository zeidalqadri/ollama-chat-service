# TenderBiru n8n Bidding System Tasks

**Last Updated**: 2026-01-28 06:00 MYT (Session 9)

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
- [x] Implement Automated Troubleshooting Pipeline
- [x] Update Workflow 09 - Harmony Ingest to v2.0.0
- [x] Update Workflow 02 - AI Completeness Analysis to v2.0.0
- [x] Fix analyze troubleshooter empty data issue
- [x] Deploy and test on VPS

### Session 9
- [x] **Create TDD Test Infrastructure** ✅
  - Created `n8n-bidding-system/tests/` with 24 files, 6,700 lines
  - 164 test functions covering all 10 workflows
  - Unit tests, integration tests, E2E tests, factories, mocks

- [x] **Run Unit Tests** ✅
  - 82/82 tests PASS (100%)
  - Callback parsing, status transitions, reviewer assignment

- [x] **Deploy Tests to VPS** ✅
  - Tests at `/opt/n8n-bidding-system/tests/`
  - Virtual env at `.venv-vps/`
  - DB connection working

- [x] **Run Integration Tests (WF03)** ✅
  - 2/10 tests PASS
  - 8 tests reveal workflow gaps (TDD RED phase complete)

## In Progress

None currently

## Pending Tasks - Session 10

### Step 1: Fix Test Infrastructure (15 min)
Update ALL integration test files with:
```python
import time
WORKFLOW_WAIT_SECONDS = 3

# After every webhook call:
response = n8n_client.post("/technical-review", json={...})
time.sleep(WORKFLOW_WAIT_SECONDS)

# In SQL queries use ::uuid cast:
db_cursor.execute("SELECT * FROM reviews WHERE bid_id = %s::uuid", (str(bid_id),))
```

**Files to update**:
- `test_wf01_bid_submission.py`
- `test_wf02_ai_analysis.py`
- `test_wf04_commercial_review.py`
- `test_wf05_management_approval.py`
- `test_wf06_callback_handler.py`
- `test_wf07_outcome_tracking.py`
- `test_wf09_harmony_ingest.py`
- `test_wf10_harmony_process.py`

### Step 2: Re-run All Integration Tests (30 min)
```bash
ssh -p 1511 root@45.159.230.42
cd /opt/n8n-bidding-system/tests
export TEST_DB_DSN='postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/tenderbiru'
source .venv-vps/bin/activate
pytest integration/ -v --tb=line 2>&1 | tee test-results.log
```

This will show which workflow features are missing (TDD RED phase).

### Step 3: Fix Workflow Gaps (1-2 hours)
Based on failing tests, update workflows to:

| Gap | Fix Required | Workflow |
|-----|--------------|----------|
| No bid status update | Add UPDATE bids SET status after review created | WF03, WF04, WF05 |
| No telegram_notifications logging | Add INSERT into telegram_notifications after sendMessage | WF03, WF04, WF05 |
| No audit_log entries | Add INSERT into audit_log for actions | All |
| No escalation on missing reviewer | Add IF node to check reviewer found | WF03, WF04, WF05 |
| Accepts invalid bid_ids | Add validation node before processing | All |

### Step 4: Commit and Push (5 min)
```bash
git add n8n-bidding-system/tests/
git commit -m "feat(tests): add TDD test suite for TenderBiru workflows

- 82 unit tests for callback parsing, status transitions, reviewer assignment
- 78 integration tests for all 10 workflows
- Test fixtures, factories, and mocks for Telegram/Ollama
- VPS test environment setup at /opt/n8n-bidding-system/tests/

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git push
```

### Step 5: Update Handoff (5 min)
Create `dev-docs/handoff-2026-01-28-session9.md`

## Quick Reference

### Test Commands
```bash
# Local unit tests
source n8n-bidding-system/tests/.venv/bin/activate
pytest n8n-bidding-system/tests/unit/ -v

# VPS integration tests
ssh -p 1511 root@45.159.230.42 "cd /opt/n8n-bidding-system/tests && export TEST_DB_DSN='postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/tenderbiru' && source .venv-vps/bin/activate && pytest integration/test_wf03_technical_review.py -v"

# Single test
pytest integration/test_wf03_technical_review.py::TestTechnicalReviewAssignment::test_technical_review_assigns_reviewer -v
```

### Workflow Webhook Paths
| Workflow | Path |
|----------|------|
| Bid Submission | `/webhook/bid/submit` |
| AI Analysis | `/webhook/bid/analyze` |
| Technical Review | `/webhook/bid/technical-review` |
| Commercial Review | `/webhook/bid/commercial-review` |
| Management Approval | `/webhook/bid/management-approval` |
| Telegram Callback | `/webhook/telegram-callback` |
| Harmony Ingest | `/webhook/harmony/ingest` |
| Harmony Process | `/webhook/harmony/process` |

### Database
```bash
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d tenderbiru
```

## Notes

### TDD Philosophy
- **RED**: Tests fail (document expected behavior) ← WE ARE HERE
- **GREEN**: Minimal code to pass tests
- **REFACTOR**: Clean up while tests pass

The 8 failing WF03 tests are the "RED" phase - they document what the workflow SHOULD do. Next session will implement the fixes (GREEN phase).

### Files Modified This Session
All files in `n8n-bidding-system/tests/` are new this session.
