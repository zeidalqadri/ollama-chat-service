# Session 8 Handoff - TenderBiru Automated Troubleshooting

**Date**: 2026-01-28 00:50 MYT
**Focus**: Implementing automated troubleshooting sequences for tender pipeline resilience

## What Was Accomplished

### 1. `/api/troubleshoot` Endpoint (BORAK)
Added a new endpoint to the BORAK service (main.py) that provides automated troubleshooting for pipeline failures:

**Location**: `main.py:195-450`

**Model Routing**:
| Stage | Model | Purpose |
|-------|-------|---------|
| scrape | qwen2.5-coder:7b | Extract tender data from raw HTML |
| extract | qwen2.5-coder:7b | Infer missing fields |
| analyze | gemma2:9b | Generate fallback scores |
| document | deepseek-ocr | Retry failed OCR |
| submit | qwen2.5-coder:7b | Analyze submission errors |

**Tested and Working**:
- Scrape: Successfully extracts tender fields from HTML tables
- Analyze: Returns completeness/win_probability/risk scores

### 2. Workflow 09 - Harmony Ingest (v2.0.0)
Updated with extraction troubleshoot branch:
- Checks if tenders array empty but raw_html available
- Calls troubleshoot endpoint to extract data from HTML
- Merges recovered data or flags for manual review
- Sends Telegram alert on failures

**Workflow ID**: `8GdOVgHbGoPaT6mM`
**Node Count**: 9 nodes

### 3. Workflow 02 - AI Completeness Analysis (v2.0.0)
Updated with retry + fallback logic:
- Detects analysis failures (timeout/error)
- Retries once with 240s timeout and simplified prompt
- Falls back to troubleshoot endpoint if retry fails
- Applies default scores (50/50/50) with NEEDS_MANUAL_REVIEW
- Sends appropriate Telegram notifications

**Workflow ID**: `l2RiR02qed1XaTzX`
**Node Count**: 23 nodes

## Critical Discovery: n8n Schema

**IMPORTANT**: n8n workflows are stored in the `n8n` schema, NOT `public` schema.

```sql
-- CORRECT
SELECT * FROM n8n.workflow_entity WHERE id = '8GdOVgHbGoPaT6mM';

-- WRONG (empty results)
SELECT * FROM public.workflow_entity WHERE id = '8GdOVgHbGoPaT6mM';
```

Always use `n8n.workflow_entity` when querying or updating workflows.

## Files Modified

| File | Changes |
|------|---------|
| `main.py` | +250 lines: TroubleshootRequest/Result models, TROUBLESHOOT_MODELS dict, TROUBLESHOOT_PROMPTS dict, run_troubleshoot() function, /api/troubleshoot endpoint, /api/troubleshoot/models endpoint |
| `n8n-bidding-system/workflows/09-harmony-ingest.json` | v2.0.0: Added troubleshoot branch, failure handling, Telegram alerts |
| `n8n-bidding-system/workflows/02-ai-completeness-analysis.json` | v2.0.0: Added retry logic, fallback scores, manual review routing |
| `dev/active/tenderbiru-context.md` | Updated with Session 8 implementation details |
| `dev/active/tenderbiru-tasks.md` | Marked Session 8 tasks complete, added pending tasks |

## Deployed to VPS

| Component | Location | Status |
|-----------|----------|--------|
| BORAK (main.py) | `/opt/ollama-ui/main.py` | ✅ Running on port 8012 |
| Workflow 09 | `n8n.workflow_entity` | ✅ Updated to v2.0.0 |
| Workflow 02 | `n8n.workflow_entity` | ✅ Updated to v2.0.0 |

## Verification Commands

```bash
# Test troubleshoot endpoint
curl -s http://45.159.230.42:8012/api/troubleshoot/models

# Test scrape recovery
curl -s -X POST http://45.159.230.42:8012/api/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"stage":"scrape","error_data":{"error":"test"},"context":{"raw_html":"<td>ID:</td><td>TND-001</td>"}}'

# Check workflow versions
ssh -p 1511 root@45.159.230.42 "PGPASSWORD='TVw2xISldsFov7O5ksjr7SYYwazR4if' psql -h localhost -U alumist -d alumist_n8n -c \"SELECT id, name, \\\"versionId\\\" FROM n8n.workflow_entity WHERE name LIKE '%Harmony Ingest%' OR name LIKE '%Completeness%';\""
```

## Next Steps for Continuation

1. **Test end-to-end troubleshooting flow**
   - Send Harmony Ingest request with empty tenders + raw_html
   - Verify data is extracted and proceeds through pipeline

2. **Test remaining troubleshooters**
   - Document (deepseek-ocr) stage
   - Submit (qwen2.5-coder:7b) stage

3. **Add BORAK_URL to n8n environment**
   - Currently using fallback `http://localhost:8012`

## Bug Fixed During Session

**Issue**: Analyze troubleshooter returning `data: {}` despite model responding with scores

**Root Cause**: The `run_troubleshoot()` function was looking for `parsed.get("extracted")` or `parsed.get("suggested_corrections")`, but the analyze prompt returns scores at top level (`completeness_score`, `win_probability`, `risk_score`)

**Fix**: Added special handling for analyze stage in `main.py:2378-2390`:
```python
if stage == "analyze" and "completeness_score" in parsed:
    return {
        "recovered_data": {
            "completeness_score": parsed.get("completeness_score", 50),
            "win_probability": parsed.get("win_probability", 50),
            "risk_score": parsed.get("risk_score", 50)
        },
        ...
    }
```

## Uncommitted Changes

All changes have been saved to files. Ready for commit.
