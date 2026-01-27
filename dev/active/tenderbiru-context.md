# TenderBiru n8n Bidding System Context

**Last Updated**: 2026-01-28 06:00 MYT (Session 9)

## Current State

### Deployment Status
- **VPS**: 45.159.230.42:5678 (SSH port 1511)
- **n8n Version**: Running via pm2 (`alumist-n8n`)
- **Databases**:
  - `alumist_n8n` (n8n data) - schema: `n8n`
  - `tenderbiru` (bid data) - schema: `public`
- **BORAK API**: 45.159.230.42:8012 (troubleshooting endpoint)

### Database Credentials (CRITICAL)
```bash
# TenderBiru database
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d tenderbiru

# n8n database
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d alumist_n8n
```

### Working Workflows
| Workflow | ID | Webhook Path | Version | Status |
|----------|------|--------------|---------|--------|
| Bid Submission Intake | `DPJT2MQD4WBj7hue` | `/webhook/bid/submit` | 1.x | ✅ Active |
| AI Completeness Analysis | `l2RiR02qed1XaTzX` | `/webhook/bid/analyze` | **2.0.0** | ✅ Active + Retry/Fallback |
| Technical Review | - | `/webhook/bid/technical-review` | 1.x | ✅ Active |
| Commercial Review | - | `/webhook/bid/commercial-review` | 1.x | ✅ Active |
| Management Approval | - | `/webhook/bid/management-approval` | 1.x | ✅ Active |
| Telegram Callback | - | `/webhook/telegram-callback` | 1.x | ✅ Active |
| Harmony Ingest | `8GdOVgHbGoPaT6mM` | `/webhook/harmony/ingest` | **2.0.0** | ✅ Active + Troubleshoot |
| Harmony Process | `NUdhPAanITYV8hTW` | `/webhook/harmony/process` | 1.x | ✅ Active |

## Session 9 Implementation: TDD Test Suite

### TDD Infrastructure Created
**Location**: `n8n-bidding-system/tests/`

```
tests/
├── conftest.py              # 573 lines - fixtures, DB connection, helpers
├── pytest.ini               # Config with workflow markers
├── requirements-test.txt    # pytest, httpx, psycopg2, respx, factory-boy
├── unit/                    # 82 tests - ALL PASS
│   ├── test_callback_parser.py       # Callback data parsing logic
│   ├── test_status_transitions.py    # Bid status state machine
│   └── test_review_assignment.py     # Reviewer assignment logic
├── integration/             # 78 tests - VPS required
│   ├── test_wf01_bid_submission.py
│   ├── test_wf02_ai_analysis.py
│   ├── test_wf03_technical_review.py  # 2/10 PASS
│   ├── test_wf04_commercial_review.py
│   ├── test_wf05_management_approval.py
│   ├── test_wf06_callback_handler.py  # Most complex - 28 tests
│   ├── test_wf07_outcome_tracking.py
│   ├── test_wf09_harmony_ingest.py
│   └── test_wf10_harmony_process.py
├── e2e/
│   └── test_full_approval_flow.py     # End-to-end flow tests
├── factories/
│   ├── bid_factory.py       # Test bid generation
│   └── reviewer_factory.py  # Test reviewer generation
└── mocks/
    ├── telegram_mock.py     # Mock Telegram API
    └── ollama_mock.py       # Mock Ollama API
```

### Test Results
| Category | Passed | Failed | Notes |
|----------|--------|--------|-------|
| Unit Tests | 82/82 | 0 | 100% - All logic tests pass |
| WF03 Integration | 2/10 | 8 | Reveals workflow gaps |

### Key Discoveries from TDD

1. **Webhook Paths**: All bid workflows use `/webhook/bid/` prefix
   - `/webhook/bid/technical-review`
   - `/webhook/bid/commercial-review`
   - `/webhook/bid/management-approval`

2. **Workflows are Async**: Webhooks return `{"message": "Workflow was started"}` immediately
   - Tests need `time.sleep(3)` to wait for workflow completion

3. **UUID Casting**: PostgreSQL needs explicit `::uuid` casts in queries

4. **Workflow Gaps Identified** (failing tests = TDD RED phase):
   | Gap | Impact |
   |-----|--------|
   | No bid status update | Bid stays SUBMITTED after tech review assigned |
   | No telegram_notifications logging | Can't verify notifications in tests |
   | No audit_log entries | Missing audit trail |
   | No escalation on missing reviewer | Silently fails |
   | Accepts invalid bid_ids | Returns 200 even for non-existent bids |

