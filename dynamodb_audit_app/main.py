"""
FastAPI app demonstrating bh-fastapi-audit with DynamoDBSink.

Shows DynamoDB-backed audit logging for production healthcare deployments:
- Single-table design with service#date partition key
- 3 GSIs for compliance queries (patient, actor, denials)
- TTL-based retention (~6 years for HIPAA)
- Conditional writes for idempotency
- All the same PHI safety guarantees as basic_audit_app

Requirements:
    pip install -e ../bh-fastapi-audit[dynamodb]
    pip install -r requirements.txt

Running with DynamoDB Local (recommended for development):
    docker compose up -d
    uvicorn main:app --reload

Running with real AWS DynamoDB:
    export AWS_DEFAULT_REGION=us-east-1
    uvicorn main:app --reload

Then test:
    curl http://localhost:8000/patients/123
    curl -H "X-User-Id: clinician_42" http://localhost:8000/patients/123
    curl http://localhost:8000/patients/123/notes
    curl http://localhost:8000/admin/query/patient/pat_001
    curl http://localhost:8000/admin/query/denials
"""

import os

from fastapi import FastAPI, HTTPException, Request

from bh_fastapi_audit import AuditConfig, AuditMiddleware
from bh_fastapi_audit.sinks.dynamodb import DynamoDBSink

app = FastAPI(
    title="BH Healthcare DynamoDB Example",
    description="Demonstrates DynamoDB-backed audit logging with bh-fastapi-audit",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Actor extraction
# ---------------------------------------------------------------------------


def extract_actor(request: Request) -> dict | None:
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
# Metadata
# ---------------------------------------------------------------------------


def extract_metadata(request: Request, status_code: int) -> dict | None:
    return {
        "content_type": request.headers.get("content-type"),
        "response_status_family": f"{status_code // 100}xx",
    }


# ---------------------------------------------------------------------------
# Denial callback
# ---------------------------------------------------------------------------


def classify_denial(request: Request, response: object) -> str | None:
    if "/notes" in request.url.path:
        return "RoleDenied"
    return None


# ---------------------------------------------------------------------------
# DynamoDB Sink — create_table=True for local dev with DynamoDB Local
# ---------------------------------------------------------------------------

TABLE_NAME = os.environ.get("BH_AUDIT_TABLE", "bh_audit_events")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

sink = DynamoDBSink(
    table_name=TABLE_NAME,
    region=REGION,
    ttl_days=2190,
    create_table=True,
)

config = AuditConfig(
    service_name="bh-example-api",
    service_environment="dev",
    service_version="1.0.0",
    get_actor=extract_actor,
    get_metadata=extract_metadata,
    metadata_allowlist=frozenset({"content_type", "response_status_family"}),
    include_client_ip=False,
    emit_failure_mode="log",
    emit_mode="sync",
    denied_status_codes=frozenset({401, 403}),
    get_denial_reason=classify_denial,
    validate_events=True,
    validation_failure_mode="log_and_emit",
    target_schema_version="1.1",
)

app.add_middleware(AuditMiddleware, sink=sink, config=config)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
def root():
    return {"message": "BH Healthcare DynamoDB Example", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    if patient_id == "404":
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"patient_id": patient_id, "name": "Example Patient", "status": "active"}


@app.get("/patients/{patient_id}/notes")
def get_patient_notes(patient_id: str):
    raise HTTPException(status_code=403, detail="Insufficient role for clinical notes")


@app.post("/patients")
def create_patient():
    return {"patient_id": "new-123", "created": True}


# ---------------------------------------------------------------------------
# Admin query endpoints — demonstrate GSI compliance queries
# ---------------------------------------------------------------------------


@app.get("/admin/query/patient/{patient_id}")
def query_patient_access(
    patient_id: str, start: str | None = None, end: str | None = None
):
    """Query all audit events for a specific patient (GSI1: patient_id-index)."""
    results = sink.query_by_patient(patient_id, start=start, end=end)
    return {"patient_id": patient_id, "events": len(results), "results": results}


@app.get("/admin/query/actor/{actor_id}")
def query_actor_activity(actor_id: str, start: str | None = None):
    """Query all actions by a specific user (GSI2: actor-index)."""
    results = sink.query_by_actor(actor_id, start=start)
    return {"actor_id": actor_id, "events": len(results), "results": results}


@app.get("/admin/query/denials")
def query_denials(start: str | None = None):
    """Query all DENIED outcomes (GSI3: outcome-index)."""
    results = sink.query_denials(start=start)
    return {"events": len(results), "results": results}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
