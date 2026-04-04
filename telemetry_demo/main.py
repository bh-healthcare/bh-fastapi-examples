"""
FastAPI app demonstrating opt-in telemetry.

Shows:
- Enabling telemetry via AuditConfig
- Aggregate counter accumulation (no PII/PHI)
- /admin/telemetry endpoint showing current counters

Note: Uses a mock endpoint. In production, telemetry reports are POSTed
weekly to the configured telemetry_endpoint.

Run:
    cd telemetry_demo
    pip install -r requirements.txt
    uvicorn main:app --reload

Then test:
    # Generate some audit events
    curl http://localhost:8000/patients/123
    curl http://localhost:8000/patients/456
    curl -X POST http://localhost:8000/patients

    # View telemetry counters
    curl http://localhost:8000/admin/telemetry
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from starlette.types import ASGIApp

from bh_fastapi_audit import AuditConfig, AuditMiddleware, LoggingSink

TELEMETRY_ID_PATH = os.environ.get("TELEMETRY_ID_PATH", "/tmp/bh-audit-telemetry-demo/")

config = AuditConfig(
    service_name="telemetry-demo",
    service_environment="dev",
    emit_mode="sync",
    excluded_paths=frozenset({"/health", "/healthz", "/ready", "/admin/telemetry"}),
    telemetry_enabled=True,
    telemetry_endpoint="https://example.com/telemetry",
    telemetry_deployment_id_path=TELEMETRY_ID_PATH,
)

sink = LoggingSink(logger_name="bh.audit", level="INFO")

_audit_middleware: AuditMiddleware | None = None


class _CapturingAuditMiddleware(AuditMiddleware):
    """Thin wrapper that stores a module-level reference for the admin endpoint."""

    def __init__(self, app: ASGIApp, **kwargs):  # type: ignore[override]
        super().__init__(app, **kwargs)
        global _audit_middleware  # noqa: PLW0603
        _audit_middleware = self


app = FastAPI(
    title="BH Audit Telemetry Demo",
    description="Demonstrates opt-in telemetry with bh-fastapi-audit",
    version="1.0.0",
)

app.add_middleware(_CapturingAuditMiddleware, sink=sink, config=config)


@app.get("/")
def root():
    return {"message": "Telemetry Demo API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    if patient_id == "404":
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"patient_id": patient_id, "status": "active"}


@app.post("/patients")
def create_patient():
    return {"patient_id": "new-123", "created": True}


@app.put("/patients/{patient_id}")
def update_patient(patient_id: str):
    return {"patient_id": patient_id, "updated": True}


@app.get("/admin/telemetry")
def admin_telemetry():
    """Show current telemetry counters (for demonstration only).

    In production, counters are POSTed to the telemetry endpoint weekly.
    This admin endpoint exists only for this demo.
    """
    if _audit_middleware is None or _audit_middleware._telemetry is None:
        return {"error": "Telemetry is not enabled"}

    counters = _audit_middleware._telemetry.counters
    return {
        "telemetry_enabled": True,
        "deployment_id_path": TELEMETRY_ID_PATH,
        "counters": {
            "events_emitted": counters.events_emitted,
            "by_action_type": dict(counters.by_action_type),
            "by_outcome": dict(counters.by_outcome),
            "by_data_classification": dict(counters.by_data_classification),
            "integrity_events": counters.integrity_events,
            "chain_gaps": counters.chain_gaps,
            "emit_failures": counters.emit_failures,
        },
        "privacy_note": (
            "These counters contain NO patient IDs, NO user IDs, "
            "NO event content, NO IP addresses. Only aggregate counts."
        ),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
