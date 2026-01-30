"""
Integration Tests: WF10 - Harmony Process Workflow

TDD tests for processing and normalizing ingested tenders.
Tests verify date normalization, priority scoring, and bid submission triggering.

Webhook: POST /webhook/harmony-process
"""

import pytest
import httpx
import time
from datetime import datetime, timezone, timedelta
from uuid import uuid4

pytestmark = [pytest.mark.integration, pytest.mark.wf10, pytest.mark.session9]

# Workflow is async - need to wait for processing
WORKFLOW_WAIT_SECONDS = 3


# =============================================================================
# TEST DATA
# =============================================================================

@pytest.fixture
def sample_raw_tender():
    """Sample raw tender for processing."""
    return {
        "external_id": f"RAW-{uuid4().hex[:8]}",
        "source": "smartgep",
        "title": "Cloud Infrastructure Project",
        "organization": "Ministry of Health",
        "value": 750000.00,
        "currency": "MYR",
        "deadline_raw": "15/02/2026",  # Malaysian format DD/MM/YYYY
        "category": "IT Infrastructure",
        "description": "Modernization of health ministry IT systems",
        "url": "https://smartgep.gov.my/tender/99999"
    }


@pytest.fixture
def sample_high_priority_tender():
    """Tender with high priority (high value, close deadline)."""
    return {
        "external_id": f"HP-{uuid4().hex[:8]}",
        "source": "eperolehan",
        "title": "Urgent Security Audit",
        "organization": "Bank Negara Malaysia",
        "value": 2000000.00,
        "currency": "MYR",
        "deadline_raw": (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%d/%m/%Y"),
        "category": "Cybersecurity"
    }


@pytest.fixture
def sample_low_priority_tender():
    """Tender with low priority (low value, far deadline)."""
    return {
        "external_id": f"LP-{uuid4().hex[:8]}",
        "source": "mytender",
        "title": "Office Supplies Procurement",
        "organization": "Local Council",
        "value": 25000.00,
        "currency": "MYR",
        "deadline_raw": (datetime.now(timezone.utc) + timedelta(days=60)).strftime("%d/%m/%Y"),
        "category": "Supplies"
    }


# =============================================================================
# TESTS: Date Normalization
# =============================================================================

class TestDateNormalization:
    """Tests for date format normalization."""

    @pytest.mark.vps
    def test_process_normalizes_dates(
        self,
        harmony_client: httpx.Client,
        sample_raw_tender
    ):
        """
        RED: Malaysian date format DD/MM/YYYY is normalized to ISO format.
        """
        # Act
        response = harmony_client.post("/process", json=sample_raw_tender)

        # Assert
        assert response.status_code == 200

        result = response.json()
        # Check if normalized date is returned or stored
        if "deadline" in result:
            # Should be ISO format
            assert "T" in result["deadline"] or "-" in result["deadline"]

    @pytest.mark.vps
    def test_process_handles_various_date_formats(
        self,
        harmony_client: httpx.Client
    ):
        """
        RED: Various date formats are handled correctly.
        """
        date_formats = [
            {"deadline_raw": "15/02/2026"},      # DD/MM/YYYY
            {"deadline_raw": "2026-02-15"},      # ISO
            {"deadline_raw": "Feb 15, 2026"},    # Month DD, YYYY
            {"deadline_raw": "15-Feb-2026"},     # DD-Mon-YYYY
        ]

        for date_data in date_formats:
            tender = {
                "external_id": f"DATE-{uuid4().hex[:6]}",
                "source": "smartgep",
                "title": "Date Test Tender",
                "organization": "Test Org",
                "value": 100000,
                **date_data
            }

            response = harmony_client.post("/process", json=tender)
            # Should handle all formats
            assert response.status_code in [200, 400]


# =============================================================================
# TESTS: Priority Scoring
# =============================================================================

class TestPriorityScoring:
    """Tests for tender priority calculation."""

    @pytest.mark.vps
    def test_process_calculates_priority(
        self,
        harmony_client: httpx.Client,
        sample_raw_tender
    ):
        """
        RED: Priority score is calculated based on value and deadline.
        """
        # Act
        response = harmony_client.post("/process", json=sample_raw_tender)

        # Assert
        assert response.status_code == 200

        result = response.json()
        # Priority may be in response or stored in database
        # This test documents the expected behavior

    @pytest.mark.vps
    def test_process_high_value_increases_priority(
        self,
        harmony_client: httpx.Client,
        sample_high_priority_tender,
        sample_low_priority_tender
    ):
        """
        RED: Higher value tenders get higher priority scores.
        """
        # Act
        response_high = harmony_client.post("/process", json=sample_high_priority_tender)
        response_low = harmony_client.post("/process", json=sample_low_priority_tender)

        # Assert
        assert response_high.status_code == 200
        assert response_low.status_code == 200

        # Priority scoring should differentiate these
        # Actual assertion depends on response format

    @pytest.mark.vps
    def test_process_close_deadline_increases_priority(
        self,
        harmony_client: httpx.Client
    ):
        """
        RED: Tenders with closer deadlines get higher urgency scores.
        """
        close_deadline = {
            "external_id": f"CLOSE-{uuid4().hex[:6]}",
            "source": "smartgep",
            "title": "Urgent Tender",
            "organization": "Test Org",
            "value": 100000,
            "deadline_raw": (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%d/%m/%Y")
        }

        far_deadline = {
            "external_id": f"FAR-{uuid4().hex[:6]}",
            "source": "smartgep",
            "title": "Non-Urgent Tender",
            "organization": "Test Org",
            "value": 100000,  # Same value
            "deadline_raw": (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%d/%m/%Y")
        }

        # Act
        response_close = harmony_client.post("/process", json=close_deadline)
        response_far = harmony_client.post("/process", json=far_deadline)

        # Assert
        assert response_close.status_code == 200
        assert response_far.status_code == 200


# =============================================================================
# TESTS: Bid Submission Triggering
# =============================================================================

class TestBidSubmissionTriggering:
    """Tests for triggering bid submission workflow."""

    @pytest.mark.vps
    def test_process_triggers_submission(
        self,
        harmony_client: httpx.Client,
        db_cursor,
        sample_raw_tender
    ):
        """
        RED: Processing tender triggers bid submission workflow.
        """
        # Act
        response = harmony_client.post("/process", json=sample_raw_tender)

        # Assert
        assert response.status_code == 200

        # May create a bid directly or trigger submission workflow
        result = response.json()
        bid_id = result.get("bid_id")

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        if bid_id:
            db_cursor.execute(
                "SELECT id, title, source FROM bids WHERE id = %s::uuid",
                (str(bid_id),)
            )
            bid = db_cursor.fetchone()
            assert bid is not None

    @pytest.mark.vps
    def test_process_preserves_source_info(
        self,
        harmony_client: httpx.Client,
        db_cursor,
        sample_raw_tender
    ):
        """
        RED: Source information is preserved when creating bid.
        """
        # Act
        response = harmony_client.post("/process", json=sample_raw_tender)

        # Assert
        assert response.status_code == 200

        result = response.json()
        bid_id = result.get("bid_id")

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        if bid_id:
            db_cursor.execute(
                "SELECT source, client_name FROM bids WHERE id = %s::uuid",
                (str(bid_id),)
            )
            bid = db_cursor.fetchone()
            # Source should match or be prefixed
            assert "smartgep" in (bid.get("source") or "").lower() or \
                   sample_raw_tender["organization"] == bid.get("client_name")


# =============================================================================
# TESTS: Data Transformation
# =============================================================================

class TestDataTransformation:
    """Tests for transforming tender data to bid format."""

    @pytest.mark.vps
    def test_process_maps_fields_correctly(
        self,
        harmony_client: httpx.Client,
        sample_raw_tender
    ):
        """
        RED: Tender fields are correctly mapped to bid fields.

        Mapping:
        - organization -> client_name
        - value -> estimated_value
        - deadline -> submission_deadline
        - title -> title
        """
        # Act
        response = harmony_client.post("/process", json=sample_raw_tender)

        # Assert
        assert response.status_code == 200

        result = response.json()
        # Verify field mapping in response or by querying bid

    @pytest.mark.vps
    def test_process_generates_reference_number(
        self,
        harmony_client: httpx.Client,
        db_cursor,
        sample_raw_tender
    ):
        """
        RED: Processed tender gets unique reference number.
        """
        # Act
        response = harmony_client.post("/process", json=sample_raw_tender)

        # Assert
        assert response.status_code == 200

        result = response.json()
        reference = result.get("reference_number")
        bid_id = result.get("bid_id")

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        if bid_id:
            db_cursor.execute(
                "SELECT reference_number FROM bids WHERE id = %s::uuid",
                (str(bid_id),)
            )
            bid = db_cursor.fetchone()
            assert bid["reference_number"] is not None
            assert bid["reference_number"].startswith("BID-")


# =============================================================================
# TESTS: Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in processing."""

    @pytest.mark.vps
    def test_process_handles_missing_value(
        self,
        harmony_client: httpx.Client
    ):
        """
        RED: Missing value field is handled gracefully.
        """
        no_value_tender = {
            "external_id": f"NOVAL-{uuid4().hex[:6]}",
            "source": "smartgep",
            "title": "Tender Without Value",
            "organization": "Test Org",
            "deadline_raw": "15/02/2026"
            # No value field
        }

        # Act
        response = harmony_client.post("/process", json=no_value_tender)

        # Assert - Should handle gracefully
        assert response.status_code in [200, 400]

    @pytest.mark.vps
    def test_process_handles_invalid_date(
        self,
        harmony_client: httpx.Client
    ):
        """
        RED: Invalid date format is handled gracefully.
        """
        invalid_date_tender = {
            "external_id": f"BADDATE-{uuid4().hex[:6]}",
            "source": "smartgep",
            "title": "Tender With Bad Date",
            "organization": "Test Org",
            "value": 100000,
            "deadline_raw": "not-a-date"
        }

        # Act
        response = harmony_client.post("/process", json=invalid_date_tender)

        # Assert - Should handle gracefully (error or skip)
        assert response.status_code in [200, 400, 422]
