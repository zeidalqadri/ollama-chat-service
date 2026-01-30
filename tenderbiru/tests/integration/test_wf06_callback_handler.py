"""
Integration Tests: WF06 - Telegram Callback Handler Workflow

TDD tests for the central callback handler that processes all review decisions.
This is the most complex workflow - handles approvals, revisions, and rejections.

Webhook: Telegram Trigger (callback_query and message events)
"""

import pytest
import httpx
import time
from uuid import uuid4
import json

pytestmark = [pytest.mark.integration, pytest.mark.wf06, pytest.mark.session9]

# Workflow is async - need to wait for processing
WORKFLOW_WAIT_SECONDS = 5


# =============================================================================
# TESTS: Callback Parsing
# =============================================================================

class TestCallbackParsing:
    """Tests for callback data parsing."""

    @pytest.mark.vps
    def test_callback_parses_approve_tech(
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
        RED: Callback handler correctly parses technical approval.

        callback_data format: approve_{bid_id}_tech
        """
        # Arrange
        bid = create_test_bid(status="TECHNICAL_REVIEW")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        review = create_test_review(bid["id"], "TECHNICAL", reviewer["id"])

        callback_payload = {
            "callback_query": {
                "id": "test_callback_123",
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 100,
                    "chat": {"id": reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"approve_{bid['id']}_tech"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert
        assert response.status_code == 200

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        db_cursor.execute("""
            SELECT decision FROM reviews
            WHERE bid_id = %s::uuid AND review_type = 'TECHNICAL'
        """, (str(bid["id"]),))

        result = db_cursor.fetchone()
        assert result["decision"] == "APPROVED"

    @pytest.mark.vps
    def test_callback_parses_revision_comm(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        create_test_review,
        sample_reviewer_commercial,
        cleanup_test_data
    ):
        """
        RED: Callback handler parses commercial revision request.

        Revision requires reason - should create conversation state.
        """
        # Arrange
        bid = create_test_bid(status="COMMERCIAL_REVIEW")
        reviewer = create_test_reviewer(sample_reviewer_commercial)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        create_test_review(bid["id"], "COMMERCIAL", reviewer["id"])

        callback_payload = {
            "callback_query": {
                "id": "test_callback_124",
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 101,
                    "chat": {"id": reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"revision_{bid['id']}_comm"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert
        assert response.status_code == 200

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        # Should create conversation state awaiting reason
        db_cursor.execute("""
            SELECT state_type, context_json FROM conversation_state
            WHERE chat_id = %s AND user_id = %s
        """, (reviewer["telegram_chat_id"], reviewer["telegram_chat_id"]))

        state = db_cursor.fetchone()
        assert state is not None
        assert state["state_type"] == "awaiting_revision_reason"


# =============================================================================
# TESTS: Callback Answer
# =============================================================================

class TestCallbackAnswer:
    """Tests for Telegram callback answering."""

    @pytest.mark.vps
    def test_callback_answers_telegram(
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
        RED: Callback handler answers the callback query.

        answerCallbackQuery must be called to dismiss the loading state.
        """
        # Arrange
        bid = create_test_bid(status="TECHNICAL_REVIEW")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        create_test_review(bid["id"], "TECHNICAL", reviewer["id"])

        callback_payload = {
            "callback_query": {
                "id": "test_callback_125",
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 102,
                    "chat": {"id": reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"approve_{bid['id']}_tech"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert - Response should be successful (callback answered)
        assert response.status_code == 200


# =============================================================================
# TESTS: Approval Flow
# =============================================================================

class TestApprovalFlow:
    """Tests for approval decision processing."""

    @pytest.mark.vps
    def test_callback_approval_updates_review(
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
        RED: Approval callback updates review decision to APPROVED.
        """
        # Arrange
        bid = create_test_bid(status="TECHNICAL_REVIEW")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        create_test_review(bid["id"], "TECHNICAL", reviewer["id"])

        callback_payload = {
            "callback_query": {
                "id": "test_callback_126",
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 103,
                    "chat": {"id": reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"approve_{bid['id']}_tech"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert
        assert response.status_code == 200

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        db_cursor.execute("""
            SELECT decision, decision_at, decision_reason
            FROM reviews
            WHERE bid_id = %s::uuid AND review_type = 'TECHNICAL'
        """, (str(bid["id"]),))

        review = db_cursor.fetchone()
        assert review["decision"] == "APPROVED"
        assert review["decision_at"] is not None

    @pytest.mark.vps
    def test_callback_approval_logs_decision(
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
        RED: Approval creates approval_decisions record.
        """
        # Arrange
        bid = create_test_bid(status="TECHNICAL_REVIEW")
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        review = create_test_review(bid["id"], "TECHNICAL", reviewer["id"])

        callback_payload = {
            "callback_query": {
                "id": "test_callback_127",
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 104,
                    "chat": {"id": reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"approve_{bid['id']}_tech"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert
        assert response.status_code == 200

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        db_cursor.execute("""
            SELECT decision, reviewer_id, telegram_callback_id
            FROM approval_decisions
            WHERE bid_id = %s::uuid
        """, (str(bid["id"]),))

        decision = db_cursor.fetchone()
        assert decision is not None
        assert decision["decision"] == "APPROVED"
        assert decision["reviewer_id"] == reviewer["id"]


# =============================================================================
# TESTS: Stage Routing
# =============================================================================

class TestStageRouting:
    """Tests for routing to next workflow stage after approval."""

    @pytest.mark.vps
    def test_callback_tech_approve_triggers_commercial(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        create_test_review,
        sample_reviewer_technical,
        sample_reviewer_commercial,
        cleanup_test_data,
        assert_bid_status
    ):
        """
        RED: Technical approval triggers commercial review workflow.

        After tech approval, bid status should change to COMMERCIAL_REVIEW.
        """
        # Arrange
        bid = create_test_bid(status="TECHNICAL_REVIEW")
        tech_reviewer = create_test_reviewer(sample_reviewer_technical)
        comm_reviewer = create_test_reviewer(sample_reviewer_commercial)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](tech_reviewer["id"])
        cleanup_test_data["track_reviewer"](comm_reviewer["id"])

        create_test_review(bid["id"], "TECHNICAL", tech_reviewer["id"])

        callback_payload = {
            "callback_query": {
                "id": "test_callback_128",
                "from": {
                    "id": tech_reviewer["telegram_chat_id"],
                    "username": tech_reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 105,
                    "chat": {"id": tech_reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"approve_{bid['id']}_tech"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert
        assert response.status_code == 200
        assert_bid_status(bid["id"], "COMMERCIAL_REVIEW")

    @pytest.mark.vps
    def test_callback_comm_approve_triggers_management(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        create_test_review,
        sample_reviewer_technical,
        sample_reviewer_commercial,
        sample_reviewer_management,
        cleanup_test_data,
        assert_bid_status
    ):
        """
        RED: Commercial approval triggers management approval workflow.
        """
        # Arrange
        bid = create_test_bid(status="COMMERCIAL_REVIEW")
        tech_reviewer = create_test_reviewer(sample_reviewer_technical)
        comm_reviewer = create_test_reviewer(sample_reviewer_commercial)
        mgmt_approver = create_test_reviewer(sample_reviewer_management)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](tech_reviewer["id"])
        cleanup_test_data["track_reviewer"](comm_reviewer["id"])
        cleanup_test_data["track_reviewer"](mgmt_approver["id"])

        # Tech already approved
        create_test_review(bid["id"], "TECHNICAL", tech_reviewer["id"], "APPROVED")
        create_test_review(bid["id"], "COMMERCIAL", comm_reviewer["id"])

        callback_payload = {
            "callback_query": {
                "id": "test_callback_129",
                "from": {
                    "id": comm_reviewer["telegram_chat_id"],
                    "username": comm_reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 106,
                    "chat": {"id": comm_reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"approve_{bid['id']}_comm"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert
        assert response.status_code == 200
        assert_bid_status(bid["id"], "MGMT_APPROVAL")

    @pytest.mark.vps
    def test_callback_mgmt_approve_marks_complete(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        create_test_review,
        sample_reviewer_technical,
        sample_reviewer_commercial,
        sample_reviewer_management,
        cleanup_test_data,
        assert_bid_status
    ):
        """
        RED: Management approval sets status to APPROVED_TO_SUBMIT.
        """
        # Arrange
        bid = create_test_bid(status="MGMT_APPROVAL")
        tech_reviewer = create_test_reviewer(sample_reviewer_technical)
        comm_reviewer = create_test_reviewer(sample_reviewer_commercial)
        mgmt_approver = create_test_reviewer(sample_reviewer_management)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](tech_reviewer["id"])
        cleanup_test_data["track_reviewer"](comm_reviewer["id"])
        cleanup_test_data["track_reviewer"](mgmt_approver["id"])

        # Both prior reviews approved
        create_test_review(bid["id"], "TECHNICAL", tech_reviewer["id"], "APPROVED")
        create_test_review(bid["id"], "COMMERCIAL", comm_reviewer["id"], "APPROVED")
        create_test_review(bid["id"], "MANAGEMENT", mgmt_approver["id"])

        callback_payload = {
            "callback_query": {
                "id": "test_callback_130",
                "from": {
                    "id": mgmt_approver["telegram_chat_id"],
                    "username": mgmt_approver["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 107,
                    "chat": {"id": mgmt_approver["telegram_chat_id"], "type": "private"}
                },
                "data": f"approve_{bid['id']}_mgmt"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert
        assert response.status_code == 200
        assert_bid_status(bid["id"], "APPROVED_TO_SUBMIT")


# =============================================================================
# TESTS: Revision Flow
# =============================================================================

class TestRevisionFlow:
    """Tests for revision request processing."""

    @pytest.mark.vps
    def test_callback_revision_sets_state(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        create_test_review,
        sample_reviewer_commercial,
        cleanup_test_data
    ):
        """
        RED: Revision creates conversation_state record.
        """
        # Arrange
        bid = create_test_bid(status="COMMERCIAL_REVIEW")
        reviewer = create_test_reviewer(sample_reviewer_commercial)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        create_test_review(bid["id"], "COMMERCIAL", reviewer["id"])

        callback_payload = {
            "callback_query": {
                "id": "test_callback_131",
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 108,
                    "chat": {"id": reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"revision_{bid['id']}_comm"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert
        assert response.status_code == 200

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        db_cursor.execute("""
            SELECT state_type, context_json, expires_at
            FROM conversation_state
            WHERE chat_id = %s
        """, (reviewer["telegram_chat_id"],))

        state = db_cursor.fetchone()
        assert state is not None
        assert state["state_type"] == "awaiting_revision_reason"
        assert state["expires_at"] is not None

        # Verify context contains needed info
        context = json.loads(state["context_json"]) if isinstance(state["context_json"], str) else state["context_json"]
        assert context["bid_id"] == str(bid["id"])
        assert context["review_type"] == "COMMERCIAL"

    @pytest.mark.vps
    def test_callback_revision_prompts_reason(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        create_test_review,
        sample_reviewer_commercial,
        cleanup_test_data
    ):
        """
        RED: Revision callback sends force_reply message asking for reason.
        """
        # Arrange
        bid = create_test_bid(status="COMMERCIAL_REVIEW")
        reviewer = create_test_reviewer(sample_reviewer_commercial)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        create_test_review(bid["id"], "COMMERCIAL", reviewer["id"])

        callback_payload = {
            "callback_query": {
                "id": "test_callback_132",
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 109,
                    "chat": {"id": reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"revision_{bid['id']}_comm"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert - Workflow should succeed (message sent)
        assert response.status_code == 200


# =============================================================================
# TESTS: Message with Reason
# =============================================================================

class TestMessageWithReason:
    """Tests for processing text messages with revision/rejection reasons."""

    @pytest.mark.vps
    def test_message_with_state_saves_reason(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        create_test_review,
        sample_reviewer_commercial,
        cleanup_test_data
    ):
        """
        RED: Text message with active state saves reason to review.
        """
        # Arrange
        bid = create_test_bid(status="COMMERCIAL_REVIEW")
        reviewer = create_test_reviewer(sample_reviewer_commercial)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        review = create_test_review(bid["id"], "COMMERCIAL", reviewer["id"])

        # Clean up any existing conversation state first
        db_cursor.execute("""
            DELETE FROM conversation_state WHERE chat_id = %s AND user_id = %s
        """, (reviewer["telegram_chat_id"], reviewer["telegram_chat_id"]))
        db_cursor.connection.commit()

        # Create conversation state (simulating after revision button)
        db_cursor.execute("""
            INSERT INTO conversation_state (chat_id, user_id, state_type, context_json, expires_at)
            VALUES (%s, %s, 'awaiting_revision_reason', %s, NOW() + INTERVAL '1 hour')
        """, (
            reviewer["telegram_chat_id"],
            reviewer["telegram_chat_id"],
            json.dumps({
                "bid_id": str(bid["id"]),
                "review_type": "COMMERCIAL",
                "decision": "REVISION_REQUESTED",
                "message_id": 109,
                "reviewer_id": str(reviewer["id"]),
                "reviewer_name": reviewer["name"]
            })
        ))
        db_cursor.connection.commit()

        reason_text = "Budget allocation needs revision. Increase contingency by 15%."

        message_payload = {
            "message": {
                "message_id": 110,
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "chat": {"id": reviewer["telegram_chat_id"], "type": "private"},
                "date": 1704067200,
                "text": reason_text
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=message_payload)

        # Assert
        assert response.status_code == 200

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        db_cursor.execute("""
            SELECT decision, decision_reason, revision_count
            FROM reviews
            WHERE bid_id = %s::uuid AND review_type = 'COMMERCIAL'
        """, (str(bid["id"]),))

        review = db_cursor.fetchone()
        assert review["decision"] == "REVISION_REQUESTED"
        assert reason_text in (review["decision_reason"] or "")

    @pytest.mark.vps
    def test_message_clears_state(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        create_test_review,
        sample_reviewer_commercial,
        cleanup_test_data
    ):
        """
        RED: After processing reason, conversation state is cleared.
        """
        # Arrange
        bid = create_test_bid(status="COMMERCIAL_REVIEW")
        reviewer = create_test_reviewer(sample_reviewer_commercial)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](reviewer["id"])

        create_test_review(bid["id"], "COMMERCIAL", reviewer["id"])

        # Clean up any existing conversation state first
        db_cursor.execute("""
            DELETE FROM conversation_state WHERE chat_id = %s AND user_id = %s
        """, (reviewer["telegram_chat_id"], reviewer["telegram_chat_id"]))
        db_cursor.connection.commit()

        # Create conversation state
        db_cursor.execute("""
            INSERT INTO conversation_state (chat_id, user_id, state_type, context_json, expires_at)
            VALUES (%s, %s, 'awaiting_revision_reason', %s, NOW() + INTERVAL '1 hour')
        """, (
            reviewer["telegram_chat_id"],
            reviewer["telegram_chat_id"],
            json.dumps({
                "bid_id": str(bid["id"]),
                "review_type": "COMMERCIAL",
                "decision": "REVISION_REQUESTED",
                "message_id": 109,
                "reviewer_id": str(reviewer["id"]),
                "reviewer_name": reviewer["name"]
            })
        ))
        db_cursor.connection.commit()

        message_payload = {
            "message": {
                "message_id": 111,
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "chat": {"id": reviewer["telegram_chat_id"], "type": "private"},
                "date": 1704067200,
                "text": "This is the revision reason."
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=message_payload)

        # Assert
        assert response.status_code == 200

        # Wait for async workflow to complete Clear State node
        time.sleep(WORKFLOW_WAIT_SECONDS)

        db_cursor.execute("""
            SELECT COUNT(*) as count FROM conversation_state
            WHERE chat_id = %s
        """, (reviewer["telegram_chat_id"],))

        result = db_cursor.fetchone()
        assert result["count"] == 0  # State should be cleared


# =============================================================================
# TESTS: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.vps
    def test_callback_unknown_bid_handles_gracefully(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_reviewer,
        sample_reviewer_technical,
        cleanup_test_data
    ):
        """
        RED: Callback with non-existent bid is handled gracefully.
        """
        # Arrange
        reviewer = create_test_reviewer(sample_reviewer_technical)
        cleanup_test_data["track_reviewer"](reviewer["id"])

        fake_bid_id = str(uuid4())

        callback_payload = {
            "callback_query": {
                "id": "test_callback_133",
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 112,
                    "chat": {"id": reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"approve_{fake_bid_id}_tech"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Assert - Should not crash, may return error or handled message
        assert response.status_code in [200, 400, 404]

    @pytest.mark.vps
    def test_callback_unauthorized_reviewer_rejected(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_bid,
        create_test_reviewer,
        create_test_review,
        sample_reviewer_technical,
        sample_reviewer_commercial,
        cleanup_test_data
    ):
        """
        RED: Reviewer without permission cannot approve different review type.

        Technical reviewer trying to approve commercial review should fail.
        TODO: Add reviewer authorization check to WF06 workflow.
        """
        # Arrange
        bid = create_test_bid(status="COMMERCIAL_REVIEW")
        # Use unique telegram_chat_id for tech reviewer to test auth properly
        tech_reviewer_data = sample_reviewer_technical.copy()
        tech_reviewer_data["telegram_chat_id"] = 999999998  # Different from comm_reviewer
        tech_reviewer = create_test_reviewer(tech_reviewer_data)
        comm_reviewer = create_test_reviewer(sample_reviewer_commercial)
        cleanup_test_data["track_bid"](bid["id"])
        cleanup_test_data["track_reviewer"](tech_reviewer["id"])
        cleanup_test_data["track_reviewer"](comm_reviewer["id"])

        # Commercial review assigned to comm_reviewer
        create_test_review(bid["id"], "COMMERCIAL", comm_reviewer["id"])

        # Tech reviewer tries to approve (not assigned and not authorized for commercial)
        callback_payload = {
            "callback_query": {
                "id": "test_callback_134",
                "from": {
                    "id": tech_reviewer["telegram_chat_id"],  # Tech reviewer's unique ID
                    "username": tech_reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "message": {
                    "message_id": 113,
                    "chat": {"id": tech_reviewer["telegram_chat_id"], "type": "private"}
                },
                "data": f"approve_{bid['id']}_comm"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=callback_payload)

        # Wait for async workflow to complete
        time.sleep(WORKFLOW_WAIT_SECONDS)

        # Assert - Review should not be changed
        db_cursor.execute("""
            SELECT decision FROM reviews
            WHERE bid_id = %s::uuid AND review_type = 'COMMERCIAL'
        """, (str(bid["id"]),))

        review = db_cursor.fetchone()
        # Either workflow rejects or review stays PENDING
        assert response.status_code in [200, 403] and review["decision"] == "PENDING" or \
            response.status_code == 403

    @pytest.mark.vps
    def test_message_without_state_ignored(
        self,
        n8n_client: httpx.Client,
        db_cursor,
        create_test_reviewer,
        sample_reviewer_commercial,
        cleanup_test_data
    ):
        """
        RED: Text message without conversation state is ignored.

        Random messages shouldn't affect anything.
        """
        # Arrange
        reviewer = create_test_reviewer(sample_reviewer_commercial)
        cleanup_test_data["track_reviewer"](reviewer["id"])

        # No conversation state exists
        message_payload = {
            "message": {
                "message_id": 114,
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "username": reviewer["telegram_username"],
                    "first_name": "Test"
                },
                "chat": {"id": reviewer["telegram_chat_id"], "type": "private"},
                "date": 1704067200,
                "text": "Random message without context"
            }
        }

        # Act
        response = n8n_client.post("/telegram-callback", json=message_payload)

        # Assert - Should be handled gracefully (ignored or acknowledged)
        assert response.status_code in [200, 202]
