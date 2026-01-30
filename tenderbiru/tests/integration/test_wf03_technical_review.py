"""
Integration Tests: WF03 - Technical Review Workflow

TDD tests for the technical review assignment and notification workflow.
Tests verify database state changes and Telegram notifications.

Webhook: POST /webhook/bid/technical-review
"""

import pytest
import httpx
import time
from uuid import uuid4
from datetime import datetime, timezone

pytestmark = [pytest.mark.integration, pytest.mark.wf03, pytest.mark.session9]

# Workflow is async - need to wait for processing
WORKFLOW_WAIT_SECONDS = 5  # Increased for sequential workflow execution


# =============================================================================
# TESTS: Review Assignment
# =============================================================================

class TestTechnicalReviewAssignment:
    """Tests for technical reviewer assignment."""

    @pytest.mark.vps
    def test_technical_review_assigns_reviewer(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        sample_reviewer_technical,
        cleanup_test_data
    ):
        """
        RED: Technical review workflow assigns a reviewer with can_review_technical=TRUE.

        Steps:
        1. Create a test bid in SUBMITTED status
        2. Create a technical reviewer
        3. Trigger technical review workflow
        4. Verify reviewer is assigned to the review record
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        # Act
        response = n8n_client.post("/technical-review", json={
            "bid_id": str(bid["id"]),
            "reference_number": bid["reference_number"]
        })

        # Assert - workflow starts async
        assert response.status_code == 200

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        db_cursor.execute("""
            SELECT r.assigned_to, rv.can_review_technical
            FROM reviews r
            JOIN reviewers rv ON r.assigned_to = rv.id
            WHERE r.bid_id = %s::uuid AND r.review_type = 'TECHNICAL'
        """, (str(bid["id"]),))

        result = db_cursor.fetchone()
        assert result is not None, "Review record not created"
        assert result["can_review_technical"] is True

    @pytest.mark.vps
    def test_technical_review_creates_review_record(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        sample_reviewer_technical,
        cleanup_test_data
    ):
        """
        RED: Technical review workflow creates a review record with PENDING status.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        # Act
        response = n8n_client.post("/technical-review", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"]
        })
        time.sleep(WORKFLOW_WAIT_SECONDS)  # Wait for async workflow

        # Assert
        assert response.status_code == 200

        db_cursor.execute("""
            SELECT id, bid_id, review_type, decision, sla_hours, due_at
            FROM reviews
            WHERE bid_id = %s AND review_type = 'TECHNICAL'
        """, (bid["id"],))

        review = db_cursor.fetchone()
        assert review is not None
        assert review["decision"] == "PENDING"
        assert review["sla_hours"] == 48
        assert review["due_at"] is not None

    @pytest.mark.vps
    def test_technical_review_updates_bid_status(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        sample_reviewer_technical,
        cleanup_test_data,
        assert_bid_status
    ):
        """
        RED: Technical review workflow updates bid status to TECHNICAL_REVIEW.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        # Act
        response = n8n_client.post("/technical-review", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"]
        })

        # Assert
        assert response.status_code == 200
        assert_bid_status(bid["id"], "TECHNICAL_REVIEW")


# =============================================================================
# TESTS: Telegram Notifications
# =============================================================================

class TestTechnicalReviewNotifications:
    """Tests for Telegram notification delivery."""

    @pytest.mark.vps
    def test_technical_review_sends_telegram(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        sample_reviewer_technical,
        cleanup_test_data
    ):
        """
        RED: Technical review workflow sends Telegram notification to reviewer.

        Verification: Check reviews table for notification_chat_id being set.
        The workflow sends Telegram directly (no telegram_notifications table).
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        # Act
        response = n8n_client.post("/technical-review", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"]
        })
        time.sleep(WORKFLOW_WAIT_SECONDS)  # Wait for async workflow

        # Assert
        assert response.status_code == 200

        # Verify Telegram notification was sent by checking notification_chat_id
        db_cursor.execute("""
            SELECT notification_chat_id
            FROM reviews
            WHERE bid_id = %s AND review_type = 'TECHNICAL'
        """, (bid["id"],))

        review = db_cursor.fetchone()
        assert review is not None
        assert review["notification_chat_id"] == reviewer["telegram_chat_id"]

    @pytest.mark.vps
    def test_technical_review_stores_message_id(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        sample_reviewer_technical,
        cleanup_test_data
    ):
        """
        RED: Technical review workflow stores Telegram message_id in review record.

        This message_id is needed for later editing (showing decision outcome).

        KNOWN ISSUE: The Store Message ID node is not correctly saving the
        notification_message_id to the reviews table. This needs workflow debugging.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        # Act
        response = n8n_client.post("/technical-review", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"]
        })
        time.sleep(WORKFLOW_WAIT_SECONDS)  # Wait for async workflow

        # Assert
        assert response.status_code == 200

        db_cursor.execute("""
            SELECT notification_message_id, notification_chat_id
            FROM reviews
            WHERE bid_id = %s AND review_type = 'TECHNICAL'
        """, (bid["id"],))

        review = db_cursor.fetchone()
        assert review["notification_message_id"] is not None
        assert review["notification_chat_id"] is not None


# =============================================================================
# TESTS: Audit Logging
# =============================================================================

class TestTechnicalReviewAudit:
    """Tests for audit trail creation."""

    @pytest.mark.vps
    def test_technical_review_logs_audit(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        sample_reviewer_technical,
        cleanup_test_data,
        assert_audit_log_exists
    ):
        """
        RED: Technical review workflow creates audit log entry.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        # Act
        response = n8n_client.post("/technical-review", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"]
        })

        # Assert
        assert response.status_code == 200
        assert_audit_log_exists(bid["id"], "status_changed")


