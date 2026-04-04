# bh-fastapi-examples

Minimal applications demonstrating **bh-fastapi-audit** (v1.0.0) with production-hardened, HIPAA-safe defaults.

For non-HTTP examples (batch jobs, Lambdas, ETL, CLI tools), see [bh-audit-logger-examples](https://github.com/bh-healthcare/bh-audit-logger-examples).

## Examples

| Example | What it demonstrates |
|---|---|
| `basic_audit_app/` | Production-hardened middleware: actor extraction, DENIED outcomes, validation, schema negotiation |
| `dynamodb_audit_app/` | DynamoDB sink with compliance query patterns, GSI queries, Docker Compose + Terraform |
| `ledger_audit_app/` | LedgerSink for tamper-evident JSONL with built-in chain hashing, `/admin/verify` endpoint |
| `verifier_demo/` | Chain integrity verification via `/admin/verify` endpoint using `verify_chain()` |
| `telemetry_demo/` | Opt-in telemetry: aggregate counters, `/admin/telemetry` showing what is tracked (no PII/PHI) |

### basic_audit_app — FastAPI middleware

A FastAPI app showing audit logging with `bh-fastapi-audit` v1.0.0:

- **Pure ASGI middleware** — no BaseHTTPMiddleware overhead, supports streaming
- **Non-blocking async emission** via bounded queue (or `emit_mode="sync"` for demos)
- **Actor identification** via `get_actor` callback (HIPAA requires knowing *who* accessed data)
- **DENIED outcomes** for 401/403 with custom `get_denial_reason` callback (v0.4)
- **Runtime schema validation** via `validate_events=True` (v0.4)
- **Schema version negotiation** via `target_schema_version` (v0.4)
- **Cross-org access detection** via `owner_org_id` in actor block (v0.4)
- **Sink failure isolation** — audit failures never break request handling (`emit_failure_mode="log"`)
- **Metadata allowlist** with scalar enforcement and string truncation
- **client_ip excluded** by default (opt-in with `include_client_ip=True`)
- **route_template** always present (defaults to `"unknown"` for unmatched routes)
- **LoggingSink** for stdout-based audit trails (cloud-ready)
- **Schema v1.1** with HIPAA/SOC compliance rules (FAILURE requires error_type + error_message)

**Quick start:**

```bash
python -m venv .venv
source .venv/bin/activate

# Install from local checkouts
pip install -e ../bh-fastapi-audit
pip install -r basic_audit_app/requirements.txt

# Run
cd basic_audit_app
uvicorn main:app --reload
```

**Test it:**

```bash
# Unauthenticated request (actor defaults to "unknown")
curl http://localhost:8000/patients/123

# Authenticated request (actor extracted from header)
curl -H "X-User-Id: clinician_42" http://localhost:8000/patients/123

# HTTPException — status code preserved in audit event (404, not 500)
curl http://localhost:8000/patients/404

# DENIED outcome — 403 with custom denial reason "RoleDenied" (v0.4)
curl http://localhost:8000/patients/123/notes

# Health check — excluded from audit logging
curl http://localhost:8000/health
```

**Example SUCCESS audit event (stdout JSON):**

```json
{
  "schema_version": "1.1",
  "event_id": "...",
  "timestamp": "2026-03-30T12:00:00.000Z",
  "service": { "name": "bh-example-api", "environment": "dev", "version": "1.0.0" },
  "actor": { "subject_id": "clinician_42", "subject_type": "human", "org_id": "sample_org_id", "owner_org_id": "sample_org_id" },
  "action": { "type": "READ", "data_classification": "UNKNOWN" },
  "resource": { "type": "get_patient" },
  "http": { "method": "GET", "route_template": "/patients/{patient_id}", "status_code": 200 },
  "outcome": { "status": "SUCCESS" },
  "metadata": { "response_status_family": "2xx" }
}
```

**Example DENIED audit event (v0.4):**

```json
{
  "schema_version": "1.1",
  "event_id": "...",
  "timestamp": "2026-03-30T12:01:00.000Z",
  "service": { "name": "bh-example-api", "environment": "dev", "version": "1.0.0" },
  "actor": { "subject_id": "clinician_42", "subject_type": "human" },
  "action": { "type": "READ", "data_classification": "UNKNOWN" },
  "resource": { "type": "get_patient_notes" },
  "http": { "method": "GET", "route_template": "/patients/{patient_id}/notes", "status_code": 403 },
  "outcome": { "status": "DENIED", "error_type": "RoleDenied" }
}
```

Note:
- The route uses `{patient_id}` template, not the actual ID (PHI safety)
- `client_ip` is absent — excluded by default
- Only allowlisted scalar metadata keys appear
- Health endpoints are excluded from audit logging
- No request/response bodies are ever logged
- DENIED events include `error_type` for compliance filtering (`WHERE outcome.status = 'DENIED'`)

---

## HIPAA compliance notes

These examples follow the safe defaults enforced by the libraries:

| Concern | How it's addressed |
|---|---|
| **Who accessed data?** | `get_actor` callback extracts user identity from request context |
| **What was accessed?** | `resource.type` and `action.type` recorded per event |
| **Access denials** | DENIED outcomes with `error_type` for compliance review (v0.4) |
| **Cross-org access** | `owner_org_id` enables detecting external provider access (v0.4) |
| **No PHI in logs** | Bodies never read; route templates used instead of raw paths; error messages sanitized |
| **Metadata safety** | Allowlist-only; non-scalar values dropped; strings truncated |
| **client_ip** | Excluded by default; opt-in via `include_client_ip=True` |
| **Sink failures** | Isolated — never break application logic or mask real exceptions |
| **Schema compliance** | Runtime validation catches malformed events before emission (v0.4) |

These are **safe defaults**, not a complete HIPAA compliance solution. You are responsible for proper authentication, access controls, encryption, and BAA agreements.

## What's new in v1.0

- **FastAPI-only scope** — `worker_audit_example/` has moved to [bh-audit-logger-examples](https://github.com/bh-healthcare/bh-audit-logger-examples). This repo now focuses exclusively on FastAPI middleware examples.

## What's new in v0.4

- **DENIED outcome** — 401/403 responses produce `outcome.status: "DENIED"` instead of `"FAILURE"`, enabling `WHERE outcome.status = 'DENIED'` queries for HIPAA access review
- **Custom denial reasons** — `get_denial_reason` callback and `audit_access_denied()` let you classify denials (RoleDenied, ConsentRequired, CrossOrgAccessDenied)
- **Runtime schema validation** — `validate_events=True` validates every event against bh-audit-schema before emission
- **Schema version negotiation** — `target_schema_version="1.0"` emits v1.0-compatible events (DENIED downgrades to FAILURE)
- **Validation timing** — `stats.snapshot()` includes `validation_time_ms_total` for performance monitoring

## Async emission (v0.3+)

The middleware defaults to `emit_mode="queue"` (10k-event bounded queue with a background drain task). For demos and testing, use `emit_mode="sync"` for deterministic ordering.

## Related Projects

- [bh-fastapi-audit](https://github.com/bh-healthcare/bh-fastapi-audit) — FastAPI audit middleware
- [bh-audit-logger](https://github.com/bh-healthcare/bh-audit-logger) — Cloud-agnostic audit logger
- [bh-audit-logger-examples](https://github.com/bh-healthcare/bh-audit-logger-examples) — Framework-agnostic audit logger examples and integration tests
- [bh-audit-schema](https://github.com/bh-healthcare/bh-audit-schema) — The audit event schema standard

## License

Apache 2.0
