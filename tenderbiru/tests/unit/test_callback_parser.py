"""
Unit Tests: Callback Parser Logic

TDD tests for parsing Telegram callback_data format.
Format: action_bidId_reviewType

RED: Write failing tests first
GREEN: These tests document expected behavior from n8n workflow
"""

import pytest
from uuid import uuid4


# =============================================================================
# CALLBACK PARSER LOGIC (extracted from n8n workflow for testing)
# =============================================================================

def parse_callback_data(callback_data: str) -> dict:
    """
    Parse callback_data from Telegram inline keyboard.

    Format: action_bidId_reviewType
    Examples:
        - approve_550e8400-e29b-41d4-a716-446655440000_tech
        - revision_550e8400-e29b-41d4-a716-446655440000_comm
        - reject_550e8400-e29b-41d4-a716-446655440000_mgmt

    Returns:
        dict with parsed fields
    """
    parts = callback_data.split("_")

    if len(parts) < 3:
        raise ValueError(f"Invalid callback_data format: {callback_data}")

    # Handle UUIDs which contain hyphens (but we split on underscore)
    # action_uuid-part1-part2-part3-part4_reviewType
    action = parts[0]
    review_type_abbrev = parts[-1]
    bid_id = "_".join(parts[1:-1])  # Rejoin middle parts (UUID)

    # Map short codes to full review types
    review_type_map = {
        "tech": "TECHNICAL",
        "comm": "COMMERCIAL",
        "mgmt": "MANAGEMENT"
    }

    full_review_type = review_type_map.get(review_type_abbrev)
    if not full_review_type:
        raise ValueError(f"Invalid review type: {review_type_abbrev}")

    # Map actions to decisions
    decision_map = {
        "approve": "APPROVED",
        "revision": "REVISION_REQUESTED",
        "reject": "REJECTED"
    }

    decision = decision_map.get(action)
    if not decision:
        raise ValueError(f"Invalid action: {action}")

    return {
        "action": action,
        "decision": decision,
        "bid_id": bid_id,
        "review_type": full_review_type,
        "needs_reason": action != "approve"
    }


# =============================================================================
# TESTS: Valid Callback Data
# =============================================================================

class TestCallbackParserValidData:
    """Tests for valid callback data parsing."""

    @pytest.mark.unit
    def test_parse_approve_tech(self):
        """RED: Parse technical approval callback."""
        bid_id = str(uuid4())
        callback_data = f"approve_{bid_id}_tech"

        result = parse_callback_data(callback_data)

        assert result["action"] == "approve"
        assert result["decision"] == "APPROVED"
        assert result["bid_id"] == bid_id
        assert result["review_type"] == "TECHNICAL"
        assert result["needs_reason"] is False

    @pytest.mark.unit
    def test_parse_approve_comm(self):
        """RED: Parse commercial approval callback."""
        bid_id = str(uuid4())
        callback_data = f"approve_{bid_id}_comm"

        result = parse_callback_data(callback_data)

        assert result["action"] == "approve"
        assert result["decision"] == "APPROVED"
        assert result["review_type"] == "COMMERCIAL"
        assert result["needs_reason"] is False

    @pytest.mark.unit
    def test_parse_approve_mgmt(self):
        """RED: Parse management approval callback."""
        bid_id = str(uuid4())
        callback_data = f"approve_{bid_id}_mgmt"

        result = parse_callback_data(callback_data)

        assert result["action"] == "approve"
        assert result["decision"] == "APPROVED"
        assert result["review_type"] == "MANAGEMENT"
        assert result["needs_reason"] is False

    @pytest.mark.unit
    def test_parse_revision_tech(self):
        """RED: Parse technical revision request callback."""
        bid_id = str(uuid4())
        callback_data = f"revision_{bid_id}_tech"

        result = parse_callback_data(callback_data)

        assert result["action"] == "revision"
        assert result["decision"] == "REVISION_REQUESTED"
        assert result["review_type"] == "TECHNICAL"
        assert result["needs_reason"] is True

    @pytest.mark.unit
    def test_parse_revision_comm(self):
        """RED: Parse commercial revision request callback."""
        bid_id = str(uuid4())
        callback_data = f"revision_{bid_id}_comm"

        result = parse_callback_data(callback_data)

        assert result["action"] == "revision"
        assert result["decision"] == "REVISION_REQUESTED"
        assert result["review_type"] == "COMMERCIAL"
        assert result["needs_reason"] is True

    @pytest.mark.unit
    def test_parse_reject_tech(self):
        """RED: Parse technical rejection callback."""
        bid_id = str(uuid4())
        callback_data = f"reject_{bid_id}_tech"

        result = parse_callback_data(callback_data)

        assert result["action"] == "reject"
        assert result["decision"] == "REJECTED"
        assert result["review_type"] == "TECHNICAL"
        assert result["needs_reason"] is True

    @pytest.mark.unit
    def test_parse_reject_comm(self):
        """RED: Parse commercial rejection callback."""
        bid_id = str(uuid4())
        callback_data = f"reject_{bid_id}_comm"

        result = parse_callback_data(callback_data)

        assert result["action"] == "reject"
        assert result["decision"] == "REJECTED"
        assert result["review_type"] == "COMMERCIAL"
        assert result["needs_reason"] is True

    @pytest.mark.unit
    def test_parse_reject_mgmt(self):
        """RED: Parse management rejection callback."""
        bid_id = str(uuid4())
        callback_data = f"reject_{bid_id}_mgmt"

        result = parse_callback_data(callback_data)

        assert result["action"] == "reject"
        assert result["decision"] == "REJECTED"
        assert result["review_type"] == "MANAGEMENT"
        assert result["needs_reason"] is True


