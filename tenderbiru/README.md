# N8N Bidding & Tendering Excellence System

A comprehensive N8N workflow system for managing bid lifecycles with human-in-the-loop approvals, AI-assisted analysis, and full accountability tracking.

## Quick Start

### 1. Database Setup

```bash
# Connect to PostgreSQL
psql -h localhost -U postgres -d your_database

# Run the schema
\i sql/001_schema.sql
```

### 2. n8n Credentials Setup

Create the following credentials in n8n:

| Credential Name | Type | Purpose |
|-----------------|------|---------|
| `Postgres Bidding DB` | Postgres | Database connection |
| `Bidding Bot` | Telegram API | Bot token from @BotFather |

### 3. Environment Variables

Set these in your n8n environment:

```env
# Telegram Groups (get chat IDs after creating groups)
TELEGRAM_INTAKE_GROUP=-100123456789
TELEGRAM_ESCALATION_GROUP=-100123456790
TELEGRAM_WINS_GROUP=-100123456791

# n8n webhook base URL
N8N_WEBHOOK_BASE_URL=https://your-n8n.com

# Ollama AI
OLLAMA_URL=http://localhost:11434
ANALYSIS_MODEL=qwen3-coder:30b

# Optional: Bid portal URL for "View Details" buttons
BID_PORTAL_URL=https://bids.yourcompany.com
```

### 4. Telegram Bot Setup

1. Message @BotFather on Telegram
2. Send `/newbot` and follow prompts
3. Copy the API token to n8n credentials
4. Create Telegram groups:
   - Bids Intake
   - Escalations
   - Wins Channel
5. Add the bot to each group as admin
6. Get chat IDs (send a message, check `getUpdates`)

### 5. Import Workflows

Import each workflow JSON in order:

1. `01-bid-submission-intake.json`
2. `02-ai-completeness-analysis.json`
3. `03-technical-review.json`
4. `04-commercial-review.json`
5. `05-management-approval.json`
6. `06-telegram-callback-handler.json`
7. `07-outcome-tracking.json`
8. `08-scheduled-reports.json`

### 6. Activate Workflows

⚠️ **Manual activation required** - workflows must be activated in n8n UI.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BIDDING EXCELLENCE SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ BID INTAKE   │    │ AI ANALYSIS  │    │ REVIEW GATES │              │
│  │ Webhook      │───▶│ Completeness │───▶│ Technical    │              │
│  │ Validation   │    │ Win Prob     │    │ Commercial   │              │
│  │ Documents    │    │ Risk Score   │    │ Management   │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                   │                       │
│         ▼                   ▼                   ▼                       │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │                    POSTGRESQL DATABASE                       │       │
│  │  bids │ reviews │ audit_log │ decisions │ lessons_learned   │       │
│  └─────────────────────────────────────────────────────────────┘       │
│         │                   │                   │                       │
│         ▼                   ▼                   ▼                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ NOTIFICATIONS│    │ OUTCOME      │    │ ANALYTICS    │              │
│  │ Telegram     │    │ Win/Loss     │    │ Win Rates    │              │
│  │ Escalations  │    │ Lessons      │    │ Patterns     │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Workflows

### 1. Bid Submission Intake
**Webhook:** `POST /webhook/bid/submit`

**Request Body:**
```json
{
  "title": "Website Redesign Project",
  "client_name": "Acme Corp",
  "submission_deadline": "2024-02-15T17:00:00Z",
  "estimated_value": 150000,
  "currency": "USD",
  "priority": "HIGH",
  "document_urls": ["https://..."],
  "client_contact": "John Smith",
  "client_email": "john@acme.com"
}
```

**Response:**
```json
{
  "success": true,
  "bid_id": "uuid",
  "reference_number": "BID-2024-0001",
  "status": "SUBMITTED",
  "message": "Bid submitted successfully. AI analysis will begin shortly."
}
```

### 2. AI Completeness Analysis
**Trigger:** Internal (after submission)

- Analyzes bid documents using `deepseek-ocr`
- Scores completeness (0-100) using `qwen3-coder`
- If score < 70%: Sets status to `NEEDS_INFO`
- If score >= 70%: Advances to `TECHNICAL_REVIEW`

