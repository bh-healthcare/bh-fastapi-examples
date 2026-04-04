"""
FastAPI app demonstrating the chain verifier (v0.5.0).

Shows:
- LedgerSink for tamper-evident JSONL audit logging
- /admin/verify endpoint using verify_chain() programmatically
- Human and JSON verification output

Run:
    cd verifier_demo
    pip install -r requirements.txt
    uvicorn main:app --reload

Then test:
    # Generate some audit events
    curl http://localhost:8000/patients/123
    curl http://localhost:8000/patients/456

    # Verify the chain (human-readable)
    curl http://localhost:8000/admin/verify

    # Verify the chain (JSON for CI)
    curl http://localhost:8000/admin/verify?format=json
"""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException

from bh_fastapi_audit import (
    AuditConfig,
    AuditMiddleware,
    LedgerSink,
    verify_chain,
)

LEDGER_PATH = os.environ.get("AUDIT_LEDGER_PATH", "/tmp/bh-audit/verifier_demo.jsonl")

app = FastAPI(
    title="BH Audit Verifier Demo",
    description="Demonstrates chain verification with bh-fastapi-audit v0.5.0",
    version="0.5.0",
)

os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
sink = LedgerSink(LEDGER_PATH)

config = AuditConfig(
    service_name="verifier-demo",
    service_environment="dev",
    emit_mode="sync",
    excluded_paths=frozenset({"/health", "/healthz", "/ready", "/admin/verify"}),
)

app.add_middleware(AuditMiddleware, sink=sink, config=config)


def _load_events() -> list[dict[str, Any]]:
    events = []
    if not os.path.exists(LEDGER_PATH):
        return events
    with open(LEDGER_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


@app.get("/")
def root():
    return {"message": "Verifier Demo API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    if patient_id == "404":
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"patient_id": patient_id, "status": "active"}


@app.get("/admin/verify")
def admin_verify(format: str = "human"):
    """Verify the integrity of the audit chain.

    Query params:
        format: "human" (default) or "json"
    """
    events = _load_events()
    result = verify_chain(events)

    if format == "json":
        return {
            "source": LEDGER_PATH,
            "events_scanned": result.events_scanned,
            "chain_length": result.chain_length,
            "chain_gaps": result.chain_gaps,
            "hash_mismatches": result.hash_mismatches,
            "unchained_events": result.unchained_events,
            "result": result.result,
            "failures": [
                {
                    "event_index": f.event_index,
                    "event_id": f.event_id,
                    "failure_type": f.failure_type,
                    "message": f.message,
                }
                for f in result.failures
            ],
        }

    lines = [
        f"Source: {LEDGER_PATH}",
        f"Events scanned: {result.events_scanned}",
        f"Chain length: {result.chain_length}",
        f"Chain gaps: {result.chain_gaps}",
        f"Hash mismatches: {result.hash_mismatches}",
        f"Result: {result.result}",
    ]
    return {"verification": "\n".join(lines)}


@app.on_event("shutdown")
def shutdown():
    sink.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
