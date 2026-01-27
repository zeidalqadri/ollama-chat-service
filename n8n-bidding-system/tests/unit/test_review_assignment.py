"""
Unit Tests: Review Assignment Logic

TDD tests for reviewer assignment rules.
Tests the logic that selects appropriate reviewers based on permissions.

RED: Write failing tests first
GREEN: These tests document expected assignment behavior
"""

import pytest
from typing import Any
from uuid import uuid4


# =============================================================================
# REVIEWER ASSIGNMENT LOGIC
# =============================================================================

def select_reviewer(
    reviewers: list[dict[str, Any]],
    review_type: str
) -> dict[str, Any] | None:
    """
    Select an appropriate reviewer for a review type.

    Args:
        reviewers: List of reviewer records from database
        review_type: TECHNICAL, COMMERCIAL, or MANAGEMENT

    Returns:
        Selected reviewer or None if no eligible reviewer found
    """
    permission_field = {
        "TECHNICAL": "can_review_technical",
        "COMMERCIAL": "can_review_commercial",
        "MANAGEMENT": "can_approve_management"
    }.get(review_type)

    if not permission_field:
        return None

    eligible = [
        r for r in reviewers
        if r.get("is_active", True) and r.get(permission_field, False)
    ]

    if not eligible:
        return None

    # Select first eligible (could be enhanced with load balancing)
    return eligible[0]


def get_eligible_reviewers(
    reviewers: list[dict[str, Any]],
    review_type: str
) -> list[dict[str, Any]]:
    """Get all eligible reviewers for a review type."""
    permission_field = {
        "TECHNICAL": "can_review_technical",
        "COMMERCIAL": "can_review_commercial",
        "MANAGEMENT": "can_approve_management"
    }.get(review_type)

    if not permission_field:
        return []

    return [
        r for r in reviewers
        if r.get("is_active", True) and r.get(permission_field, False)
    ]


def reviewer_can_review(reviewer: dict[str, Any], review_type: str) -> bool:
    """Check if a specific reviewer can handle a review type."""
    if not reviewer.get("is_active", True):
        return False

    permission_map = {
        "TECHNICAL": "can_review_technical",
        "COMMERCIAL": "can_review_commercial",
        "MANAGEMENT": "can_approve_management"
    }

    permission_field = permission_map.get(review_type)
    if not permission_field:
        return False

    return reviewer.get(permission_field, False)


def validate_reviewer_assignment(
    reviewer: dict[str, Any],
    review_type: str,
    bid_id: str
) -> tuple[bool, str]:
    """
    Validate a reviewer assignment is correct.

    Returns:
        (is_valid, error_message)
    """
    if not reviewer:
        return False, "No reviewer provided"

    if not reviewer.get("id"):
        return False, "Reviewer has no ID"

    if not reviewer.get("is_active", True):
        return False, f"Reviewer {reviewer.get('name')} is inactive"

    if not reviewer_can_review(reviewer, review_type):
        return False, f"Reviewer {reviewer.get('name')} cannot review {review_type}"

    return True, ""


# =============================================================================
# TEST DATA
# =============================================================================

@pytest.fixture
def tech_reviewer():
    """Technical reviewer."""
    return {
        "id": str(uuid4()),
        "name": "Alice Technical",
        "telegram_chat_id": 111111111,
        "can_review_technical": True,
        "can_review_commercial": False,
        "can_approve_management": False,
        "is_active": True
    }


@pytest.fixture
def comm_reviewer():
    """Commercial reviewer."""
    return {
        "id": str(uuid4()),
        "name": "Bob Commercial",
        "telegram_chat_id": 222222222,
        "can_review_technical": False,
        "can_review_commercial": True,
        "can_approve_management": False,
        "is_active": True
    }


@pytest.fixture
def mgmt_approver():
    """Management approver."""
    return {
        "id": str(uuid4()),
        "name": "Carol Management",
        "telegram_chat_id": 333333333,
        "can_review_technical": False,
        "can_review_commercial": False,
        "can_approve_management": True,
        "is_active": True
    }


@pytest.fixture
def mixed_reviewer():
    """Reviewer who can do both tech and commercial."""
    return {
        "id": str(uuid4()),
        "name": "Dave Mixed",
        "telegram_chat_id": 444444444,
        "can_review_technical": True,
        "can_review_commercial": True,
        "can_approve_management": False,
        "is_active": True
    }


@pytest.fixture
def inactive_reviewer():
    """Inactive reviewer."""
    return {
        "id": str(uuid4()),
        "name": "Eve Inactive",
        "telegram_chat_id": 555555555,
        "can_review_technical": True,
        "can_review_commercial": True,
        "can_approve_management": True,
        "is_active": False
    }