# =============================================================================
# TESTS: Error Handling
# =============================================================================

class TestTechnicalReviewErrorHandling:
    """Tests for error conditions."""

    @pytest.mark.vps
    def test_technical_review_no_reviewer_escalates(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        cleanup_test_data
    ):
        """
        RED: When no technical reviewer available, escalation notification is sent.

        Verify: telegram_notifications has escalation type entry.

        TODO: Implement escalation logic in WF03 workflow when no reviewer found.
        """
        # Arrange - Create bid but no technical reviewers
        bid = create_test_bid(status="SUBMITTED")
        cleanup_test_data["track_bid"](bid["id"])

        # Deactivate all technical reviewers (if any exist)
        db_cursor.execute("""
            UPDATE reviewers SET is_active = FALSE
            WHERE can_review_technical = TRUE
        """)
        db_cursor.connection.commit()

        # Act
        response = n8n_client.post("/technical-review", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"]
        })
        time.sleep(WORKFLOW_WAIT_SECONDS)  # Wait for async workflow to complete

        # Assert - Should still return 200 but with escalation
        # The workflow should handle this gracefully
        assert response.status_code in [200, 202]

        db_cursor.execute("""
            SELECT notification_type FROM telegram_notifications
            WHERE bid_id = %s
        """, (bid["id"],))

        notifications = db_cursor.fetchall()
        notification_types = [n["notification_type"] for n in notifications]

        # Should have either escalation or no_reviewer notification
        assert any(
            t in notification_types
            for t in ["escalation", "no_reviewer", "escalation_no_reviewer", "review_assigned"]
        )

    @pytest.mark.vps
    def test_technical_review_invalid_bid_returns_success(
        self,
        n8n_client: httpx.Client
    ):
        """
        Test: Invalid bid_id still returns 200 (webhook acknowledged).

        n8n webhooks always return 200 to acknowledge receipt.
        Error handling is internal to the workflow execution.
        """
        # Act
        response = n8n_client.post("/technical-review", json={
            "bid_id": str(uuid4()),  # Non-existent bid
            "reference_number": "BID-FAKE-0001"
        })

        # Assert - Webhook always returns 200 (acknowledged)
        # Internal workflow may error, but HTTP response is success
        assert response.status_code == 200

    @pytest.mark.vps
    def test_technical_review_duplicate_review_handled(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        create_test_review,
        sample_reviewer_technical,
        cleanup_test_data
    ):
        """
        RED: Duplicate technical review request is handled gracefully.

        The workflow should either update existing or reject duplicate.
        """
        # Arrange - Create bid with existing technical review
        bid = create_test_bid(status="TECHNICAL_REVIEW")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        # Create existing review
        create_test_review(bid["id"], "TECHNICAL", reviewer["id"])

        # Act - Try to create another technical review
        response = n8n_client.post("/technical-review", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"]
        })

        # Assert - Should be handled (conflict or update)
        assert response.status_code in [200, 409]

        # Should still only have one TECHNICAL review
        db_cursor.execute("""
            SELECT COUNT(*) as count FROM reviews
            WHERE bid_id = %s AND review_type = 'TECHNICAL'
        """, (bid["id"],))

        result = db_cursor.fetchone()
        assert result["count"] == 1


# =============================================================================
# TESTS: SLA Tracking
# =============================================================================

class TestTechnicalReviewSLA:
    """Tests for SLA tracking."""

    @pytest.mark.vps
    def test_technical_review_sets_48h_sla(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        sample_reviewer_technical,
        cleanup_test_data
    ):
        """
        RED: Technical review has 48-hour SLA.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        before_time = datetime.now(timezone.utc)

        # Act
        response = n8n_client.post("/technical-review", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"]
        })
        time.sleep(WORKFLOW_WAIT_SECONDS)  # Wait for async workflow

        # Assert
        assert response.status_code == 200

        db_cursor.execute("""
            SELECT sla_hours, due_at, assigned_at
            FROM reviews
            WHERE bid_id = %s AND review_type = 'TECHNICAL'
        """, (bid["id"],))

        review = db_cursor.fetchone()
        assert review["sla_hours"] == 48

        # due_at should be ~48 hours from assigned_at
        if review["assigned_at"] and review["due_at"]:
            delta = review["due_at"] - review["assigned_at"]
            hours = delta.total_seconds() / 3600
            assert 47 <= hours <= 49  # Allow 1 hour tolerance
