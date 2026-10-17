"""Tests for the chat flow: mock mode, structured output handling, action execution."""

import json

import pytest

from app.config import Settings
from app.llm import LLMError, LLMResponse, TradeInstruction, WatchlistInstruction, mock_response
from app.llm import client as llm_client
from app.llm.prompt import summarize_actions


def chat(client, text):
    return client.post("/api/chat", json={"message": text})


class TestMockResponse:
    @pytest.mark.parametrize(
        ("text", "trade"),
        [
            ("buy 5 aapl", ("AAPL", "buy", 5.0)),
            ("Please BUY 2.5 nvda now", ("NVDA", "buy", 2.5)),
            ("sell 3 TSLA", ("TSLA", "sell", 3.0)),
        ],
    )
    def test_trades(self, text, trade):
        r = mock_response(text)
        assert [(t.ticker, t.side, t.quantity) for t in r.trades] == [trade]
        assert r.watchlist_changes == []

    @pytest.mark.parametrize(
        ("text", "change"),
        [
            ("watch pypl", ("PYPL", "add")),
            ("add AMD", ("AMD", "add")),
            ("unwatch nflx", ("NFLX", "remove")),
            ("remove V", ("V", "remove")),
        ],
    )
    def test_watchlist(self, text, change):
        r = mock_response(text)
        assert [(w.ticker, w.action) for w in r.watchlist_changes] == [change]
        assert r.trades == []

    def test_fallback(self):
        r = mock_response("how is my portfolio?")
        assert r.message == "Mock response: I received your message."
        assert r.trades == [] and r.watchlist_changes == []


class TestMockChatApi:
    """LLM_MOCK=true (the default test settings)."""

    def test_plain_message(self, client):
        r = chat(client, "hello")
        assert r.status_code == 200
        body = r.json()
        assert body["message"] == "Mock response: I received your message."
        assert body["actions"] == {"trades": [], "watchlist_changes": []}
        assert body["created_at"].endswith("Z")

    def test_buy_executes_trade(self, client):
        r = chat(client, "buy 5 AAPL")
        body = r.json()
        assert body["message"] == "Buying 5 AAPL."
        assert body["actions"]["trades"] == [
            {"ticker": "AAPL", "side": "buy", "quantity": 5.0, "status": "executed",
             "price": 100.0, "error": None}
        ]
        assert client.get("/api/portfolio").json()["cash_balance"] == 9500.0

    def test_failed_trade_reported_inline(self, client):
        body = chat(client, "buy 500 AAPL").json()
        trade = body["actions"]["trades"][0]
        assert trade["status"] == "failed"
        assert trade["error"] == "insufficient_cash"
        assert trade["price"] is None
        assert "⚠ Buy 500 AAPL failed: insufficient cash" in body["message"]
        assert client.get("/api/portfolio").json()["cash_balance"] == 10000.0

    def test_watchlist_add_and_remove(self, client, source):
        body = chat(client, "watch PYPL").json()
        assert body["actions"]["watchlist_changes"][0]["status"] == "executed"
        assert "PYPL" in source.get_tickers()

        body = chat(client, "remove PYPL").json()
        assert body["actions"]["watchlist_changes"][0]["status"] == "executed"
        assert "PYPL" not in source.get_tickers()

    def test_watchlist_failure_reported(self, client):
        body = chat(client, "watch AAPL").json()
        change = body["actions"]["watchlist_changes"][0]
        assert change == {"ticker": "AAPL", "action": "add", "status": "failed",
                          "error": "already_watching"}
        assert "already on watchlist" in body["message"]

    @pytest.mark.parametrize("text", ["", "   "])
    def test_empty_message_rejected(self, client, text):
        assert chat(client, text).status_code == 422

    def test_history_persisted_in_order(self, client):
        chat(client, "hello")
        chat(client, "buy 1 AAPL")

        messages = client.get("/api/chat/history").json()["messages"]
        assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
        assert messages[0]["content"] == "hello"
        assert messages[0]["actions"] is None
        assert messages[3]["actions"]["trades"][0]["status"] == "executed"

    def test_history_limit_returns_latest(self, client):
        for i in range(3):
            chat(client, f"message {i}")
        messages = client.get("/api/chat/history", params={"limit": 2}).json()["messages"]
        assert [m["role"] for m in messages] == ["user", "assistant"]
        assert messages[0]["content"] == "message 2"


@pytest.fixture
def real_settings(settings: Settings) -> Settings:
    """Settings with mock mode off, so the (stubbed) real client is used."""
    return Settings(**{**settings.__dict__, "llm_mock": False})


@pytest.fixture
def real_client(real_settings, prices, source_holder):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from tests.core.conftest import FakeSource

    def factory(cache):
        source_holder["source"] = FakeSource(cache, prices)
        return source_holder["source"]

    with TestClient(create_app(settings=real_settings, source_factory=factory)) as c:
        yield c