@pytest.fixture
def all_reviewers(tech_reviewer, comm_reviewer, mgmt_approver, mixed_reviewer, inactive_reviewer):
    """All reviewer types."""
    return [tech_reviewer, comm_reviewer, mgmt_approver, mixed_reviewer, inactive_reviewer]


# =============================================================================
# TESTS: Reviewer Selection
# =============================================================================

class TestReviewerSelection:
    """Tests for reviewer selection logic."""

    @pytest.mark.unit
    def test_select_technical_reviewer(self, all_reviewers, tech_reviewer):
        """RED: Select reviewer with can_review_technical=True."""
        result = select_reviewer(all_reviewers, "TECHNICAL")

        assert result is not None
        assert result["can_review_technical"] is True

    @pytest.mark.unit
    def test_select_commercial_reviewer(self, all_reviewers, comm_reviewer):
        """RED: Select reviewer with can_review_commercial=True."""
        result = select_reviewer(all_reviewers, "COMMERCIAL")

        assert result is not None
        assert result["can_review_commercial"] is True

    @pytest.mark.unit
    def test_select_management_approver(self, all_reviewers, mgmt_approver):
        """RED: Select reviewer with can_approve_management=True."""
        result = select_reviewer(all_reviewers, "MANAGEMENT")

        assert result is not None
        assert result["can_approve_management"] is True

    @pytest.mark.unit
    def test_select_returns_none_when_no_eligible(self):
        """RED: Returns None when no eligible reviewers."""
        reviewers = [
            {
                "id": str(uuid4()),
                "name": "Only Commercial",
                "can_review_technical": False,
                "can_review_commercial": True,
                "can_approve_management": False,
                "is_active": True
            }
        ]

        result = select_reviewer(reviewers, "TECHNICAL")
        assert result is None

    @pytest.mark.unit
    def test_select_skips_inactive_reviewers(self, inactive_reviewer):
        """RED: Inactive reviewers are not selected."""
        reviewers = [inactive_reviewer]

        result = select_reviewer(reviewers, "TECHNICAL")
        assert result is None

    @pytest.mark.unit
    def test_select_invalid_review_type_returns_none(self, all_reviewers):
        """RED: Invalid review type returns None."""
        result = select_reviewer(all_reviewers, "INVALID")
        assert result is None


# =============================================================================
# TESTS: Eligible Reviewers
# =============================================================================

class TestEligibleReviewers:
    """Tests for getting all eligible reviewers."""

    @pytest.mark.unit
    def test_get_all_technical_reviewers(self, all_reviewers):
        """RED: Get all reviewers who can do technical reviews."""
        eligible = get_eligible_reviewers(all_reviewers, "TECHNICAL")

        assert len(eligible) == 2  # tech_reviewer and mixed_reviewer
        assert all(r["can_review_technical"] for r in eligible)

    @pytest.mark.unit
    def test_get_all_commercial_reviewers(self, all_reviewers):
        """RED: Get all reviewers who can do commercial reviews."""
        eligible = get_eligible_reviewers(all_reviewers, "COMMERCIAL")

        assert len(eligible) == 2  # comm_reviewer and mixed_reviewer
        assert all(r["can_review_commercial"] for r in eligible)

    @pytest.mark.unit
    def test_get_all_management_approvers(self, all_reviewers):
        """RED: Get all reviewers who can approve management."""
        eligible = get_eligible_reviewers(all_reviewers, "MANAGEMENT")

        assert len(eligible) == 1  # only mgmt_approver
        assert all(r["can_approve_management"] for r in eligible)

    @pytest.mark.unit
    def test_eligible_excludes_inactive(self, all_reviewers, inactive_reviewer):
        """RED: Inactive reviewers excluded even with permissions."""
        # Inactive reviewer has all permissions but shouldn't be eligible
        eligible = get_eligible_reviewers(all_reviewers, "TECHNICAL")

        assert inactive_reviewer not in eligible

    @pytest.mark.unit
    def test_empty_list_when_none_eligible(self):
        """RED: Empty list when no reviewers are eligible."""
        reviewers = []
        eligible = get_eligible_reviewers(reviewers, "TECHNICAL")

        assert eligible == []


# =============================================================================
# TESTS: Permission Checking
# =============================================================================

