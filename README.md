# bh-fastapi-examples

Minimal FastAPI applications demonstrating the bh-fastapi-audit middleware and related patterns.

## Examples

### basic_audit_app

A simple FastAPI app showing audit logging with `bh-fastapi-audit`.

**Quick start:**

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Option 1: Install from local checkout (for development)
pip install -e ../bh-fastapi-audit

# Option 2: Install from GitHub (until PyPI publication)
# pip install git+https://github.com/bh-healthcare/bh-fastapi-audit.git

# Install example app dependencies
pip install -r basic_audit_app/requirements.txt

# Run the app
cd basic_audit_app
uvicorn main:app --reload
```

**Test it:**

```bash
# Make some requests
curl http://localhost:8000/
curl http://localhost:8000/patients/123
curl http://localhost:8000/health

# View audit events (written to basic_audit_app/audit_events.jsonl)
# Pretty-print the first event:
cat audit_events.jsonl | head -n 1 | python -m json.tool

# Or view all events (one per line):
cat audit_events.jsonl
```

**Expected output:**

Each request (except `/health`) generates an audit event written to `audit_events.jsonl`:

```json
{
  "schema_version": "1.0",
  "event_id": "...",
  "timestamp": "2026-01-14T22:00:00Z",
  "service": {
    "name": "bh-example-api",
    "environment": "dev",
    "version": "0.1.0"
  },
  "actor": {
    "subject_id": "unknown",
    "subject_type": "service"
  },
  "action": {
    "type": "READ",
    "data_classification": "UNKNOWN"
  },
  "resource": {
    "type": "get_patient"
  },
  "http": {
    "method": "GET",
    "route_template": "/patients/{patient_id}",
    "status_code": 200
  },
  "outcome": {
    "status": "SUCCESS"
  }
}
```

Note that:
- The route uses `{patient_id}` template, not the actual ID (PHI safety)
- Health endpoints are excluded from audit logging
- No request/response bodies are logged

## Related Projects

- [bh-fastapi-audit](https://github.com/bh-healthcare/bh-fastapi-audit) - The audit middleware
- [bh-audit-schema](https://github.com/bh-healthcare/bh-audit-schema) - The audit event schema standard

## License

Apache 2.0
