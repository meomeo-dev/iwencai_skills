# Changelog

All notable changes to this project will be documented in this file.

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
