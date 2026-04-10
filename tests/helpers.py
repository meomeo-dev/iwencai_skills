from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def repo_path(spec_path: str) -> Path:
    return ROOT / spec_path.lstrip("/")


def load_yaml(path: str | Path) -> Any:
    file_path = Path(path)
    return yaml.safe_load(file_path.read_text(encoding="utf-8"))


def load_spec(name: str) -> Any:
    return load_yaml(ROOT / "specs" / name)


def load_json(path: str | Path) -> Any:
    file_path = Path(path)
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_pyproject() -> Any:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def get_nested(mapping: dict[str, Any], dotted_path: str) -> Any:
    current = mapping
    for part in dotted_path.split("."):
        current = current[part]
    return current
