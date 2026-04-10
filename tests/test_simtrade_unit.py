from __future__ import annotations

from pathlib import Path

import pytest

import iwencai_cli


class _FakeResponse:
    def __init__(self, body: str):
        self._body = body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return self._body.encode("utf-8")


def test_all_simtrade_query_handlers_exist() -> None:
    handler_names = [
        "query_simtrade_positions",
        "query_simtrade_profit",
        "query_simtrade_fund",
        "query_simtrade_today_trades",
        "query_simtrade_history_trades",
        "query_simtrade_gain_30d",
    ]

    for name in handler_names:
        assert callable(getattr(iwencai_cli, name))


def test_bootstrap_simtrade_account_persists_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account_path = tmp_path / "default_account.json"

    monkeypatch.setattr(iwencai_cli, "generate_simtrade_username", lambda: "iwencai_123")
    monkeypatch.setattr(
        iwencai_cli,
        "create_simtrade_capital_account",
        lambda username, department_id=iwencai_cli.DEFAULT_DEPARTMENT_ID: {
            "username": username,
            "capital_account": "51695817",
            "department_id": department_id,
        },
    )
    monkeypatch.setattr(
        iwencai_cli,
        "query_simtrade_shareholder_accounts",
        lambda capital_account, department_id=iwencai_cli.DEFAULT_DEPARTMENT_ID: {
            "shareholder_accounts": {"sz": "001", "sh": "A001"},
            "market_codes": {"sz": "1", "sh": "2"},
        },
    )

    account = iwencai_cli.bootstrap_simtrade_account(account_path)

    assert account["username"] == "iwencai_123"
    assert account_path.exists()
    assert iwencai_cli.load_account_state(account_path) == account


def test_bootstrap_simtrade_account_reuses_existing_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account_path = tmp_path / "default_account.json"
    existing = {"username": "iwencai_999", "capital_account": "10001"}
    iwencai_cli.save_account_state(existing, account_path)

    monkeypatch.setattr(
        iwencai_cli,
        "create_simtrade_capital_account",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not create account")),
    )

    assert iwencai_cli.bootstrap_simtrade_account(account_path) == existing


def test_place_simtrade_order_validates_and_calls_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        iwencai_cli,
        "bootstrap_simtrade_account",
        lambda account_path=iwencai_cli.DEFAULT_ACCOUNT_PATH: {
            "capital_account": "51695817",
            "department_id": "997376",
            "shareholder_accounts": {"sh": "A001"},
            "market_codes": {"sh": "2"},
        },
    )

    captured: dict = {}

    def fake_request(endpoint: str, params: dict[str, str]) -> dict:
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {"errorcode": 0, "errormsg": "", "result": [{"entrust_no": "E001"}]}

    monkeypatch.setattr(iwencai_cli, "_simtrade_request", fake_request)

    result = iwencai_cli.place_simtrade_order(
        action="buy",
        stock_code="600519",
        price=100.5,
        quantity=200,
        account_path=tmp_path / "unused.json",
    )

    assert captured["endpoint"] == "/pt_stk_weituo_dklc"
    assert captured["params"]["mmlb"] == "B"
    assert result["entrust_no"] == "E001"


def test_query_simtrade_positions_returns_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        iwencai_cli,
        "bootstrap_simtrade_account",
        lambda account_path=iwencai_cli.DEFAULT_ACCOUNT_PATH: {
            "capital_account": "51695817",
            "department_id": "997376",
            "username": "iwencai_123",
        },
    )
    monkeypatch.setattr(
        iwencai_cli,
        "_simtrade_request",
        lambda endpoint, params: {"errorcode": 0, "errormsg": "", "result": [{"zqdm": "600519"}]},
    )

    result = iwencai_cli.query_simtrade_positions(tmp_path / "unused.json")

    assert result["total_count"] == 1
    assert result["items"][0]["zqdm"] == "600519"


def test_query_simtrade_history_trades_passes_dates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        iwencai_cli,
        "bootstrap_simtrade_account",
        lambda account_path=iwencai_cli.DEFAULT_ACCOUNT_PATH: {
            "capital_account": "51695817",
            "department_id": "997376",
            "username": "iwencai_123",
        },
    )
    captured: dict = {}

    def fake_request(endpoint: str, params: dict[str, str]) -> dict:
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {"errorcode": 0, "errormsg": "", "list": [{"zqdm": "600519"}]}

    monkeypatch.setattr(iwencai_cli, "_simtrade_request", fake_request)

    result = iwencai_cli.query_simtrade_history_trades(
        start_date="20240101",
        end_date="20240131",
        account_path=tmp_path / "unused.json",
    )

    assert captured["endpoint"] == "/pt_qry_busin1"
    assert captured["params"]["start"] == "20240101"
    assert captured["params"]["end"] == "20240131"
    assert result["total_count"] == 1


def test_query_simtrade_shareholder_accounts_accepts_gdzh_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        iwencai_cli,
        "_simtrade_request",
        lambda endpoint, params: {
            "errorcode": 0,
            "errormsg": "",
            "result": [
                {"scdm": "1", "gdzh": "00165865200"},
                {"scdm": "2", "gdzh": "A541585543"},
            ],
        },
    )

    result = iwencai_cli.query_simtrade_shareholder_accounts("115079187")

    assert result["shareholder_accounts"] == {"sz": "00165865200", "sh": "A541585543"}
    assert result["market_codes"] == {"sz": "1", "sh": "2"}


def test_simtrade_request_uses_fresh_opener_and_no_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {"no_proxy_called": False}

    def fake_no_proxy() -> tuple[str, ...]:
        captured["no_proxy_called"] = True
        return iwencai_cli.DEFAULT_NO_PROXY_HOSTS

    class FakeOpener:
        def open(self, request, timeout: int = 30) -> _FakeResponse:
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return _FakeResponse('{"errorcode": 0, "result": []}')

    monkeypatch.setattr(iwencai_cli, "ensure_no_proxy_hosts", fake_no_proxy)
    monkeypatch.setattr(iwencai_cli.urllib.request, "build_opener", lambda: FakeOpener())

    result = iwencai_cli._simtrade_request("/pt_add_user", {"usrname": "iwencai_x"})  # noqa: SLF001

    assert captured["no_proxy_called"] is True
    assert captured["url"] == (
        f"{iwencai_cli.DEFAULT_SIMTRADE_BASE_URL}/pt_add_user?usrname=iwencai_x"
    )
    assert captured["timeout"] == 30
    assert result["errorcode"] == 0
