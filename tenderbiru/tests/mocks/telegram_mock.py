"""
Telegram API Mock Server

Provides mock responses for Telegram Bot API calls.
Tracks all API calls for assertion in tests.
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone
import json


@dataclass
class TelegramCall:
    """Record of a Telegram API call."""
    method: str
    endpoint: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TelegramMock:
    """
    Mock Telegram API for testing n8n workflows.

    Usage with respx:
        mock = TelegramMock(bot_token="123:ABC")
        mock.setup_routes(respx_mock)

        # After test
        assert mock.message_sent_to(chat_id=12345)
        assert "Bid Review" in mock.last_message_text()
    """

    def __init__(self, bot_token: str = "TEST_BOT_TOKEN"):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.calls: list[TelegramCall] = []
        self._message_id_counter = 1000
        self._callback_answers: list[dict] = []

    def reset(self):
        """Clear all recorded calls."""
        self.calls = []
        self._message_id_counter = 1000
        self._callback_answers = []

    def setup_routes(self, respx_mock):
        """
        Configure respx mock routes for all Telegram API endpoints.

        Args:
            respx_mock: The respx mock context
        """
        # sendMessage
        respx_mock.post(f"{self.base_url}/sendMessage").mock(
            side_effect=self._handle_send_message
        )

        # editMessageText
        respx_mock.post(f"{self.base_url}/editMessageText").mock(
            side_effect=self._handle_edit_message
        )

        # answerCallbackQuery
        respx_mock.post(f"{self.base_url}/answerCallbackQuery").mock(
            side_effect=self._handle_answer_callback
        )

        # sendDocument
        respx_mock.post(f"{self.base_url}/sendDocument").mock(
            side_effect=self._handle_send_document
        )

        # getUpdates (for webhook simulation)
        respx_mock.post(f"{self.base_url}/getUpdates").mock(
            side_effect=self._handle_get_updates
        )

    def _handle_send_message(self, request):
        """Handle sendMessage API call."""
        import httpx

        payload = self._parse_request(request)
        self._record_call("sendMessage", "/sendMessage", payload)

        message_id = self._next_message_id()
        response_data = {
            "ok": True,
            "result": {
                "message_id": message_id,
                "from": {
                    "id": int(self.bot_token.split(":")[0]) if ":" in self.bot_token else 0,
                    "is_bot": True,
                    "first_name": "Test Bot"
                },
                "chat": {
                    "id": payload.get("chat_id"),
                    "type": "private"
                },
                "date": int(datetime.now(timezone.utc).timestamp()),
                "text": payload.get("text", "")
            }
        }

        return httpx.Response(200, json=response_data)

    def _handle_edit_message(self, request):
        """Handle editMessageText API call."""
        import httpx

        payload = self._parse_request(request)
        self._record_call("editMessageText", "/editMessageText", payload)

        response_data = {
            "ok": True,
            "result": {
                "message_id": payload.get("message_id"),
                "chat": {
                    "id": payload.get("chat_id"),
                    "type": "private"
                },
                "date": int(datetime.now(timezone.utc).timestamp()),
                "text": payload.get("text", ""),
                "edit_date": int(datetime.now(timezone.utc).timestamp())
            }
        }

        return httpx.Response(200, json=response_data)

    def _handle_answer_callback(self, request):
        """Handle answerCallbackQuery API call."""
        import httpx

        payload = self._parse_request(request)
        self._record_call("answerCallbackQuery", "/answerCallbackQuery", payload)
        self._callback_answers.append(payload)

        return httpx.Response(200, json={"ok": True, "result": True})

    def _handle_send_document(self, request):
        """Handle sendDocument API call."""
        import httpx

        payload = self._parse_request(request)
        self._record_call("sendDocument", "/sendDocument", payload)

        message_id = self._next_message_id()
        return httpx.Response(200, json={
            "ok": True,
            "result": {
                "message_id": message_id,
                "document": {
                    "file_id": "test_file_id",
                    "file_name": "document.pdf"
                }
            }
        })

    def _handle_get_updates(self, request):
        """Handle getUpdates API call."""
        import httpx
        return httpx.Response(200, json={"ok": True, "result": []})

    def _parse_request(self, request) -> dict[str, Any]:
        """Parse request body from various content types."""
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            return json.loads(request.content)
        elif "application/x-www-form-urlencoded" in content_type:
            # Parse form data
            from urllib.parse import parse_qs
            data = parse_qs(request.content.decode())
            return {k: v[0] if len(v) == 1 else v for k, v in data.items()}
        else:
            # Try JSON anyway
            try:
                return json.loads(request.content)
            except json.JSONDecodeError:
                return {}

    def _record_call(self, method: str, endpoint: str, payload: dict):
        """Record an API call for later assertion."""
        self.calls.append(TelegramCall(
            method=method,
            endpoint=endpoint,
            payload=payload
        ))

    def _next_message_id(self) -> int:
        """Generate next message ID."""
        self._message_id_counter += 1
        return self._message_id_counter

    # =========================================================================
    # ASSERTION HELPERS
    # =========================================================================

    @property
    def call_count(self) -> int:
        """Total number of API calls."""
        return len(self.calls)

    def calls_for_method(self, method: str) -> list[TelegramCall]:
        """Get all calls for a specific method."""
        return [c for c in self.calls if c.method == method]

    def message_sent_to(self, chat_id: int) -> bool:
        """Check if a message was sent to specific chat."""
        return any(
            c.method == "sendMessage" and c.payload.get("chat_id") == chat_id
            for c in self.calls
        )

    def message_edited(self, chat_id: int, message_id: int) -> bool:
        """Check if a specific message was edited."""
        return any(
            c.method == "editMessageText" and
            c.payload.get("chat_id") == chat_id and
            c.payload.get("message_id") == message_id
            for c in self.calls
        )

    def callback_answered(self, callback_id: str = None) -> bool:
        """Check if callback was answered."""
        if callback_id:
            return any(
                c.payload.get("callback_query_id") == callback_id
                for c in self._callback_answers
            )
        return len(self._callback_answers) > 0

    def last_message_text(self) -> str | None:
        """Get text of last sent message."""
        send_calls = self.calls_for_method("sendMessage")
        if send_calls:
            return send_calls[-1].payload.get("text")
        return None

    def last_message_has_keyboard(self) -> bool:
        """Check if last message has inline keyboard."""
        send_calls = self.calls_for_method("sendMessage")
        if send_calls:
            return "reply_markup" in send_calls[-1].payload
        return False

    def messages_to_chat(self, chat_id: int) -> list[str]:
        """Get all message texts sent to a chat."""
        return [
            c.payload.get("text", "")
            for c in self.calls
            if c.method == "sendMessage" and c.payload.get("chat_id") == chat_id
        ]

    def get_inline_keyboard(self, call_index: int = -1) -> list[list[dict]] | None:
        """Get inline keyboard from a sendMessage call."""
        send_calls = self.calls_for_method("sendMessage")
        if not send_calls:
            return None

        call = send_calls[call_index]
        reply_markup = call.payload.get("reply_markup")
        if not reply_markup:
            return None

        if isinstance(reply_markup, str):
            reply_markup = json.loads(reply_markup)

        return reply_markup.get("inline_keyboard")

    def assert_message_contains(self, text: str, chat_id: int = None):
        """Assert that a message containing text was sent."""
        for call in self.calls_for_method("sendMessage"):
            msg_text = call.payload.get("text", "")
            if text in msg_text:
                if chat_id is None or call.payload.get("chat_id") == chat_id:
                    return True

        raise AssertionError(
            f"No message containing '{text}' was sent" +
            (f" to chat {chat_id}" if chat_id else "")
        )

    def assert_callback_answered_with(self, text: str = None, show_alert: bool = None):
        """Assert callback was answered with specific parameters."""
        assert self._callback_answers, "No callbacks were answered"

        last_answer = self._callback_answers[-1]

        if text is not None:
            assert text in last_answer.get("text", ""), \
                f"Callback answer text '{last_answer.get('text')}' doesn't contain '{text}'"

        if show_alert is not None:
            assert last_answer.get("show_alert") == show_alert, \
                f"Expected show_alert={show_alert}, got {last_answer.get('show_alert')}"
