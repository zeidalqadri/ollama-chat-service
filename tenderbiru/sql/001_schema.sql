-- N8N Bidding & Tendering Excellence System
-- PostgreSQL Schema v1.0
--
-- Run this script to create the complete database schema
-- Required: PostgreSQL 14+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- ENUMS
-- ============================================================================

-- Bid status state machine
CREATE TYPE bid_status AS ENUM (
    'DRAFT',
    'SUBMITTED',
    'NEEDS_INFO',
    'TECHNICAL_REVIEW',
    'TECH_REJECTED',
    'COMMERCIAL_REVIEW',
    'COMM_REJECTED',
    'MGMT_APPROVAL',
    'APPROVED_TO_SUBMIT',
    'SUBMITTED_TO_CLIENT',
    'WON',
    'LOST',
    'NO_DECISION',
    'LESSONS_LEARNED',
    'ARCHIVED'
);

-- Review types
CREATE TYPE review_type AS ENUM (
    'TECHNICAL',
    'COMMERCIAL',
    'MANAGEMENT'
);

-- Review decision
CREATE TYPE review_decision AS ENUM (
    'PENDING',
    'APPROVED',
    'REVISION_REQUESTED',
    'REJECTED'
);

-- Priority levels
CREATE TYPE priority_level AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL'
);

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Reviewers/Users table
CREATE TABLE reviewers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_chat_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    can_review_technical BOOLEAN DEFAULT FALSE,
    can_review_commercial BOOLEAN DEFAULT FALSE,
    can_approve_management BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on telegram_chat_id for quick lookups
CREATE INDEX idx_reviewers_telegram ON reviewers(telegram_chat_id);

-- Main bids table
CREATE TABLE bids (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_number VARCHAR(50) UNIQUE NOT NULL,

    -- Basic info
    title VARCHAR(500) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    client_contact VARCHAR(255),
    client_email VARCHAR(255),

    -- Financial
    estimated_value DECIMAL(15, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    margin_percentage DECIMAL(5, 2),

    -- Dates
    submission_deadline TIMESTAMPTZ NOT NULL,
    decision_expected_date TIMESTAMPTZ,
    project_start_date TIMESTAMPTZ,
    project_duration_days INTEGER,

    -- Status tracking
    status bid_status DEFAULT 'SUBMITTED',
    priority priority_level DEFAULT 'MEDIUM',

    -- AI Analysis scores
    completeness_score INTEGER CHECK (completeness_score >= 0 AND completeness_score <= 100),
    win_probability_score INTEGER CHECK (win_probability_score >= 0 AND win_probability_score <= 100),
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    ai_analysis_json JSONB,
    missing_sections TEXT[],
    ai_recommendations TEXT[],

    -- Documents
    document_urls TEXT[],
    document_analysis_json JSONB,

    -- Metadata
    submitted_by UUID REFERENCES reviewers(id),
    current_reviewer_id UUID REFERENCES reviewers(id),
    source VARCHAR(100),
    tags TEXT[],
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ DEFAULT NOW(),

    -- Outcome tracking
    outcome_recorded_at TIMESTAMPTZ,
    actual_contract_value DECIMAL(15, 2),
    loss_reason TEXT,
    competitor_won VARCHAR(255)
);

-- Indexes for bids
CREATE INDEX idx_bids_status ON bids(status);
CREATE INDEX idx_bids_reference ON bids(reference_number);
CREATE INDEX idx_bids_deadline ON bids(submission_deadline);
CREATE INDEX idx_bids_client ON bids(client_name);
CREATE INDEX idx_bids_created ON bids(created_at DESC);

-- ============================================================================
-- REVIEW TABLES
-- ============================================================================

-- Reviews table - tracks each review stage
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bid_id UUID NOT NULL REFERENCES bids(id) ON DELETE CASCADE,
    review_type review_type NOT NULL,

    -- Assignment
    assigned_to UUID REFERENCES reviewers(id),
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    due_at TIMESTAMPTZ,

    -- Decision
    decision review_decision DEFAULT 'PENDING',
    decision_at TIMESTAMPTZ,
    decision_reason TEXT,

    -- Revision tracking
    revision_count INTEGER DEFAULT 0,
    revision_notes TEXT,

    -- SLA tracking
    sla_hours INTEGER DEFAULT 48,
    sla_breached BOOLEAN DEFAULT FALSE,
    escalated_at TIMESTAMPTZ,

    -- Telegram message tracking
    notification_message_id BIGINT,
    notification_chat_id BIGINT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one active review per type per bid
    UNIQUE (bid_id, review_type)
);

-- Indexes for reviews
CREATE INDEX idx_reviews_bid ON reviews(bid_id);
CREATE INDEX idx_reviews_assigned ON reviews(assigned_to);
CREATE INDEX idx_reviews_decision ON reviews(decision);
CREATE INDEX idx_reviews_due ON reviews(due_at);

