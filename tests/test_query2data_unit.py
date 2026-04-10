from __future__ import annotations

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


def test_execute_query2data_family_builds_unified_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_query_iwencai(
        query: str,
        page: str,
        limit: str,
        is_cache: str,
        api_key: str | None,
    ) -> dict:
        assert query == "2连板股票"
        assert page == "1"
        assert limit == "10"
        return {
            "datas": [{"股票代码": "000793.SZ"}],
            "total_count": 1,
            "chunks_info": {"query": query},
        }

    monkeypatch.setattr(iwencai_cli, "query_iwencai", fake_query_iwencai)

    output = iwencai_cli.execute_query2data_family(
        query="2连板股票",
        api_key="token",
    )

    assert "skill" not in output
    assert "skill_name" not in output
    assert output["family"] == "query2data"
    assert "routing" not in output
    assert output["datas"] == [{"股票代码": "000793.SZ"}]


def test_execute_query2data_family_fetches_all_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "1": {
            "datas": [{"代码": "A"}, {"代码": "B"}],
            "total_count": 3,
            "chunks_info": {"page": 1},
        },
        "2": {
            "datas": [{"代码": "C"}],
            "total_count": 3,
            "chunks_info": {"page": 2},
        },
    }

    def fake_query_iwencai(
        query: str,
        page: str,
        limit: str,
        is_cache: str,
        api_key: str | None,
    ) -> dict:
        return responses[page]

    monkeypatch.setattr(iwencai_cli, "query_iwencai", fake_query_iwencai)

    output = iwencai_cli.execute_query2data_family(
        query="最近的业绩预告",
        limit="2",
        all_pages=True,
    )

    assert output["pages_fetched"] == [1, 2]
    assert output["returned_count"] == 3
    assert output["total_count"] == 3
    assert output["has_more"] is False


def test_execute_query2data_family_rejects_invalid_page() -> None:
    with pytest.raises(ValueError):
        iwencai_cli.execute_query2data_family(query="最新行情", page="0")


def test_query_iwencai_uses_fresh_opener_and_no_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {"no_proxy_called": False}

    def fake_no_proxy() -> tuple[str, ...]:
        captured["no_proxy_called"] = True
        return iwencai_cli.DEFAULT_NO_PROXY_HOSTS

    class FakeOpener:
        def open(self, request, timeout: int = 30) -> _FakeResponse:
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return _FakeResponse(
                '{"status_code": 0, "datas": [], "code_count": 0, "chunks_info": {}}'
            )

    monkeypatch.setattr(iwencai_cli, "ensure_no_proxy_hosts", fake_no_proxy)
    monkeypatch.setattr(iwencai_cli.urllib.request, "build_opener", lambda: FakeOpener())

    result = iwencai_cli.query_iwencai(
        query="2连板股票",
        page="1",
        limit="10",
        is_cache=iwencai_cli.DEFAULT_IS_CACHE,
        api_key="token",
    )

    assert captured["no_proxy_called"] is True
    assert captured["url"] == iwencai_cli.DEFAULT_API_URL
    assert captured["timeout"] == 30
    assert result["datas"] == []
