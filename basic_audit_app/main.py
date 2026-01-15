"""
Basic FastAPI app demonstrating bh-fastapi-audit middleware.

This example shows how to add audit logging to a FastAPI application
using the JsonlFileSink for local development.

Run with:
    uvicorn main:app --reload

Then test:
    curl http://localhost:8000/patients/123
    curl http://localhost:8000/health
    cat audit_events.jsonl
"""

from fastapi import FastAPI, HTTPException

from bh_fastapi_audit import AuditConfig, AuditMiddleware, JsonlFileSink

app = FastAPI(
    title="BH Healthcare Example API",
    description="Demonstrates audit logging with bh-fastapi-audit",
    version="0.1.0",
)

# Configure audit logging
# In production, you'd use SQLAlchemySink with a real database
sink = JsonlFileSink("audit_events.jsonl")

config = AuditConfig(
    service_name="bh-example-api",
    service_environment="dev",
    service_version="0.1.0",
    # Health endpoints are excluded by default
)

app.add_middleware(AuditMiddleware, sink=sink, config=config)


@app.get("/")
def root():
    """Root endpoint - welcome message."""
    return {"message": "BH Healthcare Example API", "docs": "/docs"}


@app.get("/health")
def health():
    """Health check - excluded from audit logging by default."""
    return {"status": "healthy"}


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    """
    Get patient by ID.

    This endpoint generates an audit event with:
    - action.type: READ
    - resource.type: get_patient
    - http.route_template: /patients/{patient_id}

    Note: The actual patient_id value is NOT logged (PHI safety).
    """
    # Simulated patient data (in real app, fetch from database)
    if patient_id == "404":
        raise HTTPException(status_code=404, detail="Patient not found")

    return {
        "patient_id": patient_id,
        "name": "Example Patient",
        "status": "active",
    }


@app.post("/patients")
def create_patient():
    """
    Create a new patient.

    Generates an audit event with action.type: CREATE
    """
    return {"patient_id": "new-123", "created": True}


@app.put("/patients/{patient_id}")
def update_patient(patient_id: str):
    """
    Update patient data.

    Generates an audit event with action.type: UPDATE
    """
    return {"patient_id": patient_id, "updated": True}


@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: str):
    """
    Delete a patient record.

    Generates an audit event with action.type: DELETE
    """
    return {"patient_id": patient_id, "deleted": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
