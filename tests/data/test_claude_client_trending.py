"""Tests for claude_client trending stock search."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data.claude_client import (
    _build_trending_prompt,
    search_trending_stocks,
    EMPTY_TRENDING,
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


@pytest.fixture(autouse=True)
def _reset_error_warned():
    from src.data import claude_client
    claude_client._error_warned[0] = False
    yield


# ===================================================================
# _build_trending_prompt
# ===================================================================

class TestBuildTrendingPrompt:
    def test_japan_default(self):
        prompt = _build_trending_prompt("japan")
        assert "日本株" in prompt
        assert ".T" in prompt
        assert "JSON" in prompt

    def test_japan_jp_alias(self):
        prompt = _build_trending_prompt("jp")
        assert "日本株" in prompt

    def test_us_region(self):
        prompt = _build_trending_prompt("us")
        assert "米国株" in prompt or "US stock" in prompt
        assert "AAPL" in prompt or "MSFT" in prompt

    def test_asean_region(self):
        prompt = _build_trending_prompt("asean")
        assert "ASEAN" in prompt

    def test_with_theme(self):
        prompt = _build_trending_prompt("japan", theme="AI")
        assert "AI" in prompt

    def test_without_theme(self):
        prompt = _build_trending_prompt("japan", theme=None)
        assert "Focus specifically" not in prompt

    def test_unknown_region_falls_back_to_japan(self):
        prompt = _build_trending_prompt("unknown")
        assert "日本株" in prompt

    def test_hk_region(self):
        prompt = _build_trending_prompt("hk")
        assert ".HK" in prompt

    def test_kr_region(self):
        prompt = _build_trending_prompt("kr")
        assert ".KS" in prompt


# ===================================================================
# search_trending_stocks
# ===================================================================

class TestSearchTrendingStocks:
    def test_no_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = search_trending_stocks("japan")
        assert result["stocks"] == []
        assert result["market_context"] == ""
        assert result["raw_response"] == ""

    @patch("src.data.claude_client.anthropic")
    def test_successful_response(self, mock_anthropic, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        payload = {
            "stocks": [
                {"ticker": "7203.T", "name": "Toyota", "reason": "EV investment"},
                {"ticker": "6758.T", "name": "Sony", "reason": "PS6 hype"},
            ],
            "market_context": "Bullish on Japanese tech",
        }

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(
            json.dumps(payload)
        )
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_trending_stocks("japan")
        assert len(result["stocks"]) == 2
        assert result["stocks"][0]["ticker"] == "7203.T"
        assert result["stocks"][0]["name"] == "Toyota"
        assert result["stocks"][0]["reason"] == "EV investment"
        assert result["market_context"] == "Bullish on Japanese tech"

    @patch("src.data.claude_client.anthropic")
    def test_malformed_stocks_filtered(self, mock_anthropic, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        payload = {
            "stocks": [
                {"ticker": "7203.T", "name": "Toyota", "reason": "OK"},
                {"name": "No Ticker Corp", "reason": "missing"},
                {"ticker": 123, "name": "Bad type"},
            ],
            "market_context": "",
        }

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(
            json.dumps(payload)
        )
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_trending_stocks("japan")
        assert len(result["stocks"]) == 1
        assert result["stocks"][0]["ticker"] == "7203.T"

    @patch("src.data.claude_client.anthropic")
    def test_theme_in_prompt(self, mock_anthropic, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(
            '{"stocks": [], "market_context": ""}'
        )
        mock_anthropic.Anthropic.return_value = mock_client

        search_trending_stocks("us", theme="AI")

        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "AI" in prompt

    @patch("src.data.claude_client.anthropic")
    def test_api_error_returns_empty(self, mock_anthropic, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_trending_stocks("japan")
        assert result["stocks"] == []

    @patch("src.data.claude_client.anthropic")
    def test_non_json_response(self, mock_anthropic, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(
            "Not JSON at all"
        )
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_trending_stocks("japan")
        assert result["stocks"] == []
        assert result["raw_response"] == "Not JSON at all"

    @patch("src.data.claude_client.anthropic")
    def test_empty_stocks_list(self, mock_anthropic, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(
            '{"stocks": [], "market_context": "No trends"}'
        )
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_trending_stocks("japan")
        assert result["stocks"] == []
        assert result["market_context"] == "No trends"

    @patch("src.data.claude_client.anthropic")
    def test_ticker_whitespace_stripped(self, mock_anthropic, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        payload = {
            "stocks": [{"ticker": " 7203.T ", "name": "Toyota", "reason": "test"}],
            "market_context": "",
        }

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(
            json.dumps(payload)
        )
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_trending_stocks("japan")
        assert result["stocks"][0]["ticker"] == "7203.T"

    @patch("src.data.claude_client.anthropic")
    def test_non_string_name_reason(self, mock_anthropic, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        payload = {
            "stocks": [{"ticker": "AAPL", "name": 123, "reason": None}],
            "market_context": "",
        }

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(
            json.dumps(payload)
        )
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_trending_stocks("us")
        assert result["stocks"][0]["name"] == ""
        assert result["stocks"][0]["reason"] == ""
