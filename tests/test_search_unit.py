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


def test_execute_search_family_builds_unified_output(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_query_search_channels(
        channels: list[str],
        query: str,
        api_key: str | None = None,
    ) -> list[dict]:
        assert channels == ["announcement"]
        assert query == "最近的分红公告"
        assert api_key == "token"
        return [
            {
                "title": "公告A",
                "summary": "摘要A",
                "url": "https://example.com/a",
                "publish_date": "2024-01-01",
            },
            {
                "title": "公告B",
                "summary": "摘要B",
                "url": "https://example.com/b",
                "publish_date": "2024-01-02",
            },
        ]

    monkeypatch.setattr(iwencai_cli, "query_search_channels", fake_query_search_channels)

    output = iwencai_cli.execute_search_family(
        query="最近的分红公告",
        channels=["announcement"],
        limit="1",
        api_key="token",
    )

    assert "skill" not in output
    assert "skill_name" not in output
    assert output["family"] == "comprehensive_search"
    assert output["returned_count"] == 1
    assert output["total_count"] == 2
    assert output["has_more"] is True
    assert "routing" not in output
    assert output["source"]["channel"] == "announcement"
    assert output["data"][0]["title"] == "公告A"


def test_execute_search_family_uses_all_channels_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_query_search_channels(
        channels: list[str],
        query: str,
        api_key: str | None = None,
    ) -> list[dict]:
        assert channels == ["announcement", "investor", "news", "report"]
        assert query == "最近的分红公告"
        assert api_key == "token"
        return [{"title": "公告A"}]

    monkeypatch.setattr(iwencai_cli, "query_search_channels", fake_query_search_channels)

    output = iwencai_cli.execute_search_family(
        query="最近的分红公告",
        api_key="token",
    )

    assert output["family"] == "comprehensive_search"
    assert "skill" not in output
    assert "routing" not in output
    assert output["source"]["channels"] == ["announcement", "investor", "news", "report"]
    assert output["data"] == [{"title": "公告A"}]


def test_execute_search_family_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError):
        iwencai_cli.execute_search_family(
            query="最新政策",
            channels=["news"],
            limit="0",
        )


def test_execute_search_family_rejects_unknown_channel() -> None:
    with pytest.raises(ValueError):
        iwencai_cli.execute_search_family(query="最近公告", channels=["unknown"])


def test_query_search_channels_uses_fresh_opener_and_no_proxy(
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
            return _FakeResponse('{"data": []}')

    monkeypatch.setattr(iwencai_cli, "ensure_no_proxy_hosts", fake_no_proxy)
    monkeypatch.setattr(iwencai_cli.urllib.request, "build_opener", lambda: FakeOpener())

    result = iwencai_cli.query_search_channels(
        channels=["announcement"],
        query="最近的分红公告",
        api_key="token",
    )

    assert captured["no_proxy_called"] is True
    assert captured["url"] == iwencai_cli.DEFAULT_SEARCH_API_URL
    assert captured["timeout"] == 30
    assert result == []
