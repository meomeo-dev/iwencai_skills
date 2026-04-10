from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _run_command(
    executable: Path,
    *args: str,
    cwd: Path,
    env: dict[str, str],
    expected_returncode: int,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [str(executable), *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != expected_returncode:
        raise AssertionError(
            f"command returned {completed.returncode}, expected {expected_returncode}: "
            f"{[str(executable), *args]}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def _assert_markers(output: str, markers: list[str]) -> None:
    for marker in markers:
        if marker not in output:
            raise AssertionError(f"missing marker in output: {marker}\noutput:\n{output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test an installed iwencai executable.")
    parser.add_argument("--executable", required=True, help="Path to installed iwencai executable")
    parser.add_argument("--cwd", default=None, help="Working directory for smoke commands")
    args = parser.parse_args()

    executable = Path(args.executable).resolve()
    if not executable.is_file():
        raise SystemExit(f"missing executable: {executable}")

    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd()
    env = os.environ.copy()
    env.pop("IWENCAI_API_KEY", None)
    env.pop("PYTHONPATH", None)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    top_help = _run_command(executable, "--help", cwd=cwd, env=env, expected_returncode=0)
    _assert_markers(
        top_help.stdout,
        [
            "family 子命令",
            'iwencai -q "2连板股票"',
            "Query 写法",
        ],
    )

    query_help = _run_command(
        executable, "query2data", "--help", cwd=cwd, env=env, expected_returncode=0
    )
    _assert_markers(query_help.stdout, ["不需要指定 skill", "范围 + 条件/排序 + 时间窗"])

    search_help = _run_command(
        executable, "search", "--help", cwd=cwd, env=env, expected_returncode=0
    )
    _assert_markers(
        search_help.stdout, ["announcement, investor, news, report", "多主体时拆分查询"]
    )

    trade_help = _run_command(
        executable, "trade", "--help", cwd=cwd, env=env, expected_returncode=0
    )
    _assert_markers(trade_help.stdout, ["交易动作", "iwencai trade bootstrap-account"])

    query_without_key = _run_command(
        executable,
        "-q",
        "2连板股票",
        cwd=cwd,
        env=env,
        expected_returncode=1,
    )
    payload = json.loads(query_without_key.stdout)
    assert payload["success"] is False
    assert "API密钥未设置" in payload["error"]


if __name__ == "__main__":
    try:
        main()
    except AssertionError as err:
        print(str(err), file=sys.stderr)
        raise SystemExit(1) from err
