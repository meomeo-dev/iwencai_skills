from __future__ import annotations

from tests.helpers import ROOT, get_nested, load_pyproject, load_spec, load_yaml


def test_required_pyproject_sections_exist() -> None:
    spec = load_spec("QUALITY_GATES.SPEC.yaml")
    pyproject = load_pyproject()

    for dotted_path in spec["required_pyproject_sections"]:
        assert get_nested(pyproject, dotted_path) is not None


def test_dev_dependencies_match_quality_spec() -> None:
    spec = load_spec("QUALITY_GATES.SPEC.yaml")
    pyproject = load_pyproject()
    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]

    for dependency in spec["dev_dependencies"]:
        package_name = dependency.split(">=", maxsplit=1)[0]
        assert any(
            candidate == package_name or candidate.startswith(f"{package_name}>=")
            for candidate in dev_dependencies
        )


def test_required_pre_commit_hooks_exist() -> None:
    spec = load_spec("QUALITY_GATES.SPEC.yaml")
    config = load_yaml(ROOT / ".pre-commit-config.yaml")
    actual_hooks = {hook["id"] for repo in config["repos"] for hook in repo.get("hooks", [])}

    assert actual_hooks

    for hook_name in spec["required_pre_commit_hooks"]:
        assert hook_name in actual_hooks


def test_pre_commit_hook_names_match_quality_spec() -> None:
    spec = load_spec("QUALITY_GATES.SPEC.yaml")
    config = load_yaml(ROOT / ".pre-commit-config.yaml")
    actual_hooks = {hook["id"] for repo in config["repos"] for hook in repo.get("hooks", [])}

    for hook_name in spec["required_pre_commit_hooks"]:
        assert hook_name in actual_hooks


def test_release_preflight_hook_matches_quality_spec() -> None:
    spec = load_spec("QUALITY_GATES.SPEC.yaml")
    config = load_yaml(ROOT / ".pre-commit-config.yaml")
    hooks = {hook["id"]: hook for repo in config["repos"] for hook in repo.get("hooks", [])}

    hook = hooks[spec["release_preflight"]["hook_id"]]
    assert hook["entry"] == spec["release_preflight"]["hook_entry"]
    assert hook["pass_filenames"] is False


def test_secret_scan_hook_matches_quality_spec() -> None:
    spec = load_spec("QUALITY_GATES.SPEC.yaml")
    config = load_yaml(ROOT / ".pre-commit-config.yaml")

    secret_repo = next(
        repo for repo in config["repos"] if repo["repo"] == spec["secret_scan"]["hook_repo"]
    )
    assert secret_repo["rev"] == spec["secret_scan"]["hook_rev"]

    hook = next(
        hook for hook in secret_repo["hooks"] if hook["id"] == spec["secret_scan"]["hook_id"]
    )
    assert hook["args"] == ["--baseline", ".secrets.baseline"]


def test_secret_scan_baseline_exists() -> None:
    spec = load_spec("QUALITY_GATES.SPEC.yaml")
    baseline_path = ROOT / spec["secret_scan"]["baseline_file"].lstrip("/")

    assert baseline_path.is_file()
    baseline = load_yaml(baseline_path)
    assert baseline["version"]
    assert "results" in baseline


def test_contract_test_naming_matches_quality_gate_glob() -> None:
    spec = load_spec("QUALITY_GATES.SPEC.yaml")
    contract_tests = sorted((ROOT / "tests").glob("test_*_contract.py"))

    assert contract_tests, f"No files matched {spec['contract_tests_glob']}"


def test_ruff_excludes_upstream_extracted_sources() -> None:
    spec = load_spec("QUALITY_GATES.SPEC.yaml")
    pyproject = load_pyproject()
    excludes = set(pyproject["tool"]["ruff"]["exclude"])

    for path in spec["lint_exclude_paths"]:
        assert path in excludes
