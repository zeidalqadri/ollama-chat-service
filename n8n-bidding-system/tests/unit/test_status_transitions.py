"""
Unit Tests: Bid Status Transitions

TDD tests for valid bid status state machine transitions.
The bid_status ENUM defines a specific flow that workflows must follow.

RED: Write failing tests first
GREEN: These tests document expected status transitions
"""

import pytest
from typing import Literal


# =============================================================================
# STATUS TRANSITION LOGIC
# =============================================================================

# All valid bid statuses from the PostgreSQL ENUM
BidStatus = Literal[
    "DRAFT",
    "SUBMITTED",
    "NEEDS_INFO",
    "TECHNICAL_REVIEW",
    "TECH_REJECTED",
    "COMMERCIAL_REVIEW",
    "COMM_REJECTED",
    "MGMT_APPROVAL",
    "APPROVED_TO_SUBMIT",
    "SUBMITTED_TO_CLIENT",
    "WON",
    "LOST",
    "NO_DECISION",
    "LESSONS_LEARNED",
    "ARCHIVED"
]

# Valid transitions: from_status -> [allowed_to_statuses]
VALID_TRANSITIONS: dict[str, list[str]] = {
    "DRAFT": ["SUBMITTED"],
    "SUBMITTED": ["NEEDS_INFO", "TECHNICAL_REVIEW"],
    "NEEDS_INFO": ["SUBMITTED", "ARCHIVED"],
    "TECHNICAL_REVIEW": ["TECH_REJECTED", "COMMERCIAL_REVIEW"],
    "TECH_REJECTED": ["ARCHIVED", "LESSONS_LEARNED"],
    "COMMERCIAL_REVIEW": ["COMM_REJECTED", "MGMT_APPROVAL"],
    "COMM_REJECTED": ["ARCHIVED", "LESSONS_LEARNED"],
    "MGMT_APPROVAL": ["APPROVED_TO_SUBMIT", "COMM_REJECTED"],
    "APPROVED_TO_SUBMIT": ["SUBMITTED_TO_CLIENT"],
    "SUBMITTED_TO_CLIENT": ["WON", "LOST", "NO_DECISION"],
    "WON": ["LESSONS_LEARNED"],
    "LOST": ["LESSONS_LEARNED"],
    "NO_DECISION": ["LESSONS_LEARNED", "ARCHIVED"],
    "LESSONS_LEARNED": ["ARCHIVED"],
    "ARCHIVED": []  # Terminal state
}

# Review stage mapping
REVIEW_STAGE_STATUSES = {
    "TECHNICAL": "TECHNICAL_REVIEW",
    "COMMERCIAL": "COMMERCIAL_REVIEW",
    "MANAGEMENT": "MGMT_APPROVAL"
}

# Rejection mapping
REJECTION_STATUSES = {
    "TECHNICAL": "TECH_REJECTED",
    "COMMERCIAL": "COMM_REJECTED",
    "MANAGEMENT": "COMM_REJECTED"  # Management rejection goes back to commercial
}


def is_valid_transition(from_status: str, to_status: str) -> bool:
    """Check if a status transition is valid."""
    if from_status not in VALID_TRANSITIONS:
        return False
    return to_status in VALID_TRANSITIONS[from_status]


def get_next_review_status(current_review_type: str) -> str | None:
    """Get the next status after a review approval."""
    next_stage = {
        "TECHNICAL": "COMMERCIAL_REVIEW",
        "COMMERCIAL": "MGMT_APPROVAL",
        "MANAGEMENT": "APPROVED_TO_SUBMIT"
    }
    return next_stage.get(current_review_type)


def get_rejection_status(review_type: str) -> str:
    """Get the status when a review is rejected."""
    return REJECTION_STATUSES.get(review_type, "ARCHIVED")


