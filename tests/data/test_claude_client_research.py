"""Tests for claude_client.py research functions.

Tests for _call_claude_api, _parse_json_response, _is_japanese_stock,
_contains_japanese, search_stock_deep, search_industry, search_market,
search_business.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data.claude_client import (
    _call_claude_api,
    _parse_json_response,
    _is_japanese_stock,
    _contains_japanese,
    search_stock_deep,
    search_industry,
    search_market,
    search_business,
    EMPTY_STOCK_DEEP,
    EMPTY_INDUSTRY,
    EMPTY_MARKET,
    EMPTY_BUSINESS,
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
    """Reset the module-level _error_warned flag before each test."""
    from src.data import claude_client
    claude_client._error_warned[0] = False
    yield


# ===================================================================
# _call_claude_api
# ===================================================================

class TestCallClaudeApi:

    def test_no_api_key(self, monkeypatch):
        """Returns empty string when ANTHROPIC_API_KEY is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _call_claude_api("test prompt")
        assert result == ""

    @patch("src.data.claude_client.anthropic")
    def test_successful_response(self, mock_anthropic, monkeypatch):
        """Returns text content from a successful API response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response("Hello from Claude")
        mock_anthropic.Anthropic.return_value = mock_client

        result = _call_claude_api("test prompt")
        assert result == "Hello from Claude"

    @patch("src.data.claude_client.anthropic")
    def test_api_error(self, mock_anthropic, monkeypatch):
        """Returns empty string on API error."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic.Anthropic.return_value = mock_client

        result = _call_claude_api("test prompt")
        assert result == ""

    @patch("src.data.claude_client.anthropic")
    def test_pause_turn_continues(self, mock_anthropic, monkeypatch):
        """Continues conversation on pause_turn."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        pause_resp = _make_claude_response("Searching...", stop_reason="pause_turn")
        final_resp = _make_claude_response("Final result")

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [pause_resp, final_resp]
        mock_anthropic.Anthropic.return_value = mock_client

        result = _call_claude_api("test prompt")
        assert result == "Final result"
        assert mock_client.messages.create.call_count == 2

    @patch("src.data.claude_client.anthropic")
    def test_multiple_text_blocks(self, mock_anthropic, monkeypatch):
        """Concatenates multiple text blocks in response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        text1 = MagicMock()
        text1.type = "text"
        text1.text = "Part 1 "
        text2 = MagicMock()
        text2.type = "text"
        text2.text = "Part 2"
        tool_use = MagicMock()
        tool_use.type = "server_tool_use"

        response = MagicMock()
        response.content = [text1, tool_use, text2]
        response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = response
        mock_anthropic.Anthropic.return_value = mock_client

        result = _call_claude_api("test prompt")
        assert result == "Part 1 Part 2"


# ===================================================================
# _parse_json_response
# ===================================================================

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

    def test_invalid_json(self):
        """Returns empty dict for text with no valid JSON."""
        result = _parse_json_response("This is just plain text")
        assert result == {}

    def test_empty_string(self):
        """Returns empty dict for empty string."""
        result = _parse_json_response("")
        assert result == {}

    def test_markdown_code_block(self):
        """Extracts JSON from markdown code block."""
        text = '```json\n{"key": "value"}\n```'
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_markdown_code_block_no_lang(self):
        """Extracts JSON from code block without language tag."""
        text = '```\n{"key": "value"}\n```'
        result = _parse_json_response(text)
        assert result == {"key": "value"}


# ===================================================================
# _is_japanese_stock
# ===================================================================

class TestIsJapaneseStock:

    def test_t_suffix(self):
        """7203.T is a Japanese stock."""
        assert _is_japanese_stock("7203.T") is True

    def test_s_suffix(self):
        """1234.S is a Japanese stock (Sapporo exchange)."""
        assert _is_japanese_stock("1234.S") is True

    def test_us_stock(self):
        """AAPL is not a Japanese stock."""
        assert _is_japanese_stock("AAPL") is False

    def test_sg_stock(self):
        """D05.SI is not a Japanese stock."""
        assert _is_japanese_stock("D05.SI") is False


# ===================================================================
# _contains_japanese
# ===================================================================

class TestContainsJapanese:

    def test_japanese_text(self):
        """Text with kanji returns True."""
        assert _contains_japanese("半導体") is True

    def test_english_text(self):
        """English-only text returns False."""
        assert _contains_japanese("semiconductor") is False

    def test_mixed(self):
        """Mixed text with Japanese chars returns True."""
        assert _contains_japanese("AI半導体") is True


# ===================================================================
# search_stock_deep
# ===================================================================