class TestReviewerPermissions:
    """Tests for individual permission checking."""

    @pytest.mark.unit
    def test_tech_reviewer_can_review_technical(self, tech_reviewer):
        """RED: Technical reviewer can review technical."""
        assert reviewer_can_review(tech_reviewer, "TECHNICAL") is True

    @pytest.mark.unit
    def test_tech_reviewer_cannot_review_commercial(self, tech_reviewer):
        """RED: Technical reviewer cannot review commercial."""
        assert reviewer_can_review(tech_reviewer, "COMMERCIAL") is False

    @pytest.mark.unit
    def test_tech_reviewer_cannot_approve_management(self, tech_reviewer):
        """RED: Technical reviewer cannot approve management."""
        assert reviewer_can_review(tech_reviewer, "MANAGEMENT") is False

    @pytest.mark.unit
    def test_mixed_reviewer_can_review_both(self, mixed_reviewer):
        """RED: Mixed reviewer can do tech and commercial."""
        assert reviewer_can_review(mixed_reviewer, "TECHNICAL") is True
        assert reviewer_can_review(mixed_reviewer, "COMMERCIAL") is True
        assert reviewer_can_review(mixed_reviewer, "MANAGEMENT") is False

    @pytest.mark.unit
    def test_inactive_reviewer_cannot_review_anything(self, inactive_reviewer):
        """RED: Inactive reviewer cannot review anything."""
        assert reviewer_can_review(inactive_reviewer, "TECHNICAL") is False
        assert reviewer_can_review(inactive_reviewer, "COMMERCIAL") is False
        assert reviewer_can_review(inactive_reviewer, "MANAGEMENT") is False


# =============================================================================
# TESTS: Assignment Validation
# =============================================================================

class TestAssignmentValidation:
    """Tests for assignment validation."""

    @pytest.mark.unit
    def test_valid_technical_assignment(self, tech_reviewer):
        """RED: Valid technical reviewer assignment."""
        is_valid, error = validate_reviewer_assignment(
            tech_reviewer, "TECHNICAL", str(uuid4())
        )

        assert is_valid is True
        assert error == ""

    @pytest.mark.unit
    def test_invalid_assignment_wrong_type(self, tech_reviewer):
        """RED: Technical reviewer cannot be assigned commercial."""
        is_valid, error = validate_reviewer_assignment(
            tech_reviewer, "COMMERCIAL", str(uuid4())
        )

        assert is_valid is False
        assert "cannot review COMMERCIAL" in error

    @pytest.mark.unit
    def test_invalid_assignment_inactive(self, inactive_reviewer):
        """RED: Inactive reviewer assignment is invalid."""
        is_valid, error = validate_reviewer_assignment(
            inactive_reviewer, "TECHNICAL", str(uuid4())
        )

        assert is_valid is False
        assert "inactive" in error.lower()

    @pytest.mark.unit
    def test_invalid_assignment_none_reviewer(self):
        """RED: None reviewer is invalid."""
        is_valid, error = validate_reviewer_assignment(
            None, "TECHNICAL", str(uuid4())
        )

        assert is_valid is False
        assert "No reviewer provided" in error

    @pytest.mark.unit
    def test_invalid_assignment_no_id(self, tech_reviewer):
        """RED: Reviewer without ID is invalid."""
        reviewer_no_id = {**tech_reviewer}
        del reviewer_no_id["id"]

        is_valid, error = validate_reviewer_assignment(
            reviewer_no_id, "TECHNICAL", str(uuid4())
        )

        assert is_valid is False
        assert "no ID" in error


# =============================================================================
# TESTS: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in reviewer assignment."""

    @pytest.mark.unit
    def test_reviewer_with_missing_permission_field_defaults_false(self):
        """RED: Missing permission field defaults to False."""
        reviewer = {
            "id": str(uuid4()),
            "name": "Minimal Reviewer",
            "is_active": True
            # No permission fields
        }

        assert reviewer_can_review(reviewer, "TECHNICAL") is False
        assert reviewer_can_review(reviewer, "COMMERCIAL") is False
        assert reviewer_can_review(reviewer, "MANAGEMENT") is False

    @pytest.mark.unit
    def test_reviewer_with_missing_is_active_defaults_true(self):
        """RED: Missing is_active field defaults to True."""
        reviewer = {
            "id": str(uuid4()),
            "name": "Reviewer",
            "can_review_technical": True
            # No is_active field
        }

        assert reviewer_can_review(reviewer, "TECHNICAL") is True

    @pytest.mark.unit
    def test_select_from_single_eligible_reviewer(self, tech_reviewer):
        """RED: Selection works with single eligible reviewer."""
        result = select_reviewer([tech_reviewer], "TECHNICAL")

        assert result == tech_reviewer

    @pytest.mark.unit
    def test_get_eligible_returns_copy_not_reference(self, all_reviewers):
        """RED: Eligible list is independent of source list."""
        eligible = get_eligible_reviewers(all_reviewers, "TECHNICAL")
        original_count = len(eligible)

        # Modify the result
        eligible.append({"name": "New Reviewer"})

        # Get again - should be original count
        eligible_again = get_eligible_reviewers(all_reviewers, "TECHNICAL")
        assert len(eligible_again) == original_count
