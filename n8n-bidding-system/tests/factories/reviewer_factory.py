"""
Reviewer Test Data Factory

Generates test reviewer data with realistic values.
"""

from uuid import uuid4
from typing import Any, Literal
import random


class ReviewerFactory:
    """
    Factory for generating test reviewer data.

    Usage:
        factory = ReviewerFactory()
        reviewer = factory.create_technical()
        reviewer = factory.create_commercial()
        reviewer = factory.create_management()
        reviewer = factory.create(can_review_technical=True, can_review_commercial=True)
    """

    TECH_ROLES = [
        "Technical Lead",
        "Senior Engineer",
        "Solutions Architect",
        "Technical Director",
        "Engineering Manager"
    ]

    COMM_ROLES = [
        "Finance Manager",
        "Commercial Director",
        "Finance Controller",
        "Business Analyst",
        "Pricing Manager"
    ]

    MGMT_ROLES = [
        "Executive Director",
        "Managing Director",
        "CEO",
        "COO",
        "VP Operations"
    ]

    DEPARTMENTS = {
        "technical": ["Engineering", "IT", "R&D", "Technology"],
        "commercial": ["Finance", "Commercial", "Pricing", "Business Development"],
        "management": ["Executive", "Management", "Operations", "Board"]
    }

    def __init__(self, prefix: str = "TDD"):
        self.prefix = prefix
        self._counter = 0
        self._chat_id_base = 100000000

    def _next_id(self) -> str:
        """Generate unique identifier suffix."""
        self._counter += 1
        return f"{self.prefix}-{uuid4().hex[:6]}-{self._counter}"

    def _next_chat_id(self) -> int:
        """Generate unique Telegram chat ID."""
        self._chat_id_base += random.randint(1, 1000)
        return self._chat_id_base

    def create(
        self,
        reviewer_type: Literal["technical", "commercial", "management", "mixed"] = "technical",
        **overrides
    ) -> dict[str, Any]:
        """
        Create a reviewer data dictionary.

        Args:
            reviewer_type: Type of reviewer to create
            **overrides: Override any default field

        Returns:
            dict with reviewer data
        """
        unique_id = self._next_id()
        chat_id = self._next_chat_id()

        # Set permissions based on type
        permissions = {
            "technical": {"can_review_technical": True, "can_review_commercial": False, "can_approve_management": False},
            "commercial": {"can_review_technical": False, "can_review_commercial": True, "can_approve_management": False},
            "management": {"can_review_technical": False, "can_review_commercial": False, "can_approve_management": True},
            "mixed": {"can_review_technical": True, "can_review_commercial": True, "can_approve_management": False}
        }

        # Select role and department based on type
        if reviewer_type == "technical":
            role = random.choice(self.TECH_ROLES)
            department = random.choice(self.DEPARTMENTS["technical"])
        elif reviewer_type == "commercial":
            role = random.choice(self.COMM_ROLES)
            department = random.choice(self.DEPARTMENTS["commercial"])
        elif reviewer_type == "management":
            role = random.choice(self.MGMT_ROLES)
            department = random.choice(self.DEPARTMENTS["management"])
        else:  # mixed
            role = "Senior Analyst"
            department = "Operations"

        defaults = {
            "telegram_chat_id": chat_id,
            "telegram_username": f"reviewer_{unique_id}".lower().replace("-", "_"),
            "name": f"{reviewer_type.title()} Reviewer {self._counter}",
            "email": f"reviewer-{unique_id.lower()}@test.com",
            "role": role,
            "department": department,
            "is_active": True,
            **permissions[reviewer_type]
        }

        return {**defaults, **overrides}

    def create_technical(self, **overrides) -> dict[str, Any]:
        """Create a technical reviewer."""
        return self.create(reviewer_type="technical", **overrides)

    def create_commercial(self, **overrides) -> dict[str, Any]:
        """Create a commercial reviewer."""
        return self.create(reviewer_type="commercial", **overrides)

    def create_management(self, **overrides) -> dict[str, Any]:
        """Create a management approver."""
        return self.create(reviewer_type="management", **overrides)

    def create_mixed(self, **overrides) -> dict[str, Any]:
        """Create a reviewer who can do both tech and commercial reviews."""
        return self.create(reviewer_type="mixed", **overrides)

    def create_inactive(self, reviewer_type: str = "technical", **overrides) -> dict[str, Any]:
        """Create an inactive reviewer."""
        return self.create(reviewer_type=reviewer_type, is_active=False, **overrides)

    def create_full_team(self) -> dict[str, dict[str, Any]]:
        """
        Create a complete review team with one of each type.

        Returns:
            dict with 'technical', 'commercial', 'management' reviewers
        """
        return {
            "technical": self.create_technical(),
            "commercial": self.create_commercial(),
            "management": self.create_management()
        }

    def create_multiple_technical(self, count: int = 3) -> list[dict[str, Any]]:
        """Create multiple technical reviewers."""
        return [self.create_technical() for _ in range(count)]

    def create_multiple_commercial(self, count: int = 2) -> list[dict[str, Any]]:
        """Create multiple commercial reviewers."""
        return [self.create_commercial() for _ in range(count)]

    def create_telegram_callback(
        self,
        reviewer: dict[str, Any],
        action: Literal["approve", "revision", "reject"],
        bid_id: str,
        review_type: Literal["tech", "comm", "mgmt"]
    ) -> dict[str, Any]:
        """
        Create a Telegram callback query payload for a reviewer action.

        Args:
            reviewer: Reviewer data dict
            action: The action (approve/revision/reject)
            bid_id: The bid ID
            review_type: Abbreviated review type

        Returns:
            Telegram callback_query update payload
        """
        return {
            "update_id": random.randint(100000000, 999999999),
            "callback_query": {
                "id": f"callback_{uuid4().hex[:12]}",
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "is_bot": False,
                    "first_name": reviewer["name"].split()[0],
                    "last_name": reviewer["name"].split()[-1] if " " in reviewer["name"] else "",
                    "username": reviewer["telegram_username"]
                },
                "message": {
                    "message_id": random.randint(1, 10000),
                    "chat": {
                        "id": reviewer["telegram_chat_id"],
                        "type": "private"
                    }
                },
                "chat_instance": str(random.randint(100000000, 999999999)),
                "data": f"{action}|{bid_id}|{review_type}"
            }
        }

    def create_telegram_message(
        self,
        reviewer: dict[str, Any],
        text: str,
        reply_to_message_id: int = None
    ) -> dict[str, Any]:
        """
        Create a Telegram text message payload from a reviewer.

        Args:
            reviewer: Reviewer data dict
            text: Message text
            reply_to_message_id: Optional message being replied to

        Returns:
            Telegram message update payload
        """
        import time

        message = {
            "update_id": random.randint(100000000, 999999999),
            "message": {
                "message_id": random.randint(1, 10000),
                "from": {
                    "id": reviewer["telegram_chat_id"],
                    "is_bot": False,
                    "first_name": reviewer["name"].split()[0],
                    "username": reviewer["telegram_username"]
                },
                "chat": {
                    "id": reviewer["telegram_chat_id"],
                    "type": "private"
                },
                "date": int(time.time()),
                "text": text
            }
        }

        if reply_to_message_id:
            message["message"]["reply_to_message"] = {
                "message_id": reply_to_message_id
            }

        return message


# Singleton instance for convenience
reviewer_factory = ReviewerFactory()
