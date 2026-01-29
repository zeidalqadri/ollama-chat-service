"""
TenderBiru Workflow Test Configuration

Shared fixtures for unit, integration, and e2e tests.
Provides database connections, HTTP clients, mock servers, and test data.
"""

import os
import pytest
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone
from typing import Generator, Any
from uuid import uuid4

# =============================================================================
# CONFIGURATION
# =============================================================================

# VPS Configuration
VPS_HOST = os.getenv("TEST_VPS_HOST", "45.159.230.42")
VPS_N8N_PORT = os.getenv("TEST_N8N_PORT", "5678")
VPS_DB_PORT = os.getenv("TEST_DB_PORT", "5432")

# n8n Webhook Base URL - workflows use /webhook/bid/ prefix
N8N_WEBHOOK_URL = f"http://{VPS_HOST}:{VPS_N8N_PORT}/webhook/bid"
N8N_WEBHOOK_TEST_URL = f"http://{VPS_HOST}:{VPS_N8N_PORT}/webhook-test/bid"

# Harmony workflows use /webhook/harmony/ prefix
N8N_HARMONY_URL = f"http://{VPS_HOST}:{VPS_N8N_PORT}/webhook/harmony"

# Database DSN - use test database or main with rollback
TEST_DB_DSN = os.getenv(
    "TEST_DB_DSN",
    f"postgresql://alumist:alumist-2024@{VPS_HOST}:{VPS_DB_PORT}/tenderbiru"
)

# External Service URLs (for mocking)
TELEGRAM_API_BASE = "https://api.telegram.org"
OLLAMA_API_BASE = os.getenv("OLLAMA_URL", "http://localhost:11434")


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Session-scoped database connection.
    Used for reading data and verifying state changes.
    """
    conn = psycopg2.connect(TEST_DB_DSN, cursor_factory=RealDictCursor)
    yield conn
    conn.close()


@pytest.fixture
def db(db_connection) -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Function-scoped database fixture with transaction rollback.
    Each test gets a clean slate.
    """
    conn = db_connection

    # Ensure we're in a clean transaction state
    conn.rollback()

    cursor = conn.cursor()

    # Start a savepoint we can rollback to
    cursor.execute("SAVEPOINT test_savepoint")

    yield conn

    # Rollback to savepoint after test (handles both success and failure)
    try:
        cursor.execute("ROLLBACK TO SAVEPOINT test_savepoint")
    except Exception:
        conn.rollback()  # Full rollback if savepoint fails
    cursor.close()


@pytest.fixture
def db_cursor(db):
    """Cursor for executing queries."""
    cursor = db.cursor()
    yield cursor
    cursor.close()


# =============================================================================
# HTTP CLIENT FIXTURES
# =============================================================================

@pytest.fixture
def n8n_client() -> Generator[httpx.Client, None, None]:
    """
    HTTP client for calling n8n webhooks.
    Configured with appropriate timeout for workflow execution.
    """
    client = httpx.Client(
        base_url=N8N_WEBHOOK_URL,
        timeout=httpx.Timeout(30.0, connect=5.0),
        headers={"Content-Type": "application/json"}
    )
    yield client
    client.close()


@pytest.fixture
def n8n_test_client() -> Generator[httpx.Client, None, None]:
    """
    HTTP client for n8n test webhooks.
    Use this when testing workflows in test mode.
    """
    client = httpx.Client(
        base_url=N8N_WEBHOOK_TEST_URL,
        timeout=httpx.Timeout(30.0, connect=5.0),
        headers={"Content-Type": "application/json"}
    )
    yield client
    client.close()