-- Approval decisions - detailed record of each decision
CREATE TABLE approval_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    bid_id UUID NOT NULL REFERENCES bids(id) ON DELETE CASCADE,

    reviewer_id UUID NOT NULL REFERENCES reviewers(id),
    reviewer_name VARCHAR(255) NOT NULL,
    reviewer_telegram_username VARCHAR(100),

    decision review_decision NOT NULL,
    reason TEXT,

    -- Callback tracking
    telegram_callback_id VARCHAR(100),
    telegram_message_id BIGINT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_decisions_bid ON approval_decisions(bid_id);
CREATE INDEX idx_decisions_reviewer ON approval_decisions(reviewer_id);

-- ============================================================================
-- AUDIT & LOGGING
-- ============================================================================

-- Complete audit trail
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What changed
    entity_type VARCHAR(50) NOT NULL, -- 'bid', 'review', 'decision'
    entity_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL, -- 'created', 'status_changed', 'assigned', etc.

    -- Who changed it
    actor_id UUID REFERENCES reviewers(id),
    actor_name VARCHAR(255),
    actor_type VARCHAR(50), -- 'user', 'system', 'ai', 'workflow'

    -- Change details
    old_value JSONB,
    new_value JSONB,
    change_reason TEXT,

    -- Context
    workflow_execution_id VARCHAR(100),
    source VARCHAR(100), -- 'webhook', 'telegram', 'schedule', 'manual'
    ip_address INET,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for audit log
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_actor ON audit_log(actor_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX idx_audit_action ON audit_log(action);

-- ============================================================================
-- LESSONS LEARNED & ANALYTICS
-- ============================================================================

-- Lessons learned from bid outcomes
CREATE TABLE lessons_learned (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bid_id UUID NOT NULL REFERENCES bids(id) ON DELETE CASCADE,

    -- Outcome
    outcome VARCHAR(20) NOT NULL CHECK (outcome IN ('WON', 'LOST', 'NO_DECISION')),
    outcome_date TIMESTAMPTZ DEFAULT NOW(),

    -- Analysis
    key_factors TEXT[],
    what_worked TEXT,
    what_didnt_work TEXT,
    improvement_suggestions TEXT,

    -- AI-generated insights
    ai_analysis TEXT,
    ai_patterns_identified JSONB,

    -- Tags for searchability
    categories TEXT[],

    -- Verification
    verified_by UUID REFERENCES reviewers(id),
    verified_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lessons_bid ON lessons_learned(bid_id);
CREATE INDEX idx_lessons_outcome ON lessons_learned(outcome);
CREATE INDEX idx_lessons_categories ON lessons_learned USING GIN(categories);

-- Bid analytics aggregate table (populated by scheduled job)
CREATE TABLE bid_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Time period
    period_type VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'monthly', 'quarterly'
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Counts
    total_bids INTEGER DEFAULT 0,
    bids_won INTEGER DEFAULT 0,
    bids_lost INTEGER DEFAULT 0,
    bids_pending INTEGER DEFAULT 0,
    bids_no_decision INTEGER DEFAULT 0,

    -- Rates
    win_rate DECIMAL(5, 2),
    avg_completeness_score DECIMAL(5, 2),
    avg_win_probability DECIMAL(5, 2),

    -- Values
    total_bid_value DECIMAL(15, 2),
    won_value DECIMAL(15, 2),
    lost_value DECIMAL(15, 2),

    -- SLA metrics
    avg_review_time_hours DECIMAL(10, 2),
    sla_breach_count INTEGER DEFAULT 0,
    sla_compliance_rate DECIMAL(5, 2),

    -- Breakdown by reviewer (JSONB)
    reviewer_stats JSONB,

    -- Breakdown by client (JSONB)
    client_stats JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (period_type, period_start)
);

CREATE INDEX idx_analytics_period ON bid_analytics(period_type, period_start DESC);

-- Reviewer performance metrics
CREATE TABLE reviewer_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reviewer_id UUID NOT NULL REFERENCES reviewers(id) ON DELETE CASCADE,

    -- Time period
    period_type VARCHAR(20) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Review stats
    reviews_assigned INTEGER DEFAULT 0,
    reviews_completed INTEGER DEFAULT 0,
    reviews_approved INTEGER DEFAULT 0,
    reviews_rejected INTEGER DEFAULT 0,
    reviews_revision_requested INTEGER DEFAULT 0,

    -- Time metrics
    avg_response_time_hours DECIMAL(10, 2),
    fastest_response_hours DECIMAL(10, 2),
    slowest_response_hours DECIMAL(10, 2),

    -- SLA
    sla_breaches INTEGER DEFAULT 0,
    sla_compliance_rate DECIMAL(5, 2),

    -- Prediction accuracy (for technical reviewers)
    bids_approved_that_won INTEGER DEFAULT 0,
    bids_approved_that_lost INTEGER DEFAULT 0,
    prediction_accuracy DECIMAL(5, 2),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (reviewer_id, period_type, period_start)
);

