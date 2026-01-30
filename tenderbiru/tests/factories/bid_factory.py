"""
Bid Test Data Factory

Generates test bid data with realistic values.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Any
import random


class BidFactory:
    """
    Factory for generating test bid data.

    Usage:
        factory = BidFactory()
        bid = factory.create()  # Default bid
        bid = factory.create(title="Custom Title", estimated_value=500000)
        bid = factory.create_submitted()  # Bid with SUBMITTED status
        bid = factory.create_in_review()  # Bid in technical review
    """

    # Sample data pools
    CLIENT_NAMES = [
        "Petronas Technology Solutions",
        "Tenaga Nasional Berhad",
        "Malaysia Airlines Engineering",
        "Bank Negara Malaysia",
        "Axiata Group Berhad",
        "Sime Darby Property",
        "IHH Healthcare Berhad",
        "CIMB Group Holdings",
        "Maybank Asset Management",
        "Telekom Malaysia Berhad"
    ]

    PROJECT_TYPES = [
        "IT Infrastructure Upgrade",
        "Digital Transformation Initiative",
        "Cloud Migration Project",
        "Cybersecurity Enhancement",
        "ERP System Implementation",
        "Data Analytics Platform",
        "Mobile Application Development",
        "Network Infrastructure Overhaul",
        "Business Process Automation",
        "AI/ML Solution Deployment"
    ]

    TAGS = [
        "government", "private", "infrastructure", "software",
        "consulting", "maintenance", "implementation", "upgrade",
        "security", "cloud", "digital", "analytics"
    ]

    def __init__(self, prefix: str = "TEST"):
        self.prefix = prefix
        self._counter = 0

    def _next_id(self) -> str:
        """Generate unique identifier suffix."""
        self._counter += 1
        return f"{self.prefix}-{uuid4().hex[:8]}-{self._counter}"

    def create(self, **overrides) -> dict[str, Any]:
        """
        Create a bid data dictionary.

        Args:
            **overrides: Override any default field

        Returns:
            dict with bid data ready for database insert or API call
        """
        unique_id = self._next_id()
        deadline_days = random.randint(7, 30)

        defaults = {
            "title": f"{random.choice(self.PROJECT_TYPES)} - {unique_id}",
            "client_name": random.choice(self.CLIENT_NAMES),
            "client_contact": f"Contact Person {self._counter}",
            "client_email": f"contact{self._counter}@client.com",
            "submission_deadline": (
                datetime.now(timezone.utc) + timedelta(days=deadline_days)
            ).isoformat(),
            "estimated_value": random.randint(50000, 1000000),
            "currency": "MYR",
            "margin_percentage": round(random.uniform(10, 25), 2),
            "source": "TDD_FACTORY",
            "tags": random.sample(self.TAGS, k=random.randint(2, 4)),
            "notes": f"Auto-generated test bid {unique_id}"
        }

        return {**defaults, **overrides}

    def create_submitted(self, **overrides) -> dict[str, Any]:
        """Create a bid in SUBMITTED status."""
        bid = self.create(**overrides)
        bid["status"] = "SUBMITTED"
        return bid

    def create_analyzed(
        self,
        completeness: int = 80,
        win_prob: int = 70,
        risk: int = 30,
        **overrides
    ) -> dict[str, Any]:
        """Create a bid that has been analyzed by AI."""
        bid = self.create(**overrides)
        bid["status"] = "TECHNICAL_REVIEW"
        bid["completeness_score"] = completeness
        bid["win_probability_score"] = win_prob
        bid["risk_score"] = risk
        bid["ai_analysis_json"] = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "model": "qwen3-coder:30b",
            "scores": {
                "completeness": completeness,
                "win_probability": win_prob,
                "risk": risk
            }
        }
        return bid

    def create_in_technical_review(self, **overrides) -> dict[str, Any]:
        """Create a bid in technical review stage."""
        return self.create_analyzed(status="TECHNICAL_REVIEW", **overrides)

    def create_in_commercial_review(self, **overrides) -> dict[str, Any]:
        """Create a bid in commercial review stage."""
        return self.create_analyzed(status="COMMERCIAL_REVIEW", **overrides)

    def create_in_management_approval(self, **overrides) -> dict[str, Any]:
        """Create a bid awaiting management approval."""
        return self.create_analyzed(status="MGMT_APPROVAL", **overrides)

    def create_approved(self, **overrides) -> dict[str, Any]:
        """Create an approved bid ready for submission."""
        return self.create_analyzed(status="APPROVED_TO_SUBMIT", **overrides)

    def create_needs_info(self, **overrides) -> dict[str, Any]:
        """Create a bid that needs more information."""
        bid = self.create(**overrides)
        bid["status"] = "NEEDS_INFO"
        bid["completeness_score"] = random.randint(40, 69)
        bid["missing_sections"] = [
            "Executive Summary",
            "Risk Assessment",
            "Timeline Details"
        ]
        return bid

    def create_minimal(self) -> dict[str, Any]:
        """Create a bid with only required fields."""
        return {
            "title": f"Minimal Bid {self._next_id()}",
            "client_name": "Minimal Client",
            "submission_deadline": (
                datetime.now(timezone.utc) + timedelta(days=14)
            ).isoformat()
        }

    def create_invalid_deadline(self) -> dict[str, Any]:
        """Create a bid with past deadline (invalid)."""
        bid = self.create()
        bid["submission_deadline"] = (
            datetime.now(timezone.utc) - timedelta(days=1)
        ).isoformat()
        return bid

    def create_high_value(self, value: int = 5000000, **overrides) -> dict[str, Any]:
        """Create a high-value bid."""
        return self.create(
            estimated_value=value,
            priority="HIGH",
            tags=["high-value", "strategic"],
            **overrides
        )

    def create_urgent(self, days_to_deadline: int = 3, **overrides) -> dict[str, Any]:
        """Create an urgent bid with short deadline."""
        return self.create(
            submission_deadline=(
                datetime.now(timezone.utc) + timedelta(days=days_to_deadline)
            ).isoformat(),
            priority="CRITICAL",
            tags=["urgent"],
            **overrides
        )

    def create_batch(self, count: int, **overrides) -> list[dict[str, Any]]:
        """Create multiple bids."""
        return [self.create(**overrides) for _ in range(count)]


# Singleton instance for convenience
bid_factory = BidFactory()
