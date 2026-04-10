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


def test_mutable_state_directory_is_not_required_repo_artifact() -> None:
    spec = load_spec("ARCHITECTURE.SPEC.yaml")
    mutable_state_directory = spec["constraints"]["mutable_state_directory"]

    assert mutable_state_directory not in spec["required_directories"]
    assert mutable_state_directory.endswith(".iwencai")


def test_mutable_state_directory_is_gitignored() -> None:
    spec = load_spec("ARCHITECTURE.SPEC.yaml")
    gitignore_lines = repo_path("/.gitignore").read_text(encoding="utf-8").splitlines()

    assert f"{spec['constraints']['mutable_state_directory'].lstrip('/')}/" in gitignore_lines
