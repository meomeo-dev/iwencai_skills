from __future__ import annotations

from tests.helpers import load_pyproject, load_spec, repo_path


def test_console_script_is_declared_in_pyproject() -> None:
    cli_spec = load_spec("CLI_UX.SPEC.yaml")
    pyproject = load_pyproject()

    scripts = pyproject["project"]["scripts"]
    assert (
        scripts[cli_spec["packaging"]["console_script"]]
        == cli_spec["packaging"]["module_entrypoint"]
    )


def test_runtime_module_is_packaged_as_single_py_module() -> None:
    pyproject = load_pyproject()
    assert pyproject["tool"]["setuptools"]["py-modules"] == ["iwencai_cli"]


def test_release_preflight_scripts_exist() -> None:
    quality_spec = load_spec("QUALITY_GATES.SPEC.yaml")
    release_preflight = quality_spec["release_preflight"]

    assert repo_path(release_preflight["smoke_script"]).is_file()
    assert repo_path(release_preflight["preflight_script"]).is_file()