@pytest.fixture
async def async_n8n_client():
    """Async HTTP client for concurrent tests."""
    async with httpx.AsyncClient(
        base_url=N8N_WEBHOOK_URL,
        timeout=httpx.Timeout(30.0, connect=5.0),
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client


@pytest.fixture
def harmony_client() -> Generator[httpx.Client, None, None]:
    """
    HTTP client for calling Harmony workflow webhooks.
    Harmony workflows use /webhook/harmony/ prefix.
    """
    client = httpx.Client(
        base_url=N8N_HARMONY_URL,
        timeout=httpx.Timeout(30.0, connect=5.0),
        headers={"Content-Type": "application/json"}
    )
    yield client
    client.close()


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_bid() -> dict[str, Any]:
    """
    Valid bid submission payload.
    Use this as a base and override specific fields as needed.
    """
    deadline = datetime.now(timezone.utc) + timedelta(days=14)
    return {
        "title": f"TEST-TDD-{uuid4().hex[:8]} Infrastructure Project",
        "client_name": "Test Corporation Pty Ltd",
        "client_contact": "John Doe",
        "client_email": "john@testcorp.com",
        "submission_deadline": deadline.isoformat(),
        "estimated_value": 150000.00,
        "currency": "MYR",
        "margin_percentage": 15.5,
        "source": "TDD_TEST",
        "tags": ["test", "tdd", "automated"],
        "notes": "Generated by TDD test suite"
    }


@pytest.fixture
def sample_bid_minimal() -> dict[str, Any]:
    """Minimal valid bid with only required fields."""
    deadline = datetime.now(timezone.utc) + timedelta(days=7)
    return {
        "title": f"TEST-MINIMAL-{uuid4().hex[:8]}",
        "client_name": "Minimal Test Client",
        "submission_deadline": deadline.isoformat()
    }


@pytest.fixture
def sample_bid_invalid_deadline() -> dict[str, Any]:
    """Bid with past deadline (should fail validation)."""
    deadline = datetime.now(timezone.utc) - timedelta(days=1)
    return {
        "title": f"TEST-INVALID-{uuid4().hex[:8]}",
        "client_name": "Past Deadline Client",
        "submission_deadline": deadline.isoformat()
    }


# Real Telegram chat ID for testing (Zeid's account - receives actual notifications)
REAL_TELEGRAM_CHAT_ID = 5426763403
REAL_TELEGRAM_USERNAME = "zaborz"


@pytest.fixture
def sample_reviewer_technical() -> dict[str, Any]:
    """Technical reviewer data using real Telegram ID."""
    return {
        "telegram_chat_id": REAL_TELEGRAM_CHAT_ID,
        "telegram_username": REAL_TELEGRAM_USERNAME,
        "name": "Tech Reviewer TDD",
        "email": f"tech-tdd-{uuid4().hex[:8]}@test.com",
        "role": "Technical Lead",
        "department": "Engineering",
        "can_review_technical": True,
        "can_review_commercial": False,
        "can_approve_management": False,
        "is_active": True
    }


@pytest.fixture
def sample_reviewer_commercial() -> dict[str, Any]:
    """Commercial reviewer data using real Telegram ID."""
    return {
        "telegram_chat_id": REAL_TELEGRAM_CHAT_ID,
        "telegram_username": REAL_TELEGRAM_USERNAME,
        "name": "Commercial Reviewer TDD",
        "email": f"comm-tdd-{uuid4().hex[:8]}@test.com",
        "role": "Finance Manager",
        "department": "Finance",
        "can_review_technical": False,
        "can_review_commercial": True,
        "can_approve_management": False,
        "is_active": True
    }


@pytest.fixture
def sample_reviewer_management() -> dict[str, Any]:
    """Management approver data using real Telegram ID."""
    return {
        "telegram_chat_id": REAL_TELEGRAM_CHAT_ID,
        "telegram_username": REAL_TELEGRAM_USERNAME,
        "name": "Management Approver TDD",
        "email": f"mgmt-tdd-{uuid4().hex[:8]}@test.com",
        "role": "Executive Director",
        "department": "Management",
        "can_review_technical": False,
        "can_review_commercial": False,
        "can_approve_management": True,
        "is_active": True
    }


# =============================================================================
# TELEGRAM CALLBACK FIXTURES
# =============================================================================

@pytest.fixture
def sample_callback_approve_tech() -> dict[str, Any]:
    """
    Telegram callback for technical approval.
    callback_data format: action|bid_id|review_type_abbrev
    """
    return {
        "update_id": 123456789,
        "callback_query": {
            "id": "callback_123",
            "from": {
                "id": 111111111,
                "is_bot": False,
                "first_name": "Tech",
                "last_name": "Reviewer",
                "username": "test_tech_reviewer"
            },
            "message": {
                "message_id": 100,
                "chat": {
                    "id": 111111111,
                    "type": "private"
                }
            },
            "chat_instance": "123456789",
            "data": "approve|BID_ID_PLACEHOLDER|tech"
        }
    }


@pytest.fixture
def sample_callback_revision_comm() -> dict[str, Any]:
    """Telegram callback for commercial revision request."""
    return {
        "update_id": 123456790,
        "callback_query": {
            "id": "callback_124",
            "from": {
                "id": 222222222,
                "is_bot": False,
                "first_name": "Comm",
                "last_name": "Reviewer",
                "username": "test_comm_reviewer"
            },
            "message": {
                "message_id": 101,
                "chat": {
                    "id": 222222222,
                    "type": "private"
                }
            },
            "chat_instance": "123456789",
            "data": "revision|BID_ID_PLACEHOLDER|comm"
        }
    }


@pytest.fixture
def sample_callback_reject_mgmt() -> dict[str, Any]:
    """Telegram callback for management rejection."""
    return {
        "update_id": 123456791,
        "callback_query": {
            "id": "callback_125",
            "from": {
                "id": 333333333,
                "is_bot": False,
                "first_name": "Mgmt",
                "last_name": "Approver",
                "username": "test_mgmt_approver"
            },
            "message": {
                "message_id": 102,
                "chat": {
                    "id": 333333333,
                    "type": "private"
                }
            },
            "chat_instance": "123456789",
            "data": "reject|BID_ID_PLACEHOLDER|mgmt"
        }
    }


@pytest.fixture
def sample_text_message_with_reason() -> dict[str, Any]:
    """
    Telegram text message (reason after revision/rejection).
    This simulates the user responding to a force_reply request.
    """
    return {
        "update_id": 123456792,
        "message": {
            "message_id": 103,
            "from": {
                "id": 222222222,
                "is_bot": False,
                "first_name": "Comm",
                "last_name": "Reviewer",
                "username": "test_comm_reviewer"
            },
            "chat": {
                "id": 222222222,
                "type": "private"
            },
            "date": int(datetime.now(timezone.utc).timestamp()),
            "text": "Budget allocation insufficient. Need 20% increase for contingencies.",
            "reply_to_message": {
                "message_id": 101
            }
        }
    }


# =============================================================================
# DATABASE HELPER FIXTURES
# =============================================================================

@pytest.fixture
def create_test_bid(db_cursor, sample_bid):
    """
    Factory fixture to create a test bid in the database.
    Returns the created bid's ID and reference number.
    """
    def _create_bid(**overrides) -> dict[str, Any]:
        bid_data = {**sample_bid, **overrides}
        deadline = bid_data.get("submission_deadline")
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))

        db_cursor.execute("""
            INSERT INTO bids (
                title, client_name, client_contact, client_email,
                submission_deadline, estimated_value, currency,
                margin_percentage, source, tags, notes, status
            ) VALUES (
                %(title)s, %(client_name)s, %(client_contact)s, %(client_email)s,
                %(deadline)s, %(estimated_value)s, %(currency)s,
                %(margin_percentage)s, %(source)s, %(tags)s, %(notes)s,
                %(status)s
            )
            RETURNING id, reference_number, status
        """, {
            "title": bid_data["title"],
            "client_name": bid_data["client_name"],
            "client_contact": bid_data.get("client_contact"),
            "client_email": bid_data.get("client_email"),
            "deadline": deadline,
            "estimated_value": bid_data.get("estimated_value"),
            "currency": bid_data.get("currency", "MYR"),
            "margin_percentage": bid_data.get("margin_percentage"),
            "source": bid_data.get("source", "TDD_TEST"),
            "tags": bid_data.get("tags", []),
            "notes": bid_data.get("notes"),
            "status": bid_data.get("status", "SUBMITTED")
        })
        result = db_cursor.fetchone()
        db_cursor.connection.commit()
        return dict(result)

    return _create_bid


