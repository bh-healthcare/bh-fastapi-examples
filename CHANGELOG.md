# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-03-28

### Changed

- **basic_audit_app/main.py** — updated for bh-fastapi-audit v0.3.0
  - Pure ASGI middleware (no more BaseHTTPMiddleware)
  - `get_metadata` callback now receives `(Request, int)` instead of `(Request, Response)`
  - `metadata_allowlist` now uses `frozenset` (frozen config)
  - `emit_mode="sync"` for demo simplicity (default is now `"queue"`)
  - Events now emit `schema_version: "1.1"`
- **worker_audit_example/main.py** — updated for bh-audit-logger v0.3.0
  - `metadata_allowlist` now uses `frozenset` (frozen config)
  - Events now emit `schema_version: "1.1"` with v1.1 FAILURE compliance
- **README.md** — updated version references, sample JSON, and emission notes
- **requirements.txt** — updated version comments for v0.3.0

## [0.2.2] - 2026-03-11

### Added

- **worker_audit_example/** — new example demonstrating `bh-audit-logger` v0.2.0
  for non-HTTP contexts (batch jobs, Lambdas, ETL, CLI tools)
  - Batch export with `phi_touched=True` and `data_classification="PHI"`
  - Per-record READ audit events with correlation IDs
  - Sink failure isolation demo (broken sink does not crash the worker)
  - Validation failure isolation demo (`emit()` with malformed event is safely dropped)
  - `logger.stats.snapshot()` for operational dashboards

### Changed

- **basic_audit_app/main.py** — rewritten for bh-fastapi-audit v0.2.2 hardening
  - Added `get_actor` callback for HIPAA-required actor identification
  - Added `get_metadata` callback with allowlisted scalar keys
  - Switched from `JsonlFileSink` to `LoggingSink` (cloud-ready stdout)
  - Configured `include_client_ip=False` (opt-in only)
  - Configured `emit_failure_mode="log"` explicitly
- **README.md** — rewritten with both examples, HIPAA compliance notes,
  production hardening documentation, and synchronous emission caveat

## [0.1.0] - 2026-01-14

### Added

- **basic_audit_app/** — initial example showing bh-fastapi-audit middleware
  with `JsonlFileSink` for local development
- README with quickstart, test commands, and expected output

[0.3.0]: https://github.com/bh-healthcare/bh-fastapi-examples/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/bh-healthcare/bh-fastapi-examples/compare/v0.1.0...v0.2.2
[0.1.0]: https://github.com/bh-healthcare/bh-fastapi-examples/releases/tag/v0.1.0
