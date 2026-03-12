"""
Basic FastAPI app demonstrating bh-fastapi-audit middleware (v0.2.2).

Shows production-hardened audit logging with HIPAA-safe defaults:
- Actor identification via get_actor callback
- Sink failure isolation (emit_failure_mode)
- Metadata allowlist with scalar enforcement
- client_ip excluded by default
- route_template always present

Run with:
    uvicorn main:app --reload

Then test:
    curl http://localhost:8000/patients/123
    curl -H "X-User-Id: clinician_42" http://localhost:8000/patients/123
    curl http://localhost:8000/patients/404
    curl http://localhost:8000/health
    cat audit_events.jsonl
"""

from fastapi import FastAPI, HTTPException, Request
from starlette.responses import Response

from bh_fastapi_audit import AuditConfig, AuditMiddleware, LoggingSink

app = FastAPI(
    title="BH Healthcare Example API",
    description="Demonstrates audit logging with bh-fastapi-audit v0.2.2",
    version="0.2.2",
)


# ---------------------------------------------------------------------------
# Actor extraction — HIPAA requires knowing WHO accessed data
# ---------------------------------------------------------------------------

def extract_actor(request: Request) -> dict | None:
    """
    Extract actor identity from the request.

    In production this would decode a JWT or session token. Here we
    simulate it with a header for demonstration purposes.
    """
    user_id = request.headers.get("x-user-id")
    if user_id:
        return {"subject_id": user_id, "subject_type": "human"}
    return None


# ---------------------------------------------------------------------------
# Safe operational metadata — only allowlisted scalar keys pass through
# ---------------------------------------------------------------------------

def extract_metadata(request: Request, response: Response) -> dict | None:
    """Return operational metadata. Non-allowlisted keys are dropped automatically."""
    return {
        "content_type": request.headers.get("content-type"),
        "response_status_family": f"{response.status_code // 100}xx",
    }


# ---------------------------------------------------------------------------
# Audit configuration — production-hardened defaults
# ---------------------------------------------------------------------------

config = AuditConfig(
    service_name="bh-example-api",
    service_environment="dev",
    service_version="0.2.2",
    get_actor=extract_actor,
    get_metadata=extract_metadata,
    metadata_allowlist={"content_type", "response_status_family"},
    include_client_ip=False,
    emit_failure_mode="log",
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
