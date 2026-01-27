-- Harmony Pipeline Schema Extension
-- Adds raw tender staging for multi-source scraper integration
-- Version: 1.0.0
-- Date: 2026-01-27

-- ============================================================================
-- RAW TENDER STAGING TABLE
-- ============================================================================
-- Stores raw tender data from all scraper sources before processing
-- Supports hybrid dataflow: real-time + async DB write for audit

CREATE TABLE IF NOT EXISTS raw_tenders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Source identification
    source VARCHAR(50) NOT NULL,           -- 'smartgep', 'eperolehan', 'mytender', etc.
    source_tender_id VARCHAR(255) NOT NULL, -- Original ID from source system
    source_url TEXT,                        -- Direct link to tender on source platform

    -- Job tracking
    job_id VARCHAR(100),                    -- Scraper job that produced this record

    -- Raw data preservation
    raw_data JSONB NOT NULL,                -- Complete original data from scraper

    -- Normalized fields (populated by Harmony Process)
    normalized_data JSONB,                  -- Transformed to common schema

    -- Timestamps
    scraped_at TIMESTAMPTZ NOT NULL,        -- When scraper extracted this
    processed_at TIMESTAMPTZ,               -- When Harmony Pipeline processed it

    -- Processing status
    status VARCHAR(20) DEFAULT 'pending',   -- pending, processing, processed, skipped, error
    error_message TEXT,                     -- Error details if processing failed

    -- TenderBiru integration
    bid_id UUID,                            -- Links to bids.id if successfully submitted

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate imports
    UNIQUE(source, source_tender_id)
);

-- ============================================================================
-- INDEXES FOR RAW_TENDERS
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_raw_tenders_source ON raw_tenders(source);
CREATE INDEX IF NOT EXISTS idx_raw_tenders_status ON raw_tenders(status);
CREATE INDEX IF NOT EXISTS idx_raw_tenders_job ON raw_tenders(job_id);
CREATE INDEX IF NOT EXISTS idx_raw_tenders_created ON raw_tenders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_tenders_scraped ON raw_tenders(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_tenders_bid ON raw_tenders(bid_id) WHERE bid_id IS NOT NULL;

-- GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_raw_tenders_raw_data ON raw_tenders USING GIN(raw_data);

-- ============================================================================
-- ADD SOURCE TRACKING TO BIDS TABLE
-- ============================================================================
-- Links processed bids back to their original scraper source

DO $$
BEGIN
    -- Add source column if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bids' AND column_name = 'source_tender_id'
    ) THEN
        ALTER TABLE bids ADD COLUMN source_tender_id VARCHAR(255);
    END IF;

    -- Add source_url column if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bids' AND column_name = 'source_url'
    ) THEN
        ALTER TABLE bids ADD COLUMN source_url TEXT;
    END IF;
END $$;

-- Index for source tracking (only if not exists)
CREATE INDEX IF NOT EXISTS idx_bids_source ON bids(source, source_tender_id)
    WHERE source IS NOT NULL;

-- ============================================================================
-- UPDATED_AT TRIGGER FOR RAW_TENDERS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_raw_tenders_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_raw_tenders_timestamp ON raw_tenders;
CREATE TRIGGER update_raw_tenders_timestamp
    BEFORE UPDATE ON raw_tenders
    FOR EACH ROW
    EXECUTE FUNCTION update_raw_tenders_updated_at();

-- ============================================================================
-- VIEWS FOR HARMONY PIPELINE MONITORING
-- ============================================================================

-- Pipeline processing status summary
CREATE OR REPLACE VIEW v_harmony_pipeline_status AS
SELECT
    source,
    status,
    COUNT(*) as tender_count,
    MIN(scraped_at) as oldest_scraped,
    MAX(scraped_at) as newest_scraped,
    COUNT(*) FILTER (WHERE bid_id IS NOT NULL) as submitted_to_tenderbiru,
    COUNT(*) FILTER (WHERE error_message IS NOT NULL) as error_count
FROM raw_tenders
GROUP BY source, status
ORDER BY source, status;

-- Recent pipeline activity (last 24 hours)
CREATE OR REPLACE VIEW v_harmony_recent_activity AS
SELECT
    rt.id,
    rt.source,
    rt.source_tender_id,
    rt.raw_data->>'title' as title,
    rt.status,
    rt.scraped_at,
    rt.processed_at,
    rt.bid_id,
    b.reference_number as bid_reference,
    rt.error_message
