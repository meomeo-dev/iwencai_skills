from __future__ import annotations

from tests.helpers import load_spec, repo_path


def test_required_directories_and_files_exist() -> None:
    spec = load_spec("ARCHITECTURE.SPEC.yaml")

    for path in spec["required_directories"]:
        assert repo_path(path).is_dir(), f"Missing required directory: {path}"

    for path in spec["required_files"]:
        assert repo_path(path).is_file(), f"Missing required file: {path}"


def test_architecture_declares_runtime_only_repository_mode() -> None:
    spec = load_spec("ARCHITECTURE.SPEC.yaml")
    assert spec["constraints"]["repository_mode"] == "runtime_only"