@pytest.fixture
def create_test_reviewer(db_cursor):
    """Factory fixture to create or get a test reviewer.

    When using the real Telegram ID, checks if reviewer exists first
    and updates only the permission flags (not the ID) to avoid FK violations.
    """
    def _create_reviewer(reviewer_data: dict[str, Any]) -> dict[str, Any]:
        # Check if reviewer with this telegram_chat_id already exists
        db_cursor.execute("""
            SELECT id FROM reviewers WHERE telegram_chat_id = %(telegram_chat_id)s
        """, reviewer_data)
        existing = db_cursor.fetchone()

        if existing:
            # Update permission flags - ENABLE ALL permissions so reviewer
            # can act in any role (technical, commercial, management)
            # This prevents test interference when using shared Telegram ID
            db_cursor.execute("""
                UPDATE reviewers SET
                    can_review_technical = TRUE,
                    can_review_commercial = TRUE,
                    can_approve_management = TRUE,
                    is_active = TRUE
                WHERE telegram_chat_id = %(telegram_chat_id)s
            """, reviewer_data)
            db_cursor.connection.commit()
            # Return with all permissions enabled
            return {
                "id": existing["id"],
                **reviewer_data,
                "can_review_technical": True,
                "can_review_commercial": True,
                "can_approve_management": True,
                "is_active": True
            }
        else:
            # Insert new reviewer
            db_cursor.execute("""
                INSERT INTO reviewers (
                    telegram_chat_id, telegram_username, name, email,
                    role, department, can_review_technical, can_review_commercial,
                    can_approve_management, is_active
                ) VALUES (
                    %(telegram_chat_id)s, %(telegram_username)s, %(name)s, %(email)s,
                    %(role)s, %(department)s, %(can_review_technical)s, %(can_review_commercial)s,
                    %(can_approve_management)s, %(is_active)s
                )
                RETURNING id
            """, reviewer_data)
            result = db_cursor.fetchone()
            db_cursor.connection.commit()
            return {"id": result["id"], **reviewer_data}

    return _create_reviewer


