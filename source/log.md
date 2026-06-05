# Source Log

Append-only operational timeline for the `source/` layer.

## [2026-06-05] docs | Align source log format with LLM Wiki gist
- Simplified `source/log.md` policy in `AGENTS.md` and `source/index.md` to follow Karpathy gist: chronological append-only timeline with a consistent grep-friendly prefix.
- Replaced rigid `Files/Reason/Change/Verify/Blockers` format with `## [YYYY-MM-DD] <type> | <short title>` plus 1-3 summary bullets.

## [2026-06-05] docs | Include decision rationale in source log
- Updated `AGENTS.md` and `source/index.md` so source log entries capture not only what changed and when, but also why the decision was made.
- Reason: future readers should understand the decision context without needing chat history, while keeping the LLM Wiki-style format simple and grep-friendly.

## [2026-06-05] docs | Make source log entries pipe-separated | what: changed `AGENTS.md` and `source/index.md` examples from semicolon-separated fields to `|` separators | files: `AGENTS.md`, `source/index.md`, `source/log.md` | why: user requested using `|` for all field separators in the single-line log format | verify: docs patch applied, no secrets included

## 2026-06-05 15:23 +07 — docs: define source log entry format

- Files: `AGENTS.md`, `source/index.md`, `source/log.md`
- Reason: `source/log.md` policy said what to include but did not define exact entry shape.
- Change: Added canonical heading/body format and allowed type labels.
- Verify: `read_file source/log.md` before edit; patch/write lint passed.
- Blockers: none

## 2026-06-05 15:17 +07

- Clarified source log policy in `AGENTS.md` and `source/index.md`.
- Defined when to append: source structure, drivers, core interface/registry/rules/events, runtime config/templates/dependencies, CLI/tests/verification, or source-impacting bugs/decisions.
- Defined entry contents: timestamp, change type, related files, reason, verification/blockers.
- Added safety rule: do not log secrets/token/local keys/sensitive IPs/raw long outputs.

## 2026-06-05 14:46 +07

- Expanded `source/index.md` with a folder guide for `core/`, `drivers/`, `config/`, and `esphome_configs/`.
- Updated `AGENTS.md` to explain each source/reference layer folder.

## 2026-06-05 14:42 +07

- Initialized `source/index.md` and `source/log.md` for source-layer navigation and audit trail.
- Current baseline commit: `11a2b31 refactor: move runtime files under source`.
- Source layer contains runtime code/config under `core/`, `drivers/`, `config/`, `esphome_configs/`, plus dependency/env files.
- Verified `source/config/devices.yaml` has 17 devices before creating this log.
