from __future__ import annotations

import argparse

import iwencai_cli
from tests.helpers import load_spec, repo_path


def _get_subparser_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise AssertionError("parser missing subparsers")


def test_top_level_commands_match_cli_ux_spec() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    parser = iwencai_cli.build_parser()
    action = _get_subparser_action(parser)

    assert parser.prog == spec["program_name"]
    assert sorted(action.choices) == sorted(
        command["name"] for command in spec["top_level_commands"]
    )


def test_query2data_command_exposes_required_cli_options() -> None:
    parser = iwencai_cli.build_parser()
    query_parser = _get_subparser_action(parser).choices["query2data"]
    option_strings = {
        option
        for action in query_parser._actions  # noqa: SLF001
        for option in action.option_strings
    }

    for option in {
        "--query",
        "--page",
        "--limit",
        "--all-pages",
        "--is-cache",
        "--format",
        "--output",
        "--api-key",
    }:
        assert option in option_strings


def test_search_command_exposes_required_cli_options() -> None:
    parser = iwencai_cli.build_parser()
    search_parser = _get_subparser_action(parser).choices["search"]
    option_strings = {
        option
        for action in search_parser._actions  # noqa: SLF001
        for option in action.option_strings
    }

    for option in {"--query", "--channel", "--limit", "--format", "--output", "--api-key"}:
        assert option in option_strings


def test_skillbook_command_exposes_required_cli_options() -> None:
    parser = iwencai_cli.build_parser()
    skillbook_parser = _get_subparser_action(parser).choices["skillbook"]
    option_strings = {
        option
        for action in skillbook_parser._actions  # noqa: SLF001
        for option in action.option_strings
    }

    for option in {"--format", "--output"}:
        assert option in option_strings


def test_trade_subcommands_match_cli_ux_spec() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    parser = iwencai_cli.build_parser()
    trade_parser = _get_subparser_action(parser).choices["trade"]
    trade_action = _get_subparser_action(trade_parser)

    expected = next(command for command in spec["top_level_commands"] if command["name"] == "trade")
    assert sorted(trade_action.choices) == sorted(expected["subcommands"])


def test_cli_ux_spec_declares_query2data_as_default_command() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    assert spec["routing"]["behavior_when_subcommand_is_omitted"] == "default_to_query2data"


def test_cli_ux_spec_search_channels_match_runtime_catalog() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    assert iwencai_cli.list_search_channels() == spec["search_channels"]


def test_cli_ux_packaging_entrypoint_matches_runtime_main() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")

    assert spec["packaging"]["console_script"] == spec["entrypoint"]
    assert spec["packaging"]["module_entrypoint"] == "iwencai_cli:main"


def test_top_level_help_contains_required_markers() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    help_text = iwencai_cli.build_parser().format_help()

    for marker in spec["help_surface"]["top_level_markers"]:
        assert marker in help_text


def test_query2data_help_contains_required_markers() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    parser = iwencai_cli.build_parser()
    query_parser = _get_subparser_action(parser).choices["query2data"]
    help_text = query_parser.format_help()

    for marker in spec["help_surface"]["query2data_markers"]:
        assert marker in help_text


def test_search_help_contains_required_markers() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    parser = iwencai_cli.build_parser()
    search_parser = _get_subparser_action(parser).choices["search"]
    help_text = search_parser.format_help()

    for marker in spec["help_surface"]["search_markers"]:
        assert marker in help_text


def test_skillbook_help_contains_required_markers() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    parser = iwencai_cli.build_parser()
    skillbook_parser = _get_subparser_action(parser).choices["skillbook"]
    help_text = skillbook_parser.format_help()

    for marker in spec["help_surface"]["skillbook_markers"]:
        assert marker in help_text


def test_trade_help_contains_required_markers() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    parser = iwencai_cli.build_parser()
    trade_parser = _get_subparser_action(parser).choices["trade"]
    help_text = trade_parser.format_help()

    for marker in spec["help_surface"]["trade_markers"]:
        assert marker in help_text


def test_trade_buy_help_contains_required_markers() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    parser = iwencai_cli.build_parser()
    trade_parser = _get_subparser_action(parser).choices["trade"]
    buy_parser = _get_subparser_action(trade_parser).choices["buy"]
    help_text = buy_parser.format_help()

    for marker in spec["help_surface"]["trade_buy_markers"]:
        assert marker in help_text


def test_readme_contains_skillbook_markers() -> None:
    spec = load_spec("CLI_UX.SPEC.yaml")
    readme = repo_path("/README.md").read_text(encoding="utf-8")

    for marker in spec["documentation_surface"]["readme_markers"]:
        assert marker in readme
