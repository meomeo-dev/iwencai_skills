# Changelog

All notable changes to this project will be documented in this file.

## [0.2.3] - 2026-04-10

### Changed

- clarify in `README.md` and `SKILL.md` that `IWENCAI_API_KEY` is obtained by signing in to `https://www.iwencai.com/skillhub`, opening any skill, and copying the key from the skill popup

## [0.2.2] - 2026-04-10

### Changed

- document how to launch the local API key config page from non-TTY environments such as Claude Code, CI, and scripts in `SKILL.md`

## [0.2.1] - 2026-04-10

### Fixed

- extend the interactive API key setup wait window to 10 minutes and surface a visible countdown on the local HTML page
- treat interactive timeout and user cancellation as friendly command outcomes instead of surfacing a Python traceback

### Changed

- clarify the timeout and retry behavior for the local API key setup flow in CLI help and README

## [0.2.0] - 2026-04-10

### Added

- automatically launch a local HTML API key setup page for interactive `query2data` and `search` runs when neither `.env` nor `IWENCAI_API_KEY` is configured
- allow the setup page to persist the pasted API key into the current working directory `.env`

### Changed

- document the interactive API key bootstrap flow in CLI help and README
- keep the runtime implementation single-file by embedding the setup page directly in `iwencai_cli.py`

## [0.1.1] - 2026-04-10

### Fixed

- stop treating runtime state directory `.iwencai/` as a required repository artifact, so clean CI checkouts pass architecture contracts
- untrack local `.plan/` artifacts from the published repository while keeping local planning workflow intact

### Security

- add `detect-secrets` to pre-commit with a tracked baseline for secret scanning before commit

## [0.1.0] - 2026-04-10

### Added

- unified family-first `iwencai` CLI
- packaged console entrypoint and release-preflight smoke test
- query authoring guidance in specs, README, and SKILL
- public GitHub publishing assets: license, CI, governance docs, and env example
