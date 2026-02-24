"""Tests for src/data/claude_client.py."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data.claude_client import (
    is_available,
    search_x_sentiment,
    _build_sentiment_prompt,
    _parse_json_response,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_claude_response(text: str, stop_reason: str = "end_turn") -> MagicMock:
    """Build a mock Anthropic API response that returns *text*."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    response = MagicMock()
    response.content = [text_block]
    response.stop_reason = stop_reason
    return response


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------

class TestIsAvailable:
    def test_with_key(self, monkeypatch):
        """Returns True when ANTHROPIC_API_KEY is set and anthropic is installed."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)
        assert is_available() is True

    def test_without_key(self, monkeypatch):
        """Returns False when ANTHROPIC_API_KEY is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert is_available() is False

    def test_empty_key(self, monkeypatch):
        """Returns False when ANTHROPIC_API_KEY is empty string."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        assert is_available() is False

    def test_no_anthropic_package(self, monkeypatch):
        """Returns False when anthropic package is not installed."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", False)
        assert is_available() is False


# ---------------------------------------------------------------------------
# _build_sentiment_prompt
# ---------------------------------------------------------------------------

class TestBuildSentimentPrompt:
    def test_basic_prompt(self):
        """Prompt includes symbol."""
        prompt = _build_sentiment_prompt("AAPL")
        assert "AAPL" in prompt
        assert "sentiment" in prompt.lower()

    def test_with_company_name(self):
        """Prompt includes company name."""
        prompt = _build_sentiment_prompt("7203.T", "Toyota")
        assert "Toyota" in prompt
        assert "7203.T" in prompt


# ---------------------------------------------------------------------------
# _parse_json_response
# ---------------------------------------------------------------------------

class TestParseJsonResponse:
    def test_valid_json(self):
        """Parses a clean JSON string."""
        text = '{"key": "value", "count": 42}'
        result = _parse_json_response(text)
        assert result == {"key": "value", "count": 42}

    def test_json_with_surrounding_text(self):
        """Extracts JSON from text with surrounding content."""
        text = 'Here is the result: {"key": "value"} and more text'
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_markdown_code_block(self):
        """Extracts JSON from a markdown code block."""
        text = '```json\n{"key": "value", "count": 42}\n```'
        result = _parse_json_response(text)
        assert result == {"key": "value", "count": 42}

    def test_markdown_code_block_no_lang(self):
        """Extracts JSON from a markdown code block without language tag."""
        text = '```\n{"key": "value"}\n```'
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_invalid_json(self):
        """Returns empty dict for text with no valid JSON."""
        result = _parse_json_response("This is just plain text")
        assert result == {}

    def test_empty_string(self):
        """Returns empty dict for empty string."""
        result = _parse_json_response("")
        assert result == {}


# ---------------------------------------------------------------------------
# search_x_sentiment
# ---------------------------------------------------------------------------

class TestSearchXSentiment:
    def test_no_api_key(self, monkeypatch):
        """Returns empty result when API key is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = search_x_sentiment("AAPL")
        assert result["positive"] == []
        assert result["negative"] == []
        assert result["sentiment_score"] == 0.0
        assert result["raw_response"] == ""

    @patch("src.data.claude_client.anthropic")
    def test_successful_response(self, mock_anthropic, monkeypatch):
        """Parses a successful Claude API response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        json_content = json.dumps({
            "positive": ["Strong earnings beat", "AI growth momentum"],
            "negative": ["China market weakness"],
            "sentiment_score": 0.6,
        })

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(json_content)
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_x_sentiment("AAPL", "Apple Inc.")
        assert len(result["positive"]) == 2
        assert len(result["negative"]) == 1
        assert result["sentiment_score"] == 0.6
        assert result["raw_response"] == json_content

    @patch("src.data.claude_client.anthropic")
    def test_api_error(self, mock_anthropic, monkeypatch):
        """Returns empty result on API error (graceful degradation)."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)
        mod._error_warned[0] = False

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_x_sentiment("AAPL")
        assert result["positive"] == []
        assert result["sentiment_score"] == 0.0

    @patch("src.data.claude_client.anthropic")
    def test_malformed_json_response(self, mock_anthropic, monkeypatch):
        """Handles malformed JSON in response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(
            "This is not JSON at all"
        )
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_x_sentiment("AAPL")
        assert result["raw_response"] == "This is not JSON at all"
        assert result["positive"] == []

    @patch("src.data.claude_client.anthropic")
    def test_sentiment_score_clamping(self, mock_anthropic, monkeypatch):
        """Sentiment score is clamped to [-1, 1]."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        json_content = json.dumps({
            "positive": [],
            "negative": [],
            "sentiment_score": 5.0,  # Out of range
        })

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(json_content)
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_x_sentiment("AAPL")
        assert result["sentiment_score"] == 1.0

    @patch("src.data.claude_client.anthropic")
    def test_pause_turn_handling(self, mock_anthropic, monkeypatch):
        """Handles pause_turn by continuing the conversation."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        json_content = json.dumps({
            "positive": ["Good earnings"],
            "negative": [],
            "sentiment_score": 0.5,
        })

        # First call returns pause_turn, second returns end_turn with data
        pause_response = _make_claude_response("Searching...", stop_reason="pause_turn")
        final_response = _make_claude_response(json_content, stop_reason="end_turn")

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [pause_response, final_response]
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_x_sentiment("AAPL")
        assert result["positive"] == ["Good earnings"]
        assert result["sentiment_score"] == 0.5
        assert mock_client.messages.create.call_count == 2
