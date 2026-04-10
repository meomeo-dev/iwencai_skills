from __future__ import annotations

from pathlib import Path

import pytest

import iwencai_cli


def test_load_local_env_reads_missing_variables(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text('IWENCAI_API_KEY="abc123"\n', encoding="utf-8")
    env: dict[str, str] = {}

    loaded = iwencai_cli.load_local_env(dotenv_paths=(dotenv,), env=env)

    assert loaded == [dotenv.resolve()]
    assert env["IWENCAI_API_KEY"] == "abc123"


def test_load_local_env_does_not_override_existing_variables(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("IWENCAI_API_KEY=from_file\n", encoding="utf-8")
    env = {"IWENCAI_API_KEY": "from_env"}

    iwencai_cli.load_local_env(dotenv_paths=(dotenv,), env=env)

    assert env["IWENCAI_API_KEY"] == "from_env"


def test_get_api_key_uses_dotenv_when_env_is_empty(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("export IWENCAI_API_KEY=from_dotenv\n", encoding="utf-8")
    env: dict[str, str] = {}

    api_key = iwencai_cli.get_api_key(env=env, dotenv_paths=(dotenv,))

    assert api_key == "from_dotenv"


def test_get_api_key_raises_when_unavailable(tmp_path: Path) -> None:
    env: dict[str, str] = {}

    with pytest.raises(iwencai_cli.IWenCaiAPIError):
        iwencai_cli.get_api_key(env=env, dotenv_paths=(tmp_path / ".env",))


def test_ensure_no_proxy_hosts_merges_runtime_hosts_and_preserves_existing() -> None:
    env = {"NO_PROXY": "localhost,127.0.0.1"}

    merged = iwencai_cli.ensure_no_proxy_hosts(env=env)

    assert merged == (
        "localhost",
        "127.0.0.1",
        "openapi.iwencai.com",
        "trade.10jqka.com.cn",
    )
    assert env["NO_PROXY"] == "localhost,127.0.0.1,openapi.iwencai.com,trade.10jqka.com.cn"
    assert env["no_proxy"] == env["NO_PROXY"]
