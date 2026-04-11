from __future__ import annotations

from pathlib import Path

import pytest

import iwencai_cli


def test_load_skillbook_content_reads_first_available_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    skillbook_path = tmp_path / "SKILL.md"
    skillbook_path.write_text("# iWencai Official CLI\n", encoding="utf-8")
    monkeypatch.setattr(iwencai_cli, "get_skillbook_candidate_paths", lambda: [skillbook_path])

    resolved_path, content = iwencai_cli.load_skillbook_content()

    assert resolved_path == skillbook_path
    assert content == "# iWencai Official CLI\n"


def test_resolve_skillbook_path_raises_clear_error_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing_path = tmp_path / "missing" / "SKILL.md"
    monkeypatch.setattr(iwencai_cli, "get_skillbook_candidate_paths", lambda: [missing_path])

    with pytest.raises(ValueError) as exc_info:
        iwencai_cli.resolve_skillbook_path()

    assert "未找到内置技能书" in str(exc_info.value)
    assert str(missing_path) in str(exc_info.value)


def test_execute_skillbook_command_returns_unmodified_markdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    skillbook_path = tmp_path / "SKILL.md"
    skillbook_content = "---\nname: iwencai-skills\n---\n"
    skillbook_path.write_text(skillbook_content, encoding="utf-8")
    monkeypatch.setattr(iwencai_cli, "get_skillbook_candidate_paths", lambda: [skillbook_path])

    payload = iwencai_cli.execute_skillbook_command()

    assert payload["success"] is True
    assert payload["command"] == "skillbook"
    assert payload["source_path"] == str(skillbook_path)
    assert payload["content"] == skillbook_content