### Files Created (Session 9)
| File | Lines | Purpose |
|------|-------|---------|
| `tests/conftest.py` | 573 | Fixtures, DB connection, helpers |
| `tests/pytest.ini` | 30 | pytest configuration |
| `tests/requirements-test.txt` | 12 | Test dependencies |
| `tests/unit/test_callback_parser.py` | 309 | Callback parsing tests |
| `tests/unit/test_status_transitions.py` | 359 | Status state machine tests |
| `tests/unit/test_review_assignment.py` | 459 | Reviewer assignment tests |
| `tests/integration/test_wf03_technical_review.py` | 433 | Technical review tests |
| `tests/integration/test_wf04_commercial_review.py` | 328 | Commercial review tests |
| `tests/integration/test_wf05_management_approval.py` | 349 | Management approval tests |
| `tests/integration/test_wf06_callback_handler.py` | 878 | Callback handler tests |
| `tests/integration/test_wf01_bid_submission.py` | 253 | Bid submission tests |
| `tests/integration/test_wf02_ai_analysis.py` | 310 | AI analysis tests |
| `tests/integration/test_wf07_outcome_tracking.py` | 311 | Outcome tracking tests |
| `tests/integration/test_wf09_harmony_ingest.py` | 280 | Harmony ingest tests |
| `tests/integration/test_wf10_harmony_process.py` | 386 | Harmony process tests |
| `tests/e2e/test_full_approval_flow.py` | 396 | E2E flow tests |
| `tests/factories/bid_factory.py` | 200 | Bid data factory |
| `tests/factories/reviewer_factory.py` | 252 | Reviewer data factory |
| `tests/mocks/telegram_mock.py` | 298 | Telegram API mock |
| `tests/mocks/ollama_mock.py` | 353 | Ollama API mock |

**Total**: ~6,700 lines, 164 test functions

## VPS Test Environment

### Test Environment on VPS
Tests are deployed to `/opt/n8n-bidding-system/tests/` with venv at `.venv-vps/`

```bash
# Run tests on VPS
ssh -p 1511 root@45.159.230.42
cd /opt/n8n-bidding-system/tests
export TEST_DB_DSN='postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/tenderbiru'
source .venv-vps/bin/activate

# Run unit tests (no VPS services needed)
pytest unit/ -v

# Run integration tests (requires n8n + DB)
pytest integration/test_wf03_technical_review.py -v --tb=short
```

## Key Decisions Made

### 1. TDD Test Structure
- Unit tests extract logic from n8n Code nodes for isolated testing
- Integration tests hit actual n8n webhooks and verify DB state
- E2E tests run complete approval flows

### 2. Test Fixtures
- `sample_reviewer_*` - Use random telegram_chat_id to avoid duplicates
- `create_test_bid` / `create_test_reviewer` - Factory fixtures for DB setup
- `cleanup_test_data` - Tracks and cleans up test records

### 3. Async Workflow Handling
- Add `time.sleep(WORKFLOW_WAIT_SECONDS)` after webhook calls
- Use `::uuid` casts in SQL queries for PostgreSQL
- `conftest.py` handles transaction rollback on test failure

## Next Session Priorities

### 1. Fix Remaining Integration Tests (HIGH)
Update all test files with:
- `time.sleep(WORKFLOW_WAIT_SECONDS)` after webhook calls
- `::uuid` casts in SQL queries
- Proper bid_id string conversion

### 2. Fix Workflow Gaps (HIGH)
Based on failing tests, workflows need:
- Status update to TECHNICAL_REVIEW/COMMERCIAL_REVIEW/MGMT_APPROVAL
- telegram_notifications table logging
- audit_log entries for actions
- Validation of bid_id before processing

### 3. Run Full Test Suite (MEDIUM)
After fixes, run all integration tests to verify workflows

## Quick Commands

```bash
# SSH to VPS
ssh -p 1511 root@45.159.230.42

# Run unit tests locally
source n8n-bidding-system/tests/.venv/bin/activate
pytest n8n-bidding-system/tests/unit/ -v

# Run integration tests on VPS
ssh -p 1511 root@45.159.230.42 "cd /opt/n8n-bidding-system/tests && export TEST_DB_DSN='postgresql://alumist:TVw2xISldsFov7O5ksjr7SYYwazR4if@localhost:5432/tenderbiru' && source .venv-vps/bin/activate && pytest integration/test_wf03_technical_review.py -v --tb=short"

# Test webhook directly
curl -s -X POST http://45.159.230.42:5678/webhook/bid/technical-review -H 'Content-Type: application/json' -d '{"bid_id":"test"}'

# Check recent reviews
PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h 45.159.230.42 -U alumist -d tenderbiru -c "SELECT * FROM reviews ORDER BY created_at DESC LIMIT 5;"

# Check n8n pm2 status
ssh -p 1511 root@45.159.230.42 "pm2 list"
```