def can_enter_review(current_status: str, review_type: str) -> bool:
    """Check if a bid can enter a specific review stage."""
    if review_type == "TECHNICAL":
        return current_status in ["SUBMITTED"]
    elif review_type == "COMMERCIAL":
        return current_status in ["TECHNICAL_REVIEW"]
    elif review_type == "MANAGEMENT":
        return current_status in ["COMMERCIAL_REVIEW"]
    return False


# =============================================================================
# TESTS: Valid Transitions
# =============================================================================

class TestValidStatusTransitions:
    """Tests for valid status transitions."""

    @pytest.mark.unit
    def test_draft_to_submitted(self):
        """RED: DRAFT -> SUBMITTED is valid."""
        assert is_valid_transition("DRAFT", "SUBMITTED") is True

    @pytest.mark.unit
    def test_submitted_to_technical_review(self):
        """RED: SUBMITTED -> TECHNICAL_REVIEW is valid."""
        assert is_valid_transition("SUBMITTED", "TECHNICAL_REVIEW") is True

    @pytest.mark.unit
    def test_submitted_to_needs_info(self):
        """RED: SUBMITTED -> NEEDS_INFO is valid (low completeness)."""
        assert is_valid_transition("SUBMITTED", "NEEDS_INFO") is True

    @pytest.mark.unit
    def test_technical_review_to_commercial_review(self):
        """RED: TECHNICAL_REVIEW -> COMMERCIAL_REVIEW is valid (approval)."""
        assert is_valid_transition("TECHNICAL_REVIEW", "COMMERCIAL_REVIEW") is True

    @pytest.mark.unit
    def test_technical_review_to_tech_rejected(self):
        """RED: TECHNICAL_REVIEW -> TECH_REJECTED is valid (rejection)."""
        assert is_valid_transition("TECHNICAL_REVIEW", "TECH_REJECTED") is True

    @pytest.mark.unit
    def test_commercial_review_to_mgmt_approval(self):
        """RED: COMMERCIAL_REVIEW -> MGMT_APPROVAL is valid (approval)."""
        assert is_valid_transition("COMMERCIAL_REVIEW", "MGMT_APPROVAL") is True

    @pytest.mark.unit
    def test_commercial_review_to_comm_rejected(self):
        """RED: COMMERCIAL_REVIEW -> COMM_REJECTED is valid (rejection)."""
        assert is_valid_transition("COMMERCIAL_REVIEW", "COMM_REJECTED") is True

    @pytest.mark.unit
    def test_mgmt_approval_to_approved_to_submit(self):
        """RED: MGMT_APPROVAL -> APPROVED_TO_SUBMIT is valid."""
        assert is_valid_transition("MGMT_APPROVAL", "APPROVED_TO_SUBMIT") is True

    @pytest.mark.unit
    def test_approved_to_submit_to_submitted_to_client(self):
        """RED: APPROVED_TO_SUBMIT -> SUBMITTED_TO_CLIENT is valid."""
        assert is_valid_transition("APPROVED_TO_SUBMIT", "SUBMITTED_TO_CLIENT") is True

    @pytest.mark.unit
    def test_submitted_to_client_to_won(self):
        """RED: SUBMITTED_TO_CLIENT -> WON is valid."""
        assert is_valid_transition("SUBMITTED_TO_CLIENT", "WON") is True

    @pytest.mark.unit
    def test_submitted_to_client_to_lost(self):
        """RED: SUBMITTED_TO_CLIENT -> LOST is valid."""
        assert is_valid_transition("SUBMITTED_TO_CLIENT", "LOST") is True

    @pytest.mark.unit
    def test_submitted_to_client_to_no_decision(self):
        """RED: SUBMITTED_TO_CLIENT -> NO_DECISION is valid."""
        assert is_valid_transition("SUBMITTED_TO_CLIENT", "NO_DECISION") is True

    @pytest.mark.unit
    def test_won_to_lessons_learned(self):
        """RED: WON -> LESSONS_LEARNED is valid."""
        assert is_valid_transition("WON", "LESSONS_LEARNED") is True

    @pytest.mark.unit
    def test_lost_to_lessons_learned(self):
        """RED: LOST -> LESSONS_LEARNED is valid."""
        assert is_valid_transition("LOST", "LESSONS_LEARNED") is True

    @pytest.mark.unit
    def test_lessons_learned_to_archived(self):
        """RED: LESSONS_LEARNED -> ARCHIVED is valid."""
        assert is_valid_transition("LESSONS_LEARNED", "ARCHIVED") is True