### 3. Technical Review
**Trigger:** Internal (after analysis passes)

- Assigns to available technical reviewer
- Sends Telegram message with inline buttons
- 48-hour SLA tracking
- Buttons: [Approve] [Revision] [Reject]

### 4. Commercial Review
**Trigger:** Internal (after technical approval)

- Same pattern as technical review
- Focus on pricing, terms, margins
- 48-hour SLA

### 5. Management Approval
**Trigger:** Internal (after commercial approval)

- Final executive sign-off
- AI generates final win probability assessment
- 24-hour SLA
- Button: [Approve to Submit] [Request Changes] [Reject]

### 6. Telegram Callback Handler
**Trigger:** Telegram callback_query events

- Parses button callbacks: `action_bidId_reviewType`
- Answers callback (removes loading indicator)
- For approvals: Updates DB, advances workflow
- For revisions/rejections: Asks for reason, stores in conversation state

### 7. Outcome Tracking
**Webhook:** `POST /webhook/bid/outcome`

**Request Body:**
```json
{
  "bid_id": "uuid",
  "outcome": "WON",
  "actual_contract_value": 145000,
  "notes": "Negotiated 3% discount"
}
```

For losses:
```json
{
  "bid_id": "uuid",
  "outcome": "LOST",
  "loss_reason": "Price too high",
  "competitor_won": "Competitor Inc"
}
```

### 8. Scheduled Reports
**Schedules:**
- **Daily 8 AM (weekdays):** Pipeline summary, deadline warnings, SLA breaches
- **Weekly Monday 9 AM:** Win rates, reviewer performance, analytics

---

## Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `bids` | Main bid records with AI scores |
| `reviews` | Review stages (tech, comm, mgmt) |
| `reviewers` | User accounts with Telegram IDs |
| `approval_decisions` | Detailed decision records |
| `audit_log` | Complete accountability trail |
| `lessons_learned` | Outcome analysis for improvement |
| `bid_analytics` | Aggregated metrics |
| `conversation_state` | Telegram multi-step flow state |

### Key Views

- `v_active_bids` - Active bids with review status
- `v_pending_reviews` - Reviews awaiting decision
- `v_win_rate_trend` - Monthly win rate trends

---

## Bid Status Flow

```
[DRAFT] → [SUBMITTED] → [TECHNICAL_REVIEW] → [COMMERCIAL_REVIEW] → [MGMT_APPROVAL]
                │              │                    │                    │
                ▼              ▼                    ▼                    ▼
           [NEEDS_INFO]   [TECH_REJECTED]    [COMM_REJECTED]      [APPROVED_TO_SUBMIT]
                │              │                    │                    │
                └──────────────┴────────────────────┴────────────────────┘
                                        ▼
                              [SUBMITTED_TO_CLIENT]
                                        │
                        ┌───────────────┼───────────────┐
                        ▼               ▼               ▼
                      [WON]          [LOST]      [NO_DECISION]
                        │               │               │
                        └───────────────┴───────────────┘
                                        ▼
                              [LESSONS_LEARNED] → [ARCHIVED]
```

---

## Telegram Message Examples

### Review Request
```
📋 Technical Review Required

Bid: BID-2024-0001
Title: Website Redesign Project
Client: Acme Corp
Value: $150,000
Deadline: Thu, Feb 15, 2024

AI Analysis:
• Completeness: 85%
• Win Probability: 72%
• Risk Score: 35%

SLA: 48 hours (Due: Jan 29, 10:00 AM)

[✓ Approve] [✏️ Revision] [✗ Reject]
[📄 View Details]
```

### Daily Report
```
📊 Daily Bidding Report
Monday, January 27, 2024

Pipeline Summary:
• Total Active: 12
• In Review: 5
• Needs Info: 2
• Ready to Submit: 3
• Total Pipeline Value: $2,450,000
• Avg Win Probability: 68%

⚠️ Upcoming Deadlines (3 days):
• BID-2024-0015: TODAY! - Acme Corp
• BID-2024-0012: 2 days - Beta Inc

🚨 SLA Breaches (1):
• BID-2024-0010 (TECHNICAL) - 4h overdue - @alice
```