CREATE INDEX idx_reviewer_metrics_reviewer ON reviewer_metrics(reviewer_id);
CREATE INDEX idx_reviewer_metrics_period ON reviewer_metrics(period_type, period_start DESC);

-- ============================================================================
-- NOTIFICATION & STATE TRACKING
-- ============================================================================

-- Telegram notification log
CREATE TABLE telegram_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Target
    chat_id BIGINT NOT NULL,
    chat_type VARCHAR(20), -- 'private', 'group'

    -- Message
    message_id BIGINT,
    message_text TEXT,
    has_inline_keyboard BOOLEAN DEFAULT FALSE,

    -- Context
    bid_id UUID REFERENCES bids(id) ON DELETE SET NULL,
    review_id UUID REFERENCES reviews(id) ON DELETE SET NULL,
    notification_type VARCHAR(50) NOT NULL, -- 'review_assigned', 'sla_warning', 'deadline_reminder', etc.

    -- Status
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    delivered BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_telegram_chat ON telegram_notifications(chat_id);
CREATE INDEX idx_telegram_bid ON telegram_notifications(bid_id);

-- Conversation state for multi-step Telegram interactions
CREATE TABLE conversation_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,

    -- State
    state_type VARCHAR(50) NOT NULL, -- 'awaiting_revision_reason', 'awaiting_rejection_reason', etc.
    context_json JSONB NOT NULL,

    -- Expiry
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 hour'),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Only one active state per user per chat
    UNIQUE (chat_id, user_id)
);

CREATE INDEX idx_conversation_state_chat ON conversation_state(chat_id, user_id);
CREATE INDEX idx_conversation_state_expires ON conversation_state(expires_at);

-- ============================================================================
-- CONFIGURATION TABLES
-- ============================================================================

-- System configuration
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES reviewers(id)
);

-- Insert default configuration
INSERT INTO system_config (key, value, description) VALUES
    ('sla_hours_technical', '48', 'SLA hours for technical review'),
    ('sla_hours_commercial', '48', 'SLA hours for commercial review'),
    ('sla_hours_management', '24', 'SLA hours for management approval'),
    ('completeness_threshold', '70', 'Minimum completeness score to proceed'),
    ('telegram_intake_group', 'null', 'Telegram chat ID for bid intake notifications'),
    ('telegram_escalation_group', 'null', 'Telegram chat ID for escalation alerts'),
    ('telegram_wins_group', 'null', 'Telegram chat ID for win announcements'),
    ('ollama_url', '"http://localhost:11434"', 'Ollama API URL'),
    ('analysis_model', '"qwen3-coder:30b"', 'Model for bid analysis'),
    ('ocr_model', '"deepseek-ocr:latest"', 'Model for document OCR');

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_bids_updated_at BEFORE UPDATE ON bids
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_reviews_updated_at BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_reviewers_updated_at BEFORE UPDATE ON reviewers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_lessons_learned_updated_at BEFORE UPDATE ON lessons_learned
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Function to generate bid reference number
CREATE OR REPLACE FUNCTION generate_bid_reference()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.reference_number IS NULL THEN
        NEW.reference_number := 'BID-' || TO_CHAR(NOW(), 'YYYY') || '-' ||
            LPAD(NEXTVAL('bid_reference_seq')::TEXT, 4, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create sequence for bid reference
CREATE SEQUENCE IF NOT EXISTS bid_reference_seq START 1;

CREATE TRIGGER generate_bid_ref BEFORE INSERT ON bids
    FOR EACH ROW EXECUTE FUNCTION generate_bid_reference();

-- Function to log status changes to audit
CREATE OR REPLACE FUNCTION log_bid_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO audit_log (
            entity_type, entity_id, action,
            actor_type, old_value, new_value
        ) VALUES (
            'bid', NEW.id, 'status_changed',
            'system',
            jsonb_build_object('status', OLD.status),
            jsonb_build_object('status', NEW.status)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER log_bid_status AFTER UPDATE ON bids
    FOR EACH ROW EXECUTE FUNCTION log_bid_status_change();

-- Function to check and mark SLA breaches
CREATE OR REPLACE FUNCTION check_sla_breach()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.decision = 'PENDING' AND NEW.due_at < NOW() AND NOT NEW.sla_breached THEN
        NEW.sla_breached := TRUE;
        NEW.escalated_at := NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_review_sla BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION check_sla_breach();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active bids view with review status
CREATE OR REPLACE VIEW v_active_bids AS
SELECT
    b.id,
    b.reference_number,
    b.title,
    b.client_name,
    b.estimated_value,
    b.submission_deadline,
    b.status,
    b.priority,
    b.completeness_score,
    b.win_probability_score,
    b.created_at,
    r_tech.decision AS tech_decision,
    r_tech.assigned_to AS tech_reviewer,
    r_comm.decision AS comm_decision,
    r_comm.assigned_to AS comm_reviewer,
    r_mgmt.decision AS mgmt_decision,
    r_mgmt.assigned_to AS mgmt_reviewer,
    EXTRACT(EPOCH FROM (b.submission_deadline - NOW()))/86400 AS days_to_deadline
FROM bids b
LEFT JOIN reviews r_tech ON b.id = r_tech.bid_id AND r_tech.review_type = 'TECHNICAL'
LEFT JOIN reviews r_comm ON b.id = r_comm.bid_id AND r_comm.review_type = 'COMMERCIAL'
LEFT JOIN reviews r_mgmt ON b.id = r_mgmt.bid_id AND r_mgmt.review_type = 'MANAGEMENT'
WHERE b.status NOT IN ('ARCHIVED', 'WON', 'LOST', 'NO_DECISION')
ORDER BY b.submission_deadline ASC;

-- Pending reviews view
CREATE OR REPLACE VIEW v_pending_reviews AS
SELECT
    r.id AS review_id,
    r.review_type,
    r.assigned_to,
    rv.name AS reviewer_name,
    rv.telegram_chat_id,
    r.due_at,
    r.sla_breached,
    r.assigned_at,
    EXTRACT(EPOCH FROM (NOW() - r.assigned_at))/3600 AS hours_pending,
    b.id AS bid_id,
    b.reference_number,
    b.title,
    b.client_name,
    b.estimated_value,
    b.priority
FROM reviews r
JOIN bids b ON r.bid_id = b.id
LEFT JOIN reviewers rv ON r.assigned_to = rv.id
WHERE r.decision = 'PENDING'
ORDER BY r.due_at ASC;

-- Win rate by period view
CREATE OR REPLACE VIEW v_win_rate_trend AS
SELECT
    DATE_TRUNC('month', outcome_recorded_at) AS month,
    COUNT(*) AS total_decided,
    COUNT(*) FILTER (WHERE status = 'WON') AS won,
    COUNT(*) FILTER (WHERE status = 'LOST') AS lost,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'WON') / NULLIF(COUNT(*), 0), 2) AS win_rate,
    SUM(estimated_value) FILTER (WHERE status = 'WON') AS won_value,
    SUM(estimated_value) FILTER (WHERE status = 'LOST') AS lost_value
