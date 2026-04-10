from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _venv_executable(venv_dir: Path, name: str) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / f"{name}.exe"
    return venv_dir / "bin" / name


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"command failed: {command}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def main() -> None:
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PYTHONNOUSERSITE"] = "1"

    with tempfile.TemporaryDirectory(prefix="iwencai-preflight-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        venv_dir = temp_dir / "venv"
        source_dir = temp_dir / "source"
        workspace_dir = temp_dir / "workspace"
        workspace_dir.mkdir()

        shutil.copytree(
            ROOT,
            source_dir,
            ignore=shutil.ignore_patterns(
                ".git",
                ".plan",
                ".pytest_cache",
                ".ruff_cache",
                "__pycache__",
                "*.pyc",
                ".iwencai",
                "build",
                "dist",
                "*.egg-info",
            ),
        )
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        python_bin = _venv_python(venv_dir)
        iwencai_bin = _venv_executable(venv_dir, "iwencai")

        _run(
            [str(python_bin), "-m", "pip", "install", "--no-deps", str(source_dir)],
            cwd=workspace_dir,
            env=env,
        )
        _run(
            [
                sys.executable,
                str(ROOT / "tests" / "cli_smoke.py"),
                "--executable",
                str(iwencai_bin),
                "--cwd",
                str(workspace_dir),
            ],
            cwd=workspace_dir,
            env=env,
        )


if __name__ == "__main__":
    main()
