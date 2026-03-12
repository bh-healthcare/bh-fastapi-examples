# bh-fastapi-examples

Minimal applications demonstrating **bh-fastapi-audit** (v0.2.2) and **bh-audit-logger** (v0.2.0) with production-hardened, HIPAA-safe defaults.

## Examples

### basic_audit_app — FastAPI middleware

A FastAPI app showing audit logging with `bh-fastapi-audit` v0.2.2 hardening:

- **Actor identification** via `get_actor` callback (HIPAA requires knowing *who* accessed data)
- **Sink failure isolation** — audit failures never break request handling (`emit_failure_mode="log"`)
- **Metadata allowlist** with scalar enforcement and string truncation
- **client_ip excluded** by default (opt-in with `include_client_ip=True`)
- **route_template** always present (defaults to `"unknown"` for unmatched routes)
- **LoggingSink** for stdout-based audit trails (cloud-ready)

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

# Health check — excluded from audit logging
curl http://localhost:8000/health
```

**Example audit event (stdout JSON):**

```json
{
  "schema_version": "1.0",
  "event_id": "...",
  "timestamp": "2026-03-11T12:00:00Z",
  "service": { "name": "bh-example-api", "environment": "dev", "version": "0.2.2" },
  "actor": { "subject_id": "clinician_42", "subject_type": "human" },
  "action": { "type": "READ", "data_classification": "UNKNOWN" },
  "resource": { "type": "get_patient" },
  "http": {
    "method": "GET",
    "route_template": "/patients/{patient_id}",
    "status_code": 200
  },
  "outcome": { "status": "SUCCESS" },
  "metadata": { "response_status_family": "2xx" }
}
```

Note:
- The route uses `{patient_id}` template, not the actual ID (PHI safety)
- `client_ip` is absent — excluded by default
- Only allowlisted scalar metadata keys appear
- Health endpoints are excluded from audit logging
- No request/response bodies are ever logged

---

### worker_audit_example — batch jobs and non-HTTP contexts

Demonstrates `bh-audit-logger` for workers, Lambdas, ETL jobs, CLI tools — anything that isn't FastAPI.

**Quick start:**

```bash
python -m venv .venv
source .venv/bin/activate

pip install -e ../bh-audit-logger

cd worker_audit_example
python main.py
```

This example shows:
- **Batch export** with `phi_touched=True` and `data_classification="PHI"`
- **Per-record READ** audit events with correlation IDs
- **Sink failure isolation** — a broken sink does not crash the worker
- **Stats snapshot** — `logger.stats.snapshot()` for operational dashboards

---

## HIPAA compliance notes

These examples follow the safe defaults enforced by the libraries:

| Concern | How it's addressed |
|---|---|
| **Who accessed data?** | `get_actor` callback extracts user identity from request context |
| **What was accessed?** | `resource.type` and `action.type` recorded per event |
| **No PHI in logs** | Bodies never read; route templates used instead of raw paths; error messages sanitized |
| **Metadata safety** | Allowlist-only; non-scalar values dropped; strings truncated |
| **client_ip** | Excluded by default; opt-in via `include_client_ip=True` |
| **Sink failures** | Isolated — never break application logic or mask real exceptions |

These are **safe defaults**, not a complete HIPAA compliance solution. You are responsible for proper authentication, access controls, encryption, and BAA agreements.

## Synchronous emission

Audit emission is synchronous in v0.2.x. For high-throughput systems, use `LoggingSink` (which defers I/O to your logging pipeline) or plan for async sinks in v0.3.

## Related Projects

- [bh-fastapi-audit](https://github.com/bh-healthcare/bh-fastapi-audit) — FastAPI audit middleware
- [bh-audit-logger](https://github.com/bh-healthcare/bh-audit-logger) — Cloud-agnostic audit logger
- [bh-audit-schema](https://github.com/bh-healthcare/bh-audit-schema) — The audit event schema standard

## License

Apache 2.0
