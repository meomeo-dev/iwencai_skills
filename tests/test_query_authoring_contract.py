from __future__ import annotations

from tests.helpers import ROOT, load_spec, load_yaml, repo_path


def test_query_authoring_spec_declares_distilled_historical_evidence() -> None:
    spec = load_spec("QUERY_AUTHORING.SPEC.yaml")

    assert spec["supported_runtime_families"] == [
        "query2data",
        "comprehensive_search",
        "simtrade",
    ]
    assert (
        spec["evidence"]["provenance_status"] == "distilled_from_retired_official_skill_snapshots"
    )
    assert spec["evidence"]["historical_inputs"]
    assert spec["evidence"]["retained_observations"]


def test_query_authoring_query_forms_cover_runtime_families() -> None:
    spec = load_spec("QUERY_AUTHORING.SPEC.yaml")
    query_forms = spec["query_forms"]

    assert query_forms

    runtime_families = {item["runtime_family"] for item in query_forms.values()}
    assert runtime_families == set(spec["supported_runtime_families"])

    for name, query_form in query_forms.items():
        assert query_form["strong_examples"], f"{name} missing strong examples"
        assert query_form["canonical_shapes"], f"{name} missing canonical shapes"


def test_query_authoring_rule_targets_match_spec_query_forms() -> None:
    spec = load_spec("QUERY_AUTHORING.SPEC.yaml")
    rules = load_yaml(ROOT / "specs" / "QUERY_AUTHORING.RULE.yaml")

    valid_targets = set(spec["query_forms"])

    assert rules["based_on"] == "/specs/QUERY_AUTHORING.SPEC.yaml"
    assert rules["rules"]

    for rule in rules["rules"]:
        assert set(rule["targets"]) <= valid_targets, f"Invalid rule target in {rule['id']}"
        assert rule["guidance"], f"{rule['id']} missing guidance"


def test_query_authoring_readme_contains_required_markers() -> None:
    spec = load_spec("QUERY_AUTHORING.SPEC.yaml")
    readme = repo_path(spec["documentation_surfaces"]["readme_path"]).read_text(encoding="utf-8")

    for marker in spec["documentation_surfaces"]["readme_markers"]:
        assert marker in readme
