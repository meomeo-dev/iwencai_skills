from __future__ import annotations

import urllib.parse
import urllib.request
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
        iwencai_cli.get_api_key(
            env=env,
            dotenv_paths=(tmp_path / ".env",),
            interactive_bootstrap=False,
        )


def test_get_api_key_auto_bootstraps_when_interactive(tmp_path: Path) -> None:
    env: dict[str, str] = {}

    def fake_bootstrapper(*, dotenv_path: Path, env: dict[str, str]) -> dict[str, str]:
        assert dotenv_path == tmp_path / ".env"
        env["IWENCAI_API_KEY"] = "from_web"  # pragma: allowlist secret
        return {"api_key": "from_web"}  # pragma: allowlist secret

    api_key = iwencai_cli.get_api_key(
        env=env,
        dotenv_paths=(tmp_path / ".env",),
        interactive_bootstrap=True,
        bootstrapper=fake_bootstrapper,
    )

    assert api_key == "from_web"  # pragma: allowlist secret
    assert env["IWENCAI_API_KEY"] == "from_web"  # pragma: allowlist secret


def test_upsert_dotenv_variable_replaces_existing_value(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("FOO=bar\nIWENCAI_API_KEY=old\n", encoding="utf-8")

    iwencai_cli.upsert_dotenv_variable(dotenv, "IWENCAI_API_KEY", "new")

    assert dotenv.read_text(encoding="utf-8") == (
        'FOO=bar\nIWENCAI_API_KEY="new"\n'  # pragma: allowlist secret
    )


def test_launch_api_key_setup_page_persists_dotenv(tmp_path: Path) -> None:
    env: dict[str, str] = {}
    dotenv = tmp_path / ".env"

    def submit_form(url: str) -> None:
        payload = urllib.parse.urlencode(
            {
                "api_key": "from_web_page",  # pragma: allowlist secret
                "persist_dotenv": "on",
            }
        ).encode("utf-8")
        with urllib.request.urlopen(url, data=payload, timeout=5) as response:
            assert response.status == 200

    result = iwencai_cli.launch_api_key_setup_page(
        dotenv_path=dotenv,
        env=env,
        open_browser=False,
        timeout_seconds=5,
        ready_callback=submit_form,
    )

    assert result["success"] is True
    assert result["persisted"] is True
    assert env["IWENCAI_API_KEY"] == "from_web_page"  # pragma: allowlist secret
    assert (
        dotenv.read_text(encoding="utf-8")
        == 'IWENCAI_API_KEY="from_web_page"\n'  # pragma: allowlist secret
    )


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
