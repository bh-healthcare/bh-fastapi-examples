"""
Basic FastAPI app demonstrating bh-fastapi-audit middleware (v0.4.0).

Shows production-hardened audit logging with HIPAA-safe defaults:
- Pure ASGI middleware (no BaseHTTPMiddleware overhead)
- Non-blocking async emission via bounded queue
- Actor identification via get_actor callback
- Sink failure isolation (emit_failure_mode)
- Metadata allowlist with scalar enforcement
- client_ip excluded by default
- route_template always present
- Schema v1.1 with FAILURE compliance (error_type + error_message required)
- DENIED outcome for 401/403 with custom denial reason callback (v0.4)
- Opt-in runtime schema validation (v0.4)
- Schema version negotiation (v0.4)

Run with:
    uvicorn main:app --reload

Then test:
    curl http://localhost:8000/patients/123
    curl -H "X-User-Id: clinician_42" http://localhost:8000/patients/123
    curl http://localhost:8000/patients/404
    curl http://localhost:8000/patients/123/notes
    curl -H "X-User-Id: clinician_42" http://localhost:8000/patients/123/notes
    curl http://localhost:8000/health
"""

from fastapi import FastAPI, HTTPException, Request

from bh_fastapi_audit import AuditConfig, AuditMiddleware, LoggingSink

# Alternative: tamper-evident JSONL with chain hashing (v0.5)
# from bh_fastapi_audit import LedgerSink
# sink = LedgerSink("audit_ledger.jsonl")  # drop-in replacement for LoggingSink

app = FastAPI(
    title="BH Healthcare Example API",
    description="Demonstrates audit logging with bh-fastapi-audit v0.4.0",
    version="0.4.0",
)


# ---------------------------------------------------------------------------
# Actor extraction — HIPAA requires knowing WHO accessed data
# ---------------------------------------------------------------------------


def extract_actor(request: Request) -> dict | None:
    """
    Extract actor identity from the request.

    In production this would decode a JWT or session token. Here we
    simulate it with a header for demonstration purposes.

    v0.4: Includes owner_org_id for cross-org access detection.
    """
    user_id = request.headers.get("x-user-id")
    if user_id:
        return {
            "subject_id": user_id,
            "subject_type": "human",
            "org_id": "sample_org_id",
            "owner_org_id": "sample_org_id",
        }
    return None


# ---------------------------------------------------------------------------
# Safe operational metadata — only allowlisted scalar keys pass through
# ---------------------------------------------------------------------------


def extract_metadata(request: Request, status_code: int) -> dict | None:
    """Return operational metadata. Non-allowlisted keys are dropped automatically.

    v0.3+ callback signature: (Request, int) — the int is the HTTP status code.
    """
    return {
        "content_type": request.headers.get("content-type"),
        "response_status_family": f"{status_code // 100}xx",
    }


# ---------------------------------------------------------------------------
# Denial reason callback — classify WHY access was denied (v0.4)
# ---------------------------------------------------------------------------


def classify_denial(request: Request, response: object) -> str | None:
    """Return a specific denial reason based on app context.

    Returns None to use the default error_type from the exception class.
    In production, this would check request.state or JWT claims.
    """
    if "/notes" in request.url.path:
        return "RoleDenied"
    return None


# ---------------------------------------------------------------------------
# Audit configuration — production-hardened defaults
# ---------------------------------------------------------------------------

config = AuditConfig(
    service_name="bh-example-api",
    service_environment="dev",
    service_version="0.5.0",
    get_actor=extract_actor,
    get_metadata=extract_metadata,
    metadata_allowlist=frozenset({"content_type", "response_status_family"}),
    include_client_ip=False,
    emit_failure_mode="log",
    emit_mode="sync",
    # v0.4: DENIED outcomes for 401/403 with custom denial reasons
    denied_status_codes=frozenset({401, 403}),
    get_denial_reason=classify_denial,
    # v0.4: Runtime schema validation (log_and_emit is safe for dev)
    validate_events=True,
    validation_failure_mode="log_and_emit",
    # v0.4: Schema version negotiation (default "1.1")
    target_schema_version="1.1",
    # v0.5: Opt-in telemetry — uncomment to enable aggregate usage reporting
    # telemetry_enabled=True,
    # telemetry_endpoint="https://telemetry.bh-healthcare.org/v1/report",
    # telemetry_deployment_id_path="/tmp/bh-audit/",
)

sink = LoggingSink(logger_name="bh.audit", level="INFO")

app.add_middleware(AuditMiddleware, sink=sink, config=config)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "BH Healthcare Example API", "docs": "/docs"}


@app.get("/health")
def health():
    """Health check — excluded from audit logging by default."""
    return {"status": "healthy"}


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    """
    Get patient by ID.

    Audit event will show:
    - action.type: READ
    - resource.type: get_patient
    - http.route_template: /patients/{patient_id}  (NOT the real ID)
    - actor: from X-User-Id header (or default "unknown")
    """
    if patient_id == "404":
        raise HTTPException(status_code=404, detail="Patient not found")

    return {
        "patient_id": patient_id,
        "name": "Example Patient",
        "status": "active",
    }


@app.get("/patients/{patient_id}/notes")
def get_patient_notes(patient_id: str):
    """
    Get patient notes — requires authorization.

    Always returns 403 to demonstrate DENIED outcome.
    The get_denial_reason callback classifies this as "RoleDenied".

    v0.4: Produces outcome.status = "DENIED" with error_type = "RoleDenied"
    instead of the generic "FAILURE" from prior versions.
    """
    raise HTTPException(status_code=403, detail="Insufficient role for clinical notes")


@app.post("/patients")
def create_patient():
    """Create a new patient. Generates a CREATE audit event."""
    return {"patient_id": "new-123", "created": True}


@app.put("/patients/{patient_id}")
def update_patient(patient_id: str):
    """Update patient data. Generates an UPDATE audit event."""
    return {"patient_id": patient_id, "updated": True}


@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: str):
    """Delete a patient record. Generates a DELETE audit event."""
    return {"patient_id": patient_id, "deleted": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