FROM bids
WHERE status IN ('WON', 'LOST')
AND outcome_recorded_at IS NOT NULL
GROUP BY DATE_TRUNC('month', outcome_recorded_at)
ORDER BY month DESC;

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- Insert sample reviewers (uncomment to use)
/*
INSERT INTO reviewers (telegram_chat_id, telegram_username, name, email, role, department, can_review_technical, can_review_commercial, can_approve_management) VALUES
    (123456789, 'tech_lead', 'Alice Technical', 'alice@company.com', 'Technical Lead', 'Engineering', TRUE, FALSE, FALSE),
    (234567890, 'finance_mgr', 'Bob Finance', 'bob@company.com', 'Finance Manager', 'Finance', FALSE, TRUE, FALSE),
    (345678901, 'exec_dir', 'Carol Executive', 'carol@company.com', 'Executive Director', 'Management', FALSE, FALSE, TRUE),
    (456789012, 'bid_coord', 'David Coordinator', 'david@company.com', 'Bid Coordinator', 'Sales', TRUE, TRUE, FALSE);
*/

-- ============================================================================
-- GRANTS (adjust for your database user)
-- ============================================================================

-- Create a dedicated user for n8n workflows
-- CREATE USER n8n_bidding WITH PASSWORD 'secure_password_here';

-- Grant necessary permissions
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO n8n_bidding;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO n8n_bidding;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO n8n_bidding;

COMMENT ON TABLE bids IS 'Main bid records with AI analysis scores and status tracking';
COMMENT ON TABLE reviews IS 'Review stages for each bid (technical, commercial, management)';
COMMENT ON TABLE approval_decisions IS 'Detailed record of each approval/rejection decision';
COMMENT ON TABLE audit_log IS 'Complete audit trail of all system changes';
COMMENT ON TABLE lessons_learned IS 'Post-outcome analysis for continuous improvement';
COMMENT ON TABLE bid_analytics IS 'Aggregated analytics for reporting';
COMMENT ON TABLE reviewer_metrics IS 'Per-reviewer performance tracking';
COMMENT ON TABLE conversation_state IS 'Telegram conversation state for multi-step flows';
