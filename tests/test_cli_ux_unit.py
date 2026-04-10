from __future__ import annotations

import argparse

import pytest

import iwencai_cli


def test_parse_args_defaults_to_query2data_when_command_is_omitted() -> None:
    args = iwencai_cli.parse_args(["-q", "2连板股票"])
    assert args.command == "query2data"
    assert args.query == "2连板股票"


def test_render_output_jsonl_uses_items() -> None:
    text = iwencai_cli.render_output({"items": [{"a": 1}, {"a": 2}]}, "jsonl")
    assert text.splitlines() == ['{"a": 1}', '{"a": 2}']


def test_render_output_table_for_mapping() -> None:
    text = iwencai_cli.render_output(
        {"name": "公告搜索", "family": "comprehensive_search"}, "table"
    )
    assert "field" in text
    assert "公告搜索" in text


def test_handle_query2data_command_executes_family_query(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_execute_query2data_family(**kwargs: object) -> dict:
        assert kwargs["query"] == "2连板股票"
        assert kwargs["page"] == "1"
        assert kwargs["limit"] == "10"
        return {"success": True, "family": "query2data"}

    monkeypatch.setattr(iwencai_cli, "execute_query2data_family", fake_execute_query2data_family)

    args = argparse.Namespace(
        query="2连板股票",
        page="1",
        limit="10",
        all_pages=False,
        is_cache=iwencai_cli.DEFAULT_IS_CACHE,
        api_key=None,
    )
    payload = iwencai_cli.handle_query2data_command(args)
    assert payload["family"] == "query2data"


def test_handle_search_command_executes_family_search(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_execute_search_family(**kwargs: object) -> dict:
        assert kwargs["query"] == "最近的分红公告"
        assert kwargs["channels"] is None
        return {"success": True, "family": "comprehensive_search"}

    monkeypatch.setattr(iwencai_cli, "execute_search_family", fake_execute_search_family)

    args = argparse.Namespace(
        query="最近的分红公告",
        channel=None,
        limit="10",
        api_key=None,
    )
    payload = iwencai_cli.handle_search_command(args)
    assert payload["family"] == "comprehensive_search"


def test_parse_args_rejects_trade_without_action() -> None:
    with pytest.raises(SystemExit) as exc_info:
        iwencai_cli.parse_args(["trade"])

    assert exc_info.value.code == 2