---

## Testing Checklist

### 1. Bid Submission
```bash
curl -X POST https://your-n8n.com/webhook/bid/submit \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Bid",
    "client_name": "Test Client",
    "submission_deadline": "2024-02-15T17:00:00Z",
    "estimated_value": 50000
  }'
```

- [ ] Returns 201 with bid_id and reference_number
- [ ] Bid appears in database
- [ ] Audit log entry created
- [ ] Telegram notification sent to intake group
- [ ] AI analysis triggered

### 2. AI Analysis
- [ ] Completeness score calculated (0-100)
- [ ] Win probability assessed
- [ ] Risk score generated
- [ ] Missing sections identified
- [ ] Status transitions correctly (NEEDS_INFO or TECHNICAL_REVIEW)

### 3. Review Flow
- [ ] Reviewer receives Telegram message with buttons
- [ ] Clicking button removes loading indicator
- [ ] Approve advances to next stage
- [ ] Revision/Reject asks for reason
- [ ] Reason stored in database
- [ ] Original message edited with decision

### 4. Outcome Recording
```bash
curl -X POST https://your-n8n.com/webhook/bid/outcome \
  -H "Content-Type: application/json" \
  -d '{
    "bid_id": "your-bid-uuid",
    "outcome": "WON",
    "actual_contract_value": 48000
  }'
```

- [ ] Bid status updated
- [ ] Lessons learned generated by AI
- [ ] Win announced in wins channel
- [ ] Analytics updated

### 5. Scheduled Reports
- [ ] Daily report sent at 8 AM
- [ ] SLA breaches flagged
- [ ] Weekly analytics generated on Monday

---

## Troubleshooting

### Telegram Messages Not Sending
1. Check bot token in credentials
2. Verify bot is admin in groups
3. Check chat IDs are correct (negative for groups)
4. Review n8n execution logs

### AI Analysis Failing
1. Verify Ollama is running: `curl http://localhost:11434/api/tags`
2. Check model is available: `ollama list`
3. Increase timeout if needed (currently 120-180s)
4. Review response parsing in Code nodes

### Callback Buttons Not Working
1. Ensure Workflow 06 (Telegram Callback Handler) is active
2. Check callback_data format: `action_bidId_reviewType`
3. Verify conversation_state table is being updated
4. Review error logs for parsing failures

### SLA Not Tracking
1. Check timezone in workflow settings
2. Verify reviews.due_at is being set
3. Confirm scheduled workflow (08) is active
4. Review sla_breached trigger function

---

## Security Notes

- Bot tokens stored in n8n credentials (encrypted)
- Database user should have limited permissions
- All inputs validated before database operations
- Audit log tracks all actions with actor info
- Conversation state expires after 1 hour

---

## Harmony Pipeline (Scraper Integration)

The Harmony Pipeline enables automated tender import from multiple scraper sources (SmartGEP, ePerolehan, etc.) into TenderBiru.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SCRAPER MODULES (Input)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  SmartGEP Scraper → ePerolehan Scraper → Future Scrapers                   │
│         │                   │                   │                           │
│         └───────────────────┼───────────────────┘                           │
│                             ▼                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                     HARMONY PIPELINE (Processing)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  09-harmony-ingest.json: Webhook → Validate → Store Raw → Trigger Process  │
│  10-harmony-process.json: Normalize → Score Priority → Dedupe → TenderBiru │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Webhooks

#### Harmony Ingest
**Endpoint:** `POST /webhook/harmony/ingest`

```json
{
  "source": "smartgep",
  "job_id": "scrape-20260127-abc123",
  "tenders": [
    {
      "tender_id": "QT-25-0001",
      "title": "Supply of Office Equipment",
      "organization": "PETRONAS",
      "closing_date": "31/01/2026",
      "estimated_value": 500000,
      "currency": "MYR",
      "document_urls": ["https://..."],
      "source_url": "https://smartgep.com/tender/..."
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "processed": 5,
  "new_tenders": 3,
  "updated_tenders": 2,
  "tender_ids": [...]
}
```

### Priority Scoring