@pytest.fixture
def create_test_review(db_cursor):
    """Factory fixture to create a test review record."""
    def _create_review(
        bid_id: str,
        review_type: str,
        assigned_to: str = None,
        decision: str = "PENDING",
        sla_hours: int = 48
    ) -> dict[str, Any]:
        due_at = datetime.now(timezone.utc) + timedelta(hours=sla_hours)

        db_cursor.execute("""
            INSERT INTO reviews (
                bid_id, review_type, assigned_to, decision, due_at, sla_hours
            ) VALUES (
                %(bid_id)s, %(review_type)s, %(assigned_to)s, %(decision)s,
                %(due_at)s, %(sla_hours)s
            )
            RETURNING id
        """, {
            "bid_id": bid_id,
            "review_type": review_type,
            "assigned_to": assigned_to,
            "decision": decision,
            "due_at": due_at,
            "sla_hours": sla_hours
        })
        result = db_cursor.fetchone()
        db_cursor.connection.commit()
        return {
            "id": result["id"],
            "bid_id": bid_id,
            "review_type": review_type,
            "assigned_to": assigned_to,
            "decision": decision
        }

    return _create_review


# =============================================================================
# CLEANUP FIXTURES
# =============================================================================

@pytest.fixture
def cleanup_test_data(db_cursor):
    """
    Cleanup fixture to remove test data after tests.
    Call at the end of tests that create persistent data.

    Note: Reviewers with the real REAL_TELEGRAM_CHAT_ID are preserved (not deleted)
    since they're used for real Telegram message delivery.
    """
    created_bids = []
    created_reviewers = []

    def _track_bid(bid_id: str):
        created_bids.append(bid_id)

    def _track_reviewer(reviewer_id: str):
        created_reviewers.append(reviewer_id)

    yield {"track_bid": _track_bid, "track_reviewer": _track_reviewer}

    # Cleanup bids first (they may reference reviewers)
    if created_bids:
        # Clear current_reviewer_id references first
        db_cursor.execute(
            "UPDATE bids SET current_reviewer_id = NULL WHERE id = ANY(%s::uuid[])",
            (created_bids,)
        )
        # Delete reviews associated with these bids
        db_cursor.execute(
            "DELETE FROM reviews WHERE bid_id = ANY(%s::uuid[])",
            (created_bids,)
        )
        # Delete audit logs for these bids
        db_cursor.execute(
            "DELETE FROM audit_log WHERE entity_id = ANY(%s::uuid[])",
            (created_bids,)
        )
        # Now delete the bids
        db_cursor.execute(
            "DELETE FROM bids WHERE id = ANY(%s::uuid[])",
            (created_bids,)
        )

    # Only delete reviewers that are NOT using the real Telegram ID
    if created_reviewers:
        db_cursor.execute(
            """DELETE FROM reviewers
               WHERE id = ANY(%s::uuid[])
               AND telegram_chat_id != %s""",
            (created_reviewers, REAL_TELEGRAM_CHAT_ID)
        )
    db_cursor.connection.commit()