class TestSearchStockDeep:

    def test_no_api_key(self, monkeypatch):
        """Returns EMPTY_STOCK_DEEP when API key is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = search_stock_deep("AAPL")
        assert result["recent_news"] == []
        assert result["catalysts"] == {"positive": [], "negative": []}
        assert result["x_sentiment"]["score"] == 0.0
        assert result["raw_response"] == ""

    @patch("src.data.claude_client.anthropic")
    def test_successful_response(self, mock_anthropic, monkeypatch):
        """Parses a successful deep research response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        json_content = json.dumps({
            "recent_news": ["Earnings beat expectations", "New product launch"],
            "catalysts": {
                "positive": ["AI revenue growth"],
                "negative": ["Trade war risk"],
            },
            "analyst_views": ["Buy rating from Goldman"],
            "x_sentiment": {
                "score": 0.7,
                "summary": "Bullish sentiment",
                "key_opinions": ["Strong buy signals"],
            },
            "competitive_notes": ["Market leader in segment"],
        })

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(json_content)
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_stock_deep("AAPL", "Apple Inc.")
        assert len(result["recent_news"]) == 2
        assert result["catalysts"]["positive"] == ["AI revenue growth"]
        assert result["catalysts"]["negative"] == ["Trade war risk"]
        assert result["analyst_views"] == ["Buy rating from Goldman"]
        assert result["x_sentiment"]["score"] == 0.7
        assert result["x_sentiment"]["summary"] == "Bullish sentiment"
        assert result["competitive_notes"] == ["Market leader in segment"]

    @patch("src.data.claude_client.anthropic")
    def test_japanese_stock_prompt(self, mock_anthropic, monkeypatch):
        """Japanese stock uses Japanese prompt."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response("{}")
        mock_anthropic.Anthropic.return_value = mock_client

        search_stock_deep("7203.T", "Toyota")

        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "調査" in prompt or "7203.T" in prompt

    @patch("src.data.claude_client.anthropic")
    def test_us_stock_prompt(self, mock_anthropic, monkeypatch):
        """US stock uses English prompt."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response("{}")
        mock_anthropic.Anthropic.return_value = mock_client

        search_stock_deep("AAPL", "Apple Inc.")

        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "Research" in prompt

    @patch("src.data.claude_client.anthropic")
    def test_malformed_response(self, mock_anthropic, monkeypatch):
        """Malformed JSON sets raw_response but leaves data empty."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(
            "This is not JSON at all"
        )
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_stock_deep("AAPL")
        assert result["raw_response"] == "This is not JSON at all"
        assert result["recent_news"] == []
        assert result["catalysts"] == {"positive": [], "negative": []}


# ===================================================================
# search_industry
# ===================================================================

class TestSearchIndustry:

    def test_no_api_key(self, monkeypatch):
        """Returns EMPTY_INDUSTRY when API key is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = search_industry("半導体")
        assert result["trends"] == []
        assert result["key_players"] == []
        assert result["raw_response"] == ""

    @patch("src.data.claude_client.anthropic")
    def test_successful_response(self, mock_anthropic, monkeypatch):
        """Parses a successful industry research response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        json_content = json.dumps({
            "trends": ["AI chip demand surging"],
            "key_players": [
                {"name": "TSMC", "ticker": "TSM", "note": "Foundry leader"}
            ],
            "growth_drivers": ["Data center expansion"],
            "risks": ["Geopolitical tension"],
            "regulatory": ["US export controls"],
            "investor_focus": ["CAPEX cycle"],
        })

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(json_content)
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_industry("semiconductor")
        assert result["trends"] == ["AI chip demand surging"]
        assert len(result["key_players"]) == 1
        assert result["key_players"][0]["name"] == "TSMC"
        assert result["growth_drivers"] == ["Data center expansion"]
        assert result["risks"] == ["Geopolitical tension"]
        assert result["regulatory"] == ["US export controls"]
        assert result["investor_focus"] == ["CAPEX cycle"]

    @patch("src.data.claude_client.anthropic")
    def test_japanese_theme(self, mock_anthropic, monkeypatch):
        """Japanese theme uses Japanese prompt."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response("{}")
        mock_anthropic.Anthropic.return_value = mock_client

        search_industry("半導体")

        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "半導体" in prompt
        assert "業界" in prompt or "テーマ" in prompt

    @patch("src.data.claude_client.anthropic")
    def test_english_theme(self, mock_anthropic, monkeypatch):
        """English theme uses English prompt."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response("{}")
        mock_anthropic.Anthropic.return_value = mock_client

        search_industry("semiconductor")

        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "Research" in prompt


# ===================================================================
# search_market
# ===================================================================

class TestSearchMarket:

    def test_no_api_key(self, monkeypatch):
        """Returns EMPTY_MARKET when API key is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = search_market("日経平均")
        assert result["price_action"] == ""
        assert result["macro_factors"] == []
        assert result["sentiment"]["score"] == 0.0
        assert result["raw_response"] == ""

    @patch("src.data.claude_client.anthropic")
    def test_successful_response(self, mock_anthropic, monkeypatch):
        """Parses a successful market research response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        json_content = json.dumps({
            "price_action": "Nikkei rose 1.5% on strong earnings",
            "macro_factors": ["BOJ rate decision", "Yen weakness"],
            "sentiment": {"score": 0.4, "summary": "Cautiously optimistic"},
            "upcoming_events": ["GDP release on Friday"],
            "sector_rotation": ["From defensive to cyclical"],
        })

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(json_content)
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_market("日経平均")
        assert result["price_action"] == "Nikkei rose 1.5% on strong earnings"
        assert len(result["macro_factors"]) == 2
        assert result["sentiment"]["score"] == 0.4
        assert result["sentiment"]["summary"] == "Cautiously optimistic"
        assert result["upcoming_events"] == ["GDP release on Friday"]
        assert result["sector_rotation"] == ["From defensive to cyclical"]


# ===================================================================
# search_business
# ===================================================================

class TestSearchBusiness:

    def test_no_api_key(self, monkeypatch):
        """Returns EMPTY_BUSINESS when API key is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = search_business("7751.T")
        assert result["overview"] == ""
        assert result["segments"] == []
        assert result["revenue_model"] == ""
        assert result["competitive_advantages"] == []
        assert result["raw_response"] == ""

    @patch("src.data.claude_client.anthropic")
    def test_successful_response(self, mock_anthropic, monkeypatch):
        """Parses a successful business model response."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        json_content = json.dumps({
            "overview": "Canon is a diversified imaging and optical company",
            "segments": [
                {"name": "Printing", "revenue_share": "55%", "description": "Inkjet and laser printers"},
                {"name": "Imaging", "revenue_share": "20%", "description": "Cameras and lenses"},
            ],
            "revenue_model": "Hardware sales + consumables recurring revenue",
            "competitive_advantages": ["Strong patent portfolio", "Brand recognition"],
            "key_metrics": ["Consumables attach rate", "B2B vs B2C mix"],
            "growth_strategy": ["Medical imaging expansion", "Industrial equipment"],
            "risks": ["Declining print market", "Competition from smartphones"],
        })

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(json_content)
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_business("7751.T", "Canon Inc.")
        assert result["overview"] == "Canon is a diversified imaging and optical company"
        assert len(result["segments"]) == 2
        assert result["segments"][0]["name"] == "Printing"
        assert result["segments"][0]["revenue_share"] == "55%"
        assert result["revenue_model"] == "Hardware sales + consumables recurring revenue"
        assert len(result["competitive_advantages"]) == 2
        assert len(result["key_metrics"]) == 2
        assert len(result["growth_strategy"]) == 2
        assert len(result["risks"]) == 2

    @patch("src.data.claude_client.anthropic")
    def test_japanese_stock_prompt(self, mock_anthropic, monkeypatch):
        """Japanese stock uses Japanese prompt."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response("{}")
        mock_anthropic.Anthropic.return_value = mock_client

        search_business("7751.T", "キヤノン")

        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "ビジネスモデル" in prompt or "事業概要" in prompt

    @patch("src.data.claude_client.anthropic")
    def test_us_stock_prompt(self, mock_anthropic, monkeypatch):
        """US stock uses English prompt."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response("{}")
        mock_anthropic.Anthropic.return_value = mock_client

        search_business("AAPL", "Apple Inc.")

        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "business model" in prompt.lower() or "Analyze" in prompt

    @patch("src.data.claude_client.anthropic")
    def test_malformed_response(self, mock_anthropic, monkeypatch):
        """Malformed JSON sets raw_response but leaves data empty."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(
            "This is not JSON at all"
        )
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_business("7751.T")
        assert result["raw_response"] == "This is not JSON at all"
        assert result["overview"] == ""
        assert result["segments"] == []

    @patch("src.data.claude_client.anthropic")
    def test_segment_validation(self, mock_anthropic, monkeypatch):
        """Segments with missing fields get defaults."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        import src.data.claude_client as mod
        monkeypatch.setattr(mod, "_HAS_ANTHROPIC", True)

        json_content = json.dumps({
            "segments": [
                {"name": "Division A"},
                {"name": "Division B", "revenue_share": "30%", "description": "B desc"},
            ],
        })

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_claude_response(json_content)
        mock_anthropic.Anthropic.return_value = mock_client

        result = search_business("TEST")
        assert len(result["segments"]) == 2
        assert result["segments"][0]["name"] == "Division A"
        assert result["segments"][0]["revenue_share"] == ""
        assert result["segments"][1]["description"] == "B desc"