class TestRealLLMPath:
    """LLM_MOCK=false with `call_llm` stubbed: prompt building, parsing, failures."""

    def test_prompt_contains_context_and_history(self, real_client, monkeypatch):
        captured = []

        async def fake_llm(messages):
            captured.append(messages)
            return LLMResponse(
                message="Buying 2 AAPL.",
                trades=[TradeInstruction(ticker="AAPL", side="buy", quantity=2)],
                watchlist_changes=[],
            )

        monkeypatch.setattr(llm_client, "call_llm", fake_llm)
        chat(real_client, "buy two apple")
        chat(real_client, "what do I own?")

        first, second = captured
        assert first[0]["role"] == "system" and "FinAlly" in first[0]["content"]
        context = json.loads(first[1]["content"].split("\n", 1)[1])
        assert context["cash_balance"] == 10000.0
        assert {w["ticker"] for w in context["watchlist"]} >= {"AAPL", "NVDA"}
        assert first[-1] == {"role": "user", "content": "buy two apple"}

        # Second call sees the updated portfolio and the prior exchange with its actions
        context = json.loads(second[1]["content"].split("\n", 1)[1])
        assert context["positions"][0]["ticker"] == "AAPL"
        assert [m["role"] for m in second[2:]] == ["user", "assistant", "user"]
        assert "[Actions: buy 2 AAPL at $100.00]" in second[3]["content"]

    def test_watchlist_changes_run_before_trades(self, real_client, monkeypatch, source):
        async def fake_llm(messages):
            return LLMResponse(
                message="Done.",
                trades=[TradeInstruction(ticker="PYPL", side="buy", quantity=1)],
                watchlist_changes=[WatchlistInstruction(ticker="PYPL", action="add")],
            )

        monkeypatch.setattr(llm_client, "call_llm", fake_llm)
        body = chat(real_client, "add paypal and buy one").json()
        assert body["actions"]["watchlist_changes"][0]["status"] == "executed"
        assert body["actions"]["trades"][0]["status"] == "executed"
        assert body["message"] == "Done."

    def test_llm_failure_returns_502_and_keeps_user_message(self, real_client, monkeypatch):
        async def failing_llm(messages):
            raise LLMError("boom")

        monkeypatch.setattr(llm_client, "call_llm", failing_llm)
        r = chat(real_client, "hello")
        assert r.status_code == 502
        assert r.json()["detail"]["code"] == "llm_error"

        messages = real_client.get("/api/chat/history").json()["messages"]
        assert [m["role"] for m in messages] == ["user"]
        assert real_client.get("/api/portfolio").json()["cash_balance"] == 10000.0


class FakeCompletion:
    def __init__(self, content):
        self.choices = [type("Choice", (), {"message": type("Msg", (), {"content": content})()})()]


class TestClientParsing:
    """The real client's parsing of raw model output (litellm.completion stubbed)."""

    async def test_valid_json(self, monkeypatch):
        payload = {"message": "Hi", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 1}],
                   "watchlist_changes": []}
        monkeypatch.setattr(llm_client, "completion", lambda **kw: FakeCompletion(json.dumps(payload)))
        result = await llm_client.call_llm([])
        assert result.trades[0].ticker == "AAPL"

    def test_passes_cerebras_routing(self, monkeypatch):
        seen = {}

        def fake_completion(**kwargs):
            seen.update(kwargs)
            return FakeCompletion('{"message": "ok", "trades": [], "watchlist_changes": []}')

        monkeypatch.setattr(llm_client, "completion", fake_completion)
        llm_client._call_sync([{"role": "user", "content": "x"}])
        assert seen["model"] == "openrouter/openai/gpt-oss-120b"
        assert seen["extra_body"] == {"provider": {"order": ["cerebras"]}}
        assert seen["response_format"] is LLMResponse

    @pytest.mark.parametrize(
        "content",
        [
            "not json",
            '{"message": "hi"}',  # Missing required lists
            '{"message": "hi", "trades": [{"ticker": "AAPL", "side": "hold", "quantity": 1}], '
            '"watchlist_changes": []}',
            None,
        ],
    )
    async def test_malformed_output_raises(self, monkeypatch, content):
        monkeypatch.setattr(llm_client, "completion", lambda **kw: FakeCompletion(content))
        with pytest.raises(LLMError):
            await llm_client.call_llm([])

    async def test_network_error_raises(self, monkeypatch):
        def boom(**kwargs):
            raise ConnectionError("down")

        monkeypatch.setattr(llm_client, "completion", boom)
        with pytest.raises(LLMError):
            await llm_client.call_llm([])


class TestSummarizeActions:
    def test_summary(self):
        actions = {
            "trades": [
                {"ticker": "AAPL", "side": "buy", "quantity": 2.0, "status": "executed",
                 "price": 190.5, "error": None},
                {"ticker": "TSLA", "side": "sell", "quantity": 1.0, "status": "failed",
                 "price": None, "error": "insufficient_shares"},
            ],
            "watchlist_changes": [
                {"ticker": "PYPL", "action": "add", "status": "executed", "error": None}
            ],
        }
        summary = summarize_actions(actions)
        assert "buy 2 AAPL at $190.50" in summary
        assert "sell 1 TSLA FAILED (insufficient_shares)" in summary
        assert "watchlist add PYPL done" in summary

    def test_empty(self):
        assert summarize_actions(None) == ""
        assert summarize_actions({"trades": [], "watchlist_changes": []}) == ""