# =============================================================================
# ASSERTION HELPERS
# =============================================================================

@pytest.fixture
def assert_bid_status(db_cursor):
    """Helper to assert bid status in database."""
    import time
    def _assert_status(bid_id: str, expected_status: str, wait_seconds: int = 3):
        # Wait for async workflow to complete
        time.sleep(wait_seconds)
        db_cursor.execute(
            "SELECT status FROM bids WHERE id = %s::uuid",
            (str(bid_id),)
        )
        result = db_cursor.fetchone()
        assert result is not None, f"Bid {bid_id} not found"
        assert result["status"] == expected_status, \
            f"Expected status {expected_status}, got {result['status']}"

    return _assert_status


@pytest.fixture
def assert_review_decision(db_cursor):
    """Helper to assert review decision in database."""
    import time
    def _assert_decision(bid_id: str, review_type: str, expected_decision: str, wait_seconds: int = 3):
        # Wait for async workflow to complete
        time.sleep(wait_seconds)
        db_cursor.execute("""
            SELECT decision FROM reviews
            WHERE bid_id = %s::uuid AND review_type = %s
        """, (str(bid_id), review_type))
        result = db_cursor.fetchone()
        assert result is not None, \
            f"Review not found for bid {bid_id}, type {review_type}"
        assert result["decision"] == expected_decision, \
            f"Expected decision {expected_decision}, got {result['decision']}"

    return _assert_decision


@pytest.fixture
def assert_audit_log_exists(db_cursor):
    """Helper to assert audit log entry exists."""
    import time
    def _assert_audit(entity_id: str, action: str, wait_seconds: int = 3):
        # Wait for async workflow to complete
        time.sleep(wait_seconds)
        db_cursor.execute("""
            SELECT id FROM audit_log
            WHERE entity_id = %s::uuid AND action = %s
        """, (str(entity_id), action))
        result = db_cursor.fetchone()
        assert result is not None, \
            f"Audit log not found for entity {entity_id}, action {action}"

    return _assert_audit


# =============================================================================
# MARKERS
# =============================================================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "vps: test requires VPS connectivity")
    config.addinivalue_line("markers", "destructive: test modifies database state")


# =============================================================================
# SKIP CONDITIONS
# =============================================================================

@pytest.fixture(scope="session")
def vps_available():
    """Check if VPS is reachable."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"http://{VPS_HOST}:{VPS_N8N_PORT}/healthz")
            return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def skip_without_vps(vps_available):
    """Skip test if VPS is not available."""
    if not vps_available:
        pytest.skip("VPS not available")