# =============================================================================
# TESTS: Invalid Transitions
# =============================================================================

class TestInvalidStatusTransitions:
    """Tests for invalid status transitions."""

    @pytest.mark.unit
    def test_draft_to_technical_review_invalid(self):
        """RED: DRAFT -> TECHNICAL_REVIEW is invalid (must submit first)."""
        assert is_valid_transition("DRAFT", "TECHNICAL_REVIEW") is False

    @pytest.mark.unit
    def test_submitted_to_mgmt_approval_invalid(self):
        """RED: SUBMITTED -> MGMT_APPROVAL is invalid (skip reviews)."""
        assert is_valid_transition("SUBMITTED", "MGMT_APPROVAL") is False

    @pytest.mark.unit
    def test_technical_review_to_mgmt_approval_invalid(self):
        """RED: TECHNICAL_REVIEW -> MGMT_APPROVAL is invalid (skip commercial)."""
        assert is_valid_transition("TECHNICAL_REVIEW", "MGMT_APPROVAL") is False

    @pytest.mark.unit
    def test_archived_has_no_valid_transitions(self):
        """RED: ARCHIVED is terminal - no transitions allowed."""
        for status in VALID_TRANSITIONS.keys():
            assert is_valid_transition("ARCHIVED", status) is False

    @pytest.mark.unit
    def test_backward_transition_invalid(self):
        """RED: COMMERCIAL_REVIEW -> TECHNICAL_REVIEW is invalid (no going back)."""
        assert is_valid_transition("COMMERCIAL_REVIEW", "TECHNICAL_REVIEW") is False

    @pytest.mark.unit
    def test_won_to_submitted_invalid(self):
        """RED: WON -> SUBMITTED is invalid."""
        assert is_valid_transition("WON", "SUBMITTED") is False

    @pytest.mark.unit
    def test_approved_to_submit_to_technical_review_invalid(self):
        """RED: APPROVED_TO_SUBMIT -> TECHNICAL_REVIEW is invalid."""
        assert is_valid_transition("APPROVED_TO_SUBMIT", "TECHNICAL_REVIEW") is False


# =============================================================================
# TESTS: Review Flow
# =============================================================================

class TestReviewFlow:
    """Tests for review stage progression."""

    @pytest.mark.unit
    def test_next_status_after_technical_approval(self):
        """RED: After technical approval, next is COMMERCIAL_REVIEW."""
        assert get_next_review_status("TECHNICAL") == "COMMERCIAL_REVIEW"

    @pytest.mark.unit
    def test_next_status_after_commercial_approval(self):
        """RED: After commercial approval, next is MGMT_APPROVAL."""
        assert get_next_review_status("COMMERCIAL") == "MGMT_APPROVAL"

    @pytest.mark.unit
    def test_next_status_after_management_approval(self):
        """RED: After management approval, next is APPROVED_TO_SUBMIT."""
        assert get_next_review_status("MANAGEMENT") == "APPROVED_TO_SUBMIT"

    @pytest.mark.unit
    def test_technical_rejection_status(self):
        """RED: Technical rejection sets TECH_REJECTED."""
        assert get_rejection_status("TECHNICAL") == "TECH_REJECTED"

    @pytest.mark.unit
    def test_commercial_rejection_status(self):
        """RED: Commercial rejection sets COMM_REJECTED."""
        assert get_rejection_status("COMMERCIAL") == "COMM_REJECTED"

    @pytest.mark.unit
    def test_management_rejection_returns_to_commercial(self):
        """RED: Management rejection goes back to COMM_REJECTED."""
        assert get_rejection_status("MANAGEMENT") == "COMM_REJECTED"


