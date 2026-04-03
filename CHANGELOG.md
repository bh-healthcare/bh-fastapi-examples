# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **dynamodb_audit_app/** — new example demonstrating `DynamoDBSink` for production
  DynamoDB-backed audit logging:
  - Single-table design with `service#date` partition key
  - Admin query endpoints showing GSI compliance queries (patient, actor, denials)
  - `docker-compose.yml` for DynamoDB Local development
  - TTL-based retention (6-year HIPAA default)
  - All the same PHI safety guarantees as `basic_audit_app`
  - `terraform/` directory with production-ready Terraform module:
    - DynamoDB table with PAY_PER_REQUEST, encryption, PITR, TTL
    - Minimal IAM policy for application write/query access
    - `terraform.tfvars.example` for configuration reference

## [0.5.1] - 2026-04-01

### Fixed

- **README.md** — added "What's new in v0.5" section documenting the
  `worker_audit_example/` migration to bh-audit-logger-examples

## [0.5.0] - 2026-04-01

### Removed

- **worker_audit_example/** — moved to the dedicated
  [bh-audit-logger-examples](https://github.com/bh-healthcare/bh-audit-logger-examples)
  repository. This repo now focuses exclusively on FastAPI middleware examples.

### Changed

- **README.md** — updated title, description, and related projects to reflect
  FastAPI-only scope. Added link to bh-audit-logger-examples for non-HTTP patterns.

## [0.4.0] - 2026-03-30

### Added

- **basic_audit_app/main.py** — new v0.4 features demonstrated:
  - `get_denial_reason` callback for custom denial classification (RoleDenied)
  - `/patients/{patient_id}/notes` endpoint returning 403 to show DENIED outcome
  - `validate_events=True` with `validation_failure_mode="log_and_emit"` for dev
  - `denied_status_codes=frozenset({401, 403})` explicit configuration
  - `target_schema_version="1.1"` explicit schema negotiation
  - `owner_org_id` in `get_actor` callback for cross-org access detection
- **worker_audit_example/main.py** — new v0.4 features demonstrated:
  - `audit_access_denied()` convenience method with RoleDenied and ConsentRequired
  - `validate_events=True` with `validation_failure_mode="log_and_emit"`
  - `target_schema_version="1.1"` explicit schema negotiation
  - `owner_org_id` in actor block for cross-org access detection

### Changed

- **basic_audit_app/main.py** — updated for bh-fastapi-audit v0.4.0
  - Version strings updated from 0.3.0 to 0.4.0
  - `AuditConfig` now includes validation, denial, and schema negotiation fields
- **worker_audit_example/main.py** — updated for bh-audit-logger v0.4.0
  - `AuditLoggerConfig` uses `target_schema_version` instead of `schema_version`
  - Version strings updated from 0.3.0 to 0.4.0
  - `[jsonschema]` extra noted in requirements.txt for validate_events support
- **README.md** — updated version references, added DENIED/validation/schema-negotiation
  documentation, updated sample JSON output
- **requirements.txt** — updated version comments for v0.4.0

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

[0.5.1]: https://github.com/bh-healthcare/bh-fastapi-examples/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/bh-healthcare/bh-fastapi-examples/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/bh-healthcare/bh-fastapi-examples/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/bh-healthcare/bh-fastapi-examples/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/bh-healthcare/bh-fastapi-examples/compare/v0.1.0...v0.2.2
[0.1.0]: https://github.com/bh-healthcare/bh-fastapi-examples/releases/tag/v0.1.0