FROM raw_tenders rt
LEFT JOIN bids b ON rt.bid_id = b.id
WHERE rt.created_at > NOW() - INTERVAL '24 hours'
ORDER BY rt.created_at DESC;

-- Pending tenders awaiting processing
CREATE OR REPLACE VIEW v_harmony_pending AS
SELECT
    id,
    source,
    source_tender_id,
    raw_data->>'title' as title,
    raw_data->>'client_name' as client,
    raw_data->>'submission_deadline' as deadline,
    raw_data->>'estimated_value' as value,
    scraped_at,
    created_at
FROM raw_tenders
WHERE status = 'pending'
ORDER BY scraped_at DESC;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to check if a tender already exists (for deduplication)
CREATE OR REPLACE FUNCTION tender_exists(p_source VARCHAR, p_source_tender_id VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM raw_tenders
        WHERE source = p_source AND source_tender_id = p_source_tender_id
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get tender processing stats by source
CREATE OR REPLACE FUNCTION get_harmony_stats(p_source VARCHAR DEFAULT NULL, p_days INTEGER DEFAULT 7)
RETURNS TABLE (
    source VARCHAR,
    total_tenders BIGINT,
    pending BIGINT,
    processed BIGINT,
    submitted_to_tenderbiru BIGINT,
    errors BIGINT,
    success_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rt.source,
        COUNT(*)::BIGINT as total_tenders,
        COUNT(*) FILTER (WHERE rt.status = 'pending')::BIGINT as pending,
        COUNT(*) FILTER (WHERE rt.status = 'processed')::BIGINT as processed,
        COUNT(*) FILTER (WHERE rt.bid_id IS NOT NULL)::BIGINT as submitted_to_tenderbiru,
        COUNT(*) FILTER (WHERE rt.status = 'error')::BIGINT as errors,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE rt.bid_id IS NOT NULL) /
            NULLIF(COUNT(*) FILTER (WHERE rt.status IN ('processed', 'error')), 0),
            2
        ) as success_rate
    FROM raw_tenders rt
    WHERE rt.created_at > NOW() - (p_days || ' days')::INTERVAL
    AND (p_source IS NULL OR rt.source = p_source)
    GROUP BY rt.source;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CONFIGURATION ENTRIES
-- ============================================================================

-- Add Harmony Pipeline config entries if they don't exist
INSERT INTO system_config (key, value, description)
VALUES
    ('harmony_mode', '"hybrid"', 'Harmony dataflow mode: direct, db_staging, or hybrid'),
    ('harmony_priority_threshold', '"MEDIUM"', 'Minimum priority level to auto-submit to TenderBiru'),
    ('harmony_dedup_check', 'true', 'Enable deduplication check before processing'),
    ('smartgep_api_url', '"http://localhost:8086"', 'SmartGEP scraper service URL'),
    ('eperolehan_api_url', '"http://localhost:8087"', 'ePerolehan scraper service URL')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE raw_tenders IS 'Staging table for raw tender data from all scraper sources before Harmony Pipeline processing';
COMMENT ON COLUMN raw_tenders.source IS 'Scraper source identifier: smartgep, eperolehan, mytender, etc.';
COMMENT ON COLUMN raw_tenders.source_tender_id IS 'Original tender ID from the source system';
COMMENT ON COLUMN raw_tenders.raw_data IS 'Complete original JSON from scraper, preserved for audit and replay';
COMMENT ON COLUMN raw_tenders.normalized_data IS 'Data transformed to common HarmonyRecord schema';
COMMENT ON COLUMN raw_tenders.status IS 'Processing status: pending, processing, processed, skipped, error';

COMMENT ON FUNCTION tender_exists IS 'Check if a tender with given source and ID already exists (deduplication)';
COMMENT ON FUNCTION get_harmony_stats IS 'Get processing statistics for Harmony Pipeline by source';

COMMENT ON VIEW v_harmony_pipeline_status IS 'Summary of Harmony Pipeline processing status by source';
COMMENT ON VIEW v_harmony_recent_activity IS 'Recent tender activity in the last 24 hours';
COMMENT ON VIEW v_harmony_pending IS 'Tenders awaiting Harmony Pipeline processing';