# =============================================================================
# TESTS: Invalid Callback Data
# =============================================================================

class TestCallbackParserInvalidData:
    """Tests for invalid callback data handling."""

    @pytest.mark.unit
    def test_parse_empty_string_raises(self):
        """RED: Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid callback_data format"):
            parse_callback_data("")

    @pytest.mark.unit
    def test_parse_missing_parts_raises(self):
        """RED: Missing parts should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid callback_data format"):
            parse_callback_data("approve_only")

    @pytest.mark.unit
    def test_parse_invalid_action_raises(self):
        """RED: Invalid action should raise ValueError."""
        bid_id = str(uuid4())
        with pytest.raises(ValueError, match="Invalid action"):
            parse_callback_data(f"invalid_{bid_id}_tech")

    @pytest.mark.unit
    def test_parse_invalid_review_type_raises(self):
        """RED: Invalid review type should raise ValueError."""
        bid_id = str(uuid4())
        with pytest.raises(ValueError, match="Invalid review type"):
            parse_callback_data(f"approve_{bid_id}_invalid")

    @pytest.mark.unit
    def test_parse_unknown_review_abbreviation_raises(self):
        """RED: Unknown review abbreviation should raise ValueError."""
        bid_id = str(uuid4())
        with pytest.raises(ValueError, match="Invalid review type"):
            parse_callback_data(f"approve_{bid_id}_fin")

    @pytest.mark.unit
    def test_parse_case_sensitive_action(self):
        """RED: Actions are case-sensitive - uppercase should fail."""
        bid_id = str(uuid4())
        with pytest.raises(ValueError, match="Invalid action"):
            parse_callback_data(f"APPROVE_{bid_id}_tech")

    @pytest.mark.unit
    def test_parse_case_sensitive_review_type(self):
        """RED: Review types are case-sensitive - uppercase should fail."""
        bid_id = str(uuid4())
        with pytest.raises(ValueError, match="Invalid review type"):
            parse_callback_data(f"approve_{bid_id}_TECH")


# =============================================================================
# TESTS: Edge Cases
# =============================================================================

class TestCallbackParserEdgeCases:
    """Tests for edge cases in callback data parsing."""

    @pytest.mark.unit
    def test_parse_preserves_bid_id_with_hyphens(self):
        """RED: UUID bid_id with hyphens should be preserved."""
        bid_id = "550e8400-e29b-41d4-a716-446655440000"
        callback_data = f"approve_{bid_id}_tech"

        result = parse_callback_data(callback_data)

        assert result["bid_id"] == bid_id

    @pytest.mark.unit
    def test_parse_short_uuid(self):
        """RED: Short UUID format should work."""
        bid_id = "abc123"
        callback_data = f"approve_{bid_id}_comm"

        result = parse_callback_data(callback_data)

        assert result["bid_id"] == bid_id

    @pytest.mark.unit
    def test_all_review_types_mapped_correctly(self):
        """RED: All review type abbreviations map to correct full names."""
        bid_id = str(uuid4())

        tech = parse_callback_data(f"approve_{bid_id}_tech")
        assert tech["review_type"] == "TECHNICAL"

        comm = parse_callback_data(f"approve_{bid_id}_comm")
        assert comm["review_type"] == "COMMERCIAL"

        mgmt = parse_callback_data(f"approve_{bid_id}_mgmt")
        assert mgmt["review_type"] == "MANAGEMENT"

    @pytest.mark.unit
    def test_all_decisions_mapped_correctly(self):
        """RED: All actions map to correct decisions."""
        bid_id = str(uuid4())

        approve = parse_callback_data(f"approve_{bid_id}_tech")
        assert approve["decision"] == "APPROVED"

        revision = parse_callback_data(f"revision_{bid_id}_tech")
        assert revision["decision"] == "REVISION_REQUESTED"

        reject = parse_callback_data(f"reject_{bid_id}_tech")
        assert reject["decision"] == "REJECTED"

    @pytest.mark.unit
    def test_needs_reason_only_for_non_approvals(self):
        """RED: needs_reason should be True only for revision/reject."""
        bid_id = str(uuid4())

        approve = parse_callback_data(f"approve_{bid_id}_tech")
        assert approve["needs_reason"] is False

        revision = parse_callback_data(f"revision_{bid_id}_tech")
        assert revision["needs_reason"] is True

        reject = parse_callback_data(f"reject_{bid_id}_tech")
        assert reject["needs_reason"] is True
