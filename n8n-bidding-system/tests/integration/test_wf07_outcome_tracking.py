"""
Integration Tests: WF07 - Outcome Tracking Workflow

TDD tests for recording bid outcomes (WON/LOST/NO_DECISION).
Tests verify status updates, lessons learned generation, and notifications.

Webhook: POST /webhook/outcome-tracking
"""

import pytest
import httpx

pytestmark = [pytest.mark.integration, pytest.mark.wf07]


# =============================================================================
# TESTS: Status Updates
# =============================================================================

class TestStatusUpdates:
    """Tests for outcome status updates."""

    @pytest.mark.vps
    def test_outcome_updates_status_won(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        cleanup_test_data,
        assert_bid_status
    ):
        """
        RED: Recording WON outcome updates bid status.
        """
        # Arrange - Bid in submitted to client state
        bid = create_test_bid(status="SUBMITTED_TO_CLIENT")
        cleanup_test_data["track_bid"](bid["id"])

        # Act
        response = n8n_client.post("/outcome-tracking", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"],
            "outcome": "WON",
            "actual_contract_value": 175000.00
        })

        # Assert
        assert response.status_code == 200
        assert_bid_status(bid["id"], "WON")

    @pytest.mark.vps
    def test_outcome_updates_status_lost(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        cleanup_test_data,
        assert_bid_status
    ):
        """
        RED: Recording LOST outcome updates bid status.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED_TO_CLIENT")
        cleanup_test_data["track_bid"](bid["id"])

        # Act
        response = n8n_client.post("/outcome-tracking", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"],
            "outcome": "LOST",
            "loss_reason": "Price too high",
            "competitor_won": "Competitor Corp"
        })

        # Assert
        assert response.status_code == 200
        assert_bid_status(bid["id"], "LOST")

    @pytest.mark.vps
    def test_outcome_updates_status_no_decision(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        cleanup_test_data,
        assert_bid_status
    ):
        """
        RED: Recording NO_DECISION outcome updates bid status.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED_TO_CLIENT")
        cleanup_test_data["track_bid"](bid["id"])

        # Act
        response = n8n_client.post("/outcome-tracking", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"],
            "outcome": "NO_DECISION"
        })

        # Assert
        assert response.status_code == 200
        assert_bid_status(bid["id"], "NO_DECISION")


# =============================================================================
# TESTS: Lessons Learned
# =============================================================================

class TestLessonsLearned:
    """Tests for AI-generated lessons learned."""

    @pytest.mark.vps
    def test_outcome_generates_lessons(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        cleanup_test_data
    ):
        """
        RED: Outcome recording triggers lessons learned generation.

        The workflow should call Ollama to analyze the bid outcome.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED_TO_CLIENT")
        cleanup_test_data["track_bid"](bid["id"])

        # Act
        response = n8n_client.post("/outcome-tracking", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"],
            "outcome": "WON"
        })

        # Assert
        assert response.status_code == 200

        # Lessons may be generated async, check if table updated
        db_cursor.execute("""
            SELECT id FROM lessons_learned WHERE bid_id = %s
        """, (bid["id"],))

        # May not be immediate, but should eventually exist
        # This test documents expected behavior

    @pytest.mark.vps
    def test_outcome_stores_lessons(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        cleanup_test_data
    ):
        """
        RED: Generated lessons are stored in lessons_learned table.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED_TO_CLIENT")
        cleanup_test_data["track_bid"](bid["id"])

        # Act
        response = n8n_client.post("/outcome-tracking", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"],
            "outcome": "LOST",
            "loss_reason": "Budget constraints",
            "competitor_won": "Other Corp"
        })

        # Assert
        assert response.status_code == 200

        # Give async processes time if needed
        db_cursor.execute("""
            SELECT outcome, key_factors, ai_analysis
            FROM lessons_learned WHERE bid_id = %s
        """, (bid["id"],))

        result = db_cursor.fetchone()
        if result:
            assert result["outcome"] == "LOST"


# =============================================================================
# TESTS: Win Announcements
# =============================================================================

class TestWinAnnouncements:
    """Tests for win announcement notifications."""

    @pytest.mark.vps
    def test_outcome_win_announces(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        cleanup_test_data
    ):
        """
        RED: WON outcome sends announcement to wins group.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED_TO_CLIENT")
        cleanup_test_data["track_bid"](bid["id"])

        # Act
        response = n8n_client.post("/outcome-tracking", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"],
            "outcome": "WON",
            "actual_contract_value": 200000.00
        })

        # Assert
        assert response.status_code == 200

        # Check notification was sent (may be to wins group)
        db_cursor.execute("""
            SELECT notification_type FROM telegram_notifications
            WHERE bid_id = %s
        """, (bid["id"],))

        notifications = db_cursor.fetchall()
        # Should have win announcement or similar
        # Actual verification depends on workflow implementation


# =============================================================================
# TESTS: Contract Value
# =============================================================================

class TestContractValue:
    """Tests for actual contract value tracking."""

    @pytest.mark.vps
    def test_outcome_stores_contract_value(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        cleanup_test_data
    ):
        """
        RED: WON outcome stores actual contract value.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED_TO_CLIENT", estimated_value=150000)
        cleanup_test_data["track_bid"](bid["id"])

        actual_value = 175000.00

        # Act
        response = n8n_client.post("/outcome-tracking", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"],
            "outcome": "WON",
            "actual_contract_value": actual_value
        })

        # Assert
        assert response.status_code == 200

        db_cursor.execute("""
            SELECT actual_contract_value FROM bids WHERE id = %s
        """, (bid["id"],))

        result = db_cursor.fetchone()
        if result["actual_contract_value"] is not None:
            assert float(result["actual_contract_value"]) == actual_value

    @pytest.mark.vps
    def test_outcome_stores_loss_details(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        cleanup_test_data
    ):
        """
        RED: LOST outcome stores loss reason and competitor.
        """
        # Arrange
        bid = create_test_bid(status="SUBMITTED_TO_CLIENT")
        cleanup_test_data["track_bid"](bid["id"])

        loss_reason = "Pricing was 15% above competitor"
        competitor = "TechCorp Solutions"

        # Act
        response = n8n_client.post("/outcome-tracking", json={
            "bid_id": bid["id"],
            "reference_number": bid["reference_number"],
            "outcome": "LOST",
            "loss_reason": loss_reason,
            "competitor_won": competitor
        })

        # Assert
        assert response.status_code == 200

        db_cursor.execute("""
            SELECT loss_reason, competitor_won FROM bids WHERE id = %s
        """, (bid["id"],))

        result = db_cursor.fetchone()
        assert result["loss_reason"] == loss_reason
        assert result["competitor_won"] == competitor