| Factor | Score Range | Criteria |
|--------|-------------|----------|
| Value (max 50) | 5-50 | <50K=5, 50K+=10, 100K+=20, 500K+=30, 1M+=40, 10M+=50 |
| Deadline (max 50) | 5-50 | >30d=5, 2-4w=10, 1-2w=20, 6-7d=30, 3-5d=40, ≤2d=50 |

**Priority Levels:** CRITICAL (80+), HIGH (60-79), MEDIUM (40-59), LOW (<40)

### Source Field Mappings

**SmartGEP:**
| SmartGEP Field | TenderBiru Field |
|----------------|------------------|
| `tender_id` | `source_tender_id` |
| `organization` | `client_name` |
| `closing_date` | `submission_deadline` (DD/MM/YYYY → ISO) |

**ePerolehan:**
| ePerolehan Field | TenderBiru Field |
|------------------|------------------|
| `reference` | `source_tender_id` |
| `agency` | `client_name` |
| `tarikh_tutup` | `submission_deadline` (DD/MM/YYYY → ISO) |

### Deployment

```bash
# 1. Deploy SQL schema
scp -P 1511 n8n-bidding-system/sql/002_harmony_pipeline.sql root@45.159.230.42:/opt/n8n-bidding-system/sql/
ssh -p 1511 root@45.159.230.42 "sudo -u postgres psql -d tenderbiru -f /opt/n8n-bidding-system/sql/002_harmony_pipeline.sql"

# 2. Deploy workflows
scp -P 1511 n8n-bidding-system/workflows/09-*.json n8n-bidding-system/workflows/10-*.json root@45.159.230.42:/opt/n8n-bidding-system/workflows/
ssh -p 1511 root@45.159.230.42 "cd /opt/n8n-bidding-system/workflows && n8n import:workflow --input=09-harmony-ingest.json && n8n import:workflow --input=10-harmony-process.json"

# 3. Activate workflows in n8n UI
```

### Monitoring Views

- `v_harmony_pipeline_status` - Processing status by source
- `v_harmony_recent_activity` - Last 24 hours activity
- `v_harmony_pending` - Tenders awaiting processing

---

## Files

```
tenderbiru/
├── README.md                          # This file
├── docs/
│   ├── tenderbiru-context.md          # System context and patterns
│   ├── tenderbiru-tasks.md            # Task completion history
│   └── handoffs/                      # Session handoff documents
│       ├── handoff-2026-01-27-session6.md
│       ├── handoff-2026-01-27-session7.md
│       ├── handoff-2026-01-28-session8.md
│       └── handoff-2026-01-28-session9.md
├── sql/
│   ├── 001_schema.sql                 # PostgreSQL schema
│   └── 002_harmony_pipeline.sql       # Harmony Pipeline extension
├── tests/                             # Integration test suite
│   ├── conftest.py
│   ├── pytest.ini
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── factories/
│   └── mocks/
└── workflows/
    ├── 01-bid-submission-intake.json
    ├── 02-ai-completeness-analysis.json
    ├── 03-technical-review.json
    ├── 04-commercial-review.json
    ├── 05-management-approval.json
    ├── 06-telegram-callback-handler.json
    ├── 07-outcome-tracking.json
    ├── 08-scheduled-reports.json
    ├── 09-harmony-ingest.json         # Scraper integration - Ingest
    └── 10-harmony-process.json        # Scraper integration - Process
```

---

## AI Models Used

| Model | Size | Purpose |
|-------|------|---------|
| `qwen3-coder:30b` | 18GB | Completeness analysis, win probability, lessons learned |
| `deepseek-ocr:latest` | 6.7GB | Document OCR and text extraction |

---

## Success Metrics

Track these KPIs to measure system effectiveness:

- **Process Efficiency:** Average time from submission to approval
- **Review SLA Compliance:** % reviews completed within deadline
- **Win Rate Improvement:** Trend over time
- **AI Accuracy:** Correlation between AI score and actual outcomes
- **Accountability Coverage:** 100% decisions have recorded reasons

---

## Support

For issues:
1. Check n8n execution logs
2. Review database audit_log table
3. Verify all workflows are active
4. Test individual API endpoints

---

*Generated for the N8N Bidding & Tendering Excellence System*
