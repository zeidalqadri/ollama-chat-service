"""
Ollama API Mock Server

Provides mock responses for Ollama LLM API calls.
Supports configurable responses for different models and prompts.
"""

from dataclasses import dataclass, field
from typing import Any, Callable
from datetime import datetime, timezone
import json
import re


@dataclass
class OllamaCall:
    """Record of an Ollama API call."""
    endpoint: str
    model: str
    prompt: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response: str = ""


class OllamaMock:
    """
    Mock Ollama API for testing n8n workflows.

    Usage with respx:
        mock = OllamaMock()
        mock.setup_routes(respx_mock)

        # Configure responses
        mock.set_analysis_response(completeness=85, win_prob=70, risk=30)

        # After test
        assert mock.model_called("qwen3-coder:30b")
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.calls: list[OllamaCall] = []

        # Default responses
        self._analysis_response = self._default_analysis_response()
        self._ocr_response = "Document text extracted successfully."
        self._lessons_response = self._default_lessons_response()

        # Custom response handlers
        self._custom_handlers: dict[str, Callable] = {}

        # Failure simulation
        self._should_fail = False
        self._fail_count = 0
        self._max_failures = 0

    def reset(self):
        """Clear all recorded calls and reset state."""
        self.calls = []
        self._should_fail = False
        self._fail_count = 0
        self._max_failures = 0
        self._analysis_response = self._default_analysis_response()

    def setup_routes(self, respx_mock):
        """
        Configure respx mock routes for Ollama API endpoints.

        Args:
            respx_mock: The respx mock context
        """
        # /api/generate endpoint
        respx_mock.post(f"{self.base_url}/api/generate").mock(
            side_effect=self._handle_generate
        )

        # /api/chat endpoint
        respx_mock.post(f"{self.base_url}/api/chat").mock(
            side_effect=self._handle_chat
        )

        # /api/tags endpoint (list models)
        respx_mock.get(f"{self.base_url}/api/tags").mock(
            side_effect=self._handle_tags
        )

        # Health check
        respx_mock.get(f"{self.base_url}/").mock(
            side_effect=self._handle_health
        )

    def _handle_generate(self, request):
        """Handle /api/generate endpoint."""
        import httpx

        payload = json.loads(request.content)
        model = payload.get("model", "unknown")
        prompt = payload.get("prompt", "")

        # Check for simulated failure
        if self._should_fail and self._fail_count < self._max_failures:
            self._fail_count += 1
            return httpx.Response(500, json={"error": "Simulated Ollama failure"})

        # Generate response based on model/prompt
        response_text = self._generate_response(model, prompt)

        # Record call
        self.calls.append(OllamaCall(
            endpoint="/api/generate",
            model=model,
            prompt=prompt,
            response=response_text
        ))

        # Return streaming or non-streaming response
        if payload.get("stream", True):
            # Simulate streaming with single chunk
            return httpx.Response(200, json={
                "model": model,
                "response": response_text,
                "done": True
            })
        else:
            return httpx.Response(200, json={
                "model": model,
                "response": response_text,
                "done": True,
                "context": [],
                "total_duration": 1000000000,
                "load_duration": 100000000,
                "prompt_eval_count": len(prompt.split()),
                "eval_count": len(response_text.split())
            })

    def _handle_chat(self, request):
        """Handle /api/chat endpoint."""
        import httpx

        payload = json.loads(request.content)
        model = payload.get("model", "unknown")
        messages = payload.get("messages", [])
        prompt = messages[-1].get("content", "") if messages else ""

        response_text = self._generate_response(model, prompt)

        self.calls.append(OllamaCall(
            endpoint="/api/chat",
            model=model,
            prompt=prompt,
            response=response_text
        ))

        return httpx.Response(200, json={
            "model": model,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "done": True
        })

    def _handle_tags(self, request):
        """Handle /api/tags endpoint (list models)."""
        import httpx

        return httpx.Response(200, json={
            "models": [
                {"name": "qwen3-coder:30b", "size": 18000000000},
                {"name": "deepseek-ocr:latest", "size": 6700000000},
                {"name": "translategemma:latest", "size": 3300000000}
            ]
        })

    def _handle_health(self, request):
        """Handle health check."""
        import httpx
        return httpx.Response(200, text="Ollama is running")

    def _generate_response(self, model: str, prompt: str) -> str:
        """Generate appropriate response based on model and prompt."""
        # Check custom handlers first
        for pattern, handler in self._custom_handlers.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                return handler(model, prompt)

        # Model-specific responses
        if "ocr" in model.lower() or "deepseek-ocr" in model:
            return self._ocr_response

        # Check prompt content for context
        prompt_lower = prompt.lower()

        if "analyze" in prompt_lower and "bid" in prompt_lower:
            return self._analysis_response

        if "lesson" in prompt_lower or "outcome" in prompt_lower:
            return self._lessons_response

        if "assessment" in prompt_lower or "management" in prompt_lower:
            return self._management_assessment_response()

        # Default response
        return "Analysis complete. No significant issues found."

    def _default_analysis_response(self) -> str:
        """Default bid analysis response."""
        return json.dumps({
            "completeness_score": 75,
            "win_probability_score": 65,
            "risk_score": 35,
            "missing_sections": ["Executive Summary", "Risk Mitigation Plan"],
            "recommendations": [
                "Add detailed risk mitigation strategies",
                "Include executive summary for quick overview",
                "Strengthen competitive differentiators"
            ],
            "analysis": "The bid demonstrates solid technical capabilities but lacks comprehensive risk documentation."
        })

    def _default_lessons_response(self) -> str:
        """Default lessons learned response."""
        return json.dumps({
            "key_factors": [
                "Competitive pricing",
                "Strong technical proposal",
                "Client relationship"
            ],
            "what_worked": "Technical demonstration was well-received.",
            "what_didnt_work": "Pricing was slightly above market expectations.",
            "improvement_suggestions": "Consider more aggressive pricing for similar future bids.",
            "patterns_identified": {
                "win_factors": ["technical_depth", "client_engagement"],
                "loss_factors": ["price_sensitivity"]
            }
        })

    def _management_assessment_response(self) -> str:
        """Management approval assessment response."""
        return json.dumps({
            "overall_assessment": "RECOMMEND_APPROVAL",
            "confidence": 0.78,
            "key_considerations": [
                "Strong technical merit",
                "Acceptable risk profile",
                "Strategic client relationship"
            ],
            "risks": [
                "Tight delivery timeline",
                "Resource allocation during Q4"
            ],
            "recommendation": "Proceed with bid submission with noted risk mitigations."
        })

    # =========================================================================
    # CONFIGURATION METHODS
    # =========================================================================

    def set_analysis_response(
        self,
        completeness: int = 75,
        win_prob: int = 65,
        risk: int = 35,
        missing_sections: list[str] = None,
        recommendations: list[str] = None
    ):
        """Configure analysis response scores."""
        self._analysis_response = json.dumps({
            "completeness_score": completeness,
            "win_probability_score": win_prob,
            "risk_score": risk,
            "missing_sections": missing_sections or [],
            "recommendations": recommendations or [],
            "analysis": f"Completeness: {completeness}%, Win probability: {win_prob}%, Risk: {risk}%"
        })

    def set_ocr_response(self, text: str):
        """Configure OCR extraction response."""
        self._ocr_response = text

    def set_lessons_response(self, lessons: dict[str, Any]):
        """Configure lessons learned response."""
        self._lessons_response = json.dumps(lessons)

    def add_custom_handler(self, prompt_pattern: str, handler: Callable):
        """
        Add custom response handler for specific prompts.

        Args:
            prompt_pattern: Regex pattern to match prompt
            handler: Function(model, prompt) -> response_text
        """
        self._custom_handlers[prompt_pattern] = handler

    def simulate_failure(self, fail_count: int = 1):
        """
        Configure Ollama to fail for specified number of calls.
        Useful for testing retry logic.
        """
        self._should_fail = True
        self._fail_count = 0
        self._max_failures = fail_count

    # =========================================================================
    # ASSERTION HELPERS
    # =========================================================================

    @property
    def call_count(self) -> int:
        """Total number of API calls."""
        return len(self.calls)

    def model_called(self, model: str) -> bool:
        """Check if specific model was called."""
        return any(c.model == model for c in self.calls)

    def calls_for_model(self, model: str) -> list[OllamaCall]:
        """Get all calls for a specific model."""
        return [c for c in self.calls if c.model == model]

    def prompt_contained(self, text: str) -> bool:
        """Check if any prompt contained specific text."""
        return any(text.lower() in c.prompt.lower() for c in self.calls)

    def last_prompt(self) -> str | None:
        """Get the last prompt sent."""
        return self.calls[-1].prompt if self.calls else None

    def assert_model_used(self, model: str):
        """Assert that specific model was called."""
        assert self.model_called(model), \
            f"Model {model} was not called. Called models: {[c.model for c in self.calls]}"

    def assert_prompt_contains(self, text: str):
        """Assert that a prompt containing text was sent."""
        assert self.prompt_contained(text), \
            f"No prompt containing '{text}' was found"

    def get_analysis_scores(self, call_index: int = -1) -> dict[str, int] | None:
        """Extract analysis scores from a response."""
        if not self.calls:
            return None

        response = self.calls[call_index].response
        try:
            data = json.loads(response)
            return {
                "completeness": data.get("completeness_score"),
                "win_probability": data.get("win_probability_score"),
                "risk": data.get("risk_score")
            }
        except json.JSONDecodeError:
            return None
