from __future__ import annotations

from tests.helpers import load_pyproject, load_spec, load_yaml, repo_path


def test_publishing_required_files_exist() -> None:
    spec = load_spec("PUBLISHING.SPEC.yaml")

    for path in spec["required_files"]:
        assert repo_path(path).is_file(), f"Missing publishing file: {path}"


def test_publishing_gitignore_patterns_exist() -> None:
    spec = load_spec("PUBLISHING.SPEC.yaml")
    gitignore_lines = repo_path("/.gitignore").read_text(encoding="utf-8").splitlines()

    for pattern in spec["required_gitignore_patterns"]:
        assert pattern in gitignore_lines, f"Missing gitignore pattern: {pattern}"


def test_publishing_readme_markers_exist() -> None:
    spec = load_spec("PUBLISHING.SPEC.yaml")
    readme = repo_path("/README.md").read_text(encoding="utf-8")

    for marker in spec["required_readme_markers"]:
        assert marker in readme, f"README missing publishing marker: {marker}"


def test_license_file_matches_spec() -> None:
    spec = load_spec("PUBLISHING.SPEC.yaml")
    license_text = repo_path(spec["license"]["file"]).read_text(encoding="utf-8")

    assert spec["license"]["title"] in license_text


def test_pyproject_contains_public_metadata() -> None:
    spec = load_spec("PUBLISHING.SPEC.yaml")
    pyproject = load_pyproject()
    project = pyproject["project"]

    for key in spec["pyproject"]["required_project_keys"]:
        assert key in project, f"Missing project metadata: {key}"

    assert project["authors"]

    for key in spec["pyproject"]["required_url_keys"]:
        assert key in project["urls"], f"Missing project URL key: {key}"
        assert project["urls"][key]

    classifiers = set(project["classifiers"])
    for classifier in spec["pyproject"]["required_classifiers"]:
        assert classifier in classifiers, f"Missing classifier: {classifier}"


def test_ci_workflow_matches_publishing_spec() -> None:
    spec = load_spec("PUBLISHING.SPEC.yaml")
    workflow = load_yaml(repo_path(spec["ci"]["workflow_path"]))

    workflow_events = workflow["on"]
    assert set(spec["ci"]["required_events"]) <= set(workflow_events)

    jobs = workflow["jobs"]
    assert jobs

    run_steps: list[str] = []
    for job in jobs.values():
        for step in job.get("steps", []):
            if "run" in step:
                run_steps.append(step["run"])

    joined_runs = "\n".join(run_steps)
    for marker in spec["ci"]["required_run_markers"]:
        assert marker in joined_runs, f"CI workflow missing run marker: {marker}"


def test_codeowners_has_default_owner_rule() -> None:
    spec = load_spec("PUBLISHING.SPEC.yaml")
    codeowners = repo_path(spec["codeowners"]["path"]).read_text(encoding="utf-8").splitlines()

    content_lines = [
        line.strip() for line in codeowners if line.strip() and not line.strip().startswith("#")
    ]
    assert content_lines, "CODEOWNERS is empty"
    assert content_lines[0].startswith(spec["codeowners"]["required_default_owner_prefix"])