# =============================================================================
# TESTS: Review Entry Prerequisites
# =============================================================================

class TestReviewEntryPrerequisites:
    """Tests for review stage entry conditions."""

    @pytest.mark.unit
    def test_can_enter_technical_from_submitted(self):
        """RED: Can enter technical review from SUBMITTED."""
        assert can_enter_review("SUBMITTED", "TECHNICAL") is True

    @pytest.mark.unit
    def test_cannot_enter_technical_from_draft(self):
        """RED: Cannot enter technical review from DRAFT."""
        assert can_enter_review("DRAFT", "TECHNICAL") is False

    @pytest.mark.unit
    def test_can_enter_commercial_from_technical_review(self):
        """RED: Can enter commercial review from TECHNICAL_REVIEW."""
        assert can_enter_review("TECHNICAL_REVIEW", "COMMERCIAL") is True

    @pytest.mark.unit
    def test_cannot_enter_commercial_from_submitted(self):
        """RED: Cannot enter commercial review directly from SUBMITTED."""
        assert can_enter_review("SUBMITTED", "COMMERCIAL") is False

    @pytest.mark.unit
    def test_can_enter_management_from_commercial_review(self):
        """RED: Can enter management review from COMMERCIAL_REVIEW."""
        assert can_enter_review("COMMERCIAL_REVIEW", "MANAGEMENT") is True

    @pytest.mark.unit
    def test_cannot_enter_management_from_technical_review(self):
        """RED: Cannot skip commercial and enter management."""
        assert can_enter_review("TECHNICAL_REVIEW", "MANAGEMENT") is False


# =============================================================================
# TESTS: Complete Happy Path
# =============================================================================

class TestCompleteHappyPath:
    """Tests for complete approval flow."""

    @pytest.mark.unit
    def test_full_approval_path_is_valid(self):
        """RED: Verify entire happy path is valid transitions."""
        happy_path = [
            ("DRAFT", "SUBMITTED"),
            ("SUBMITTED", "TECHNICAL_REVIEW"),
            ("TECHNICAL_REVIEW", "COMMERCIAL_REVIEW"),
            ("COMMERCIAL_REVIEW", "MGMT_APPROVAL"),
            ("MGMT_APPROVAL", "APPROVED_TO_SUBMIT"),
            ("APPROVED_TO_SUBMIT", "SUBMITTED_TO_CLIENT"),
            ("SUBMITTED_TO_CLIENT", "WON"),
            ("WON", "LESSONS_LEARNED"),
            ("LESSONS_LEARNED", "ARCHIVED")
        ]

        for from_status, to_status in happy_path:
            assert is_valid_transition(from_status, to_status), \
                f"Expected {from_status} -> {to_status} to be valid"

    @pytest.mark.unit
    def test_rejection_and_archive_path(self):
        """RED: Verify rejection path to archive is valid."""
        rejection_path = [
            ("SUBMITTED", "TECHNICAL_REVIEW"),
            ("TECHNICAL_REVIEW", "TECH_REJECTED"),
            ("TECH_REJECTED", "LESSONS_LEARNED"),
            ("LESSONS_LEARNED", "ARCHIVED")
        ]

        for from_status, to_status in rejection_path:
            assert is_valid_transition(from_status, to_status), \
                f"Expected {from_status} -> {to_status} to be valid"

    @pytest.mark.unit
    def test_needs_info_recovery_path(self):
        """RED: Verify NEEDS_INFO can be resubmitted."""
        recovery_path = [
            ("SUBMITTED", "NEEDS_INFO"),
            ("NEEDS_INFO", "SUBMITTED"),
            ("SUBMITTED", "TECHNICAL_REVIEW")
        ]

        for from_status, to_status in recovery_path:
            assert is_valid_transition(from_status, to_status), \
                f"Expected {from_status} -> {to_status} to be valid"
