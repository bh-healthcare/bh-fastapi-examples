"""
Tamper-Evident Ledger Audit Example
====================================

Demonstrates ``LedgerSink`` — a JSONL file sink with built-in SHA-256 chain
hashing.  Every audit event is written with an ``integrity`` block that links
it to the previous event, forming a tamper-evident chain.

No external infrastructure required — just a local file.

Run::

    pip install fastapi uvicorn
    pip install -e ../../bh-fastapi-audit

    uvicorn main:app --reload

Verify the chain after some requests::

    python -c "
    import json
    from bh_fastapi_audit import compute_chain_hash

    prev = None
    for i, line in enumerate(open('audit_ledger.jsonl')):
        event = json.loads(line)
        integrity = event.pop('integrity')
        recomputed = compute_chain_hash(event, prev)
        ok = recomputed['event_hash'] == integrity['event_hash']
        print(f'  event {i}: {'OK' if ok else 'TAMPERED'}')
        prev = integrity['event_hash']
    "
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request

from bh_fastapi_audit import AuditConfig, AuditMiddleware
from bh_fastapi_audit.sinks.ledger import LedgerSink

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LEDGER_PATH = Path(os.environ.get("BH_AUDIT_LEDGER", "audit_ledger.jsonl"))

sink = LedgerSink(LEDGER_PATH)

app = FastAPI(
    title="Ledger Audit Example",
    description="Tamper-evident JSONL audit logging with chain hashing",
)


def get_actor(request: Request) -> dict[str, Any] | None:
    user_id = request.headers.get("x-user-id")
    if user_id:
        return {
            "subject_id": user_id,
            "subject_type": "human",
            "org_id": "sample_org_id",
            "owner_org_id": "sample_org_id",
        }
    return None


config = AuditConfig(
    service_name="ledger-example",
    service_environment=os.environ.get("ENVIRONMENT", "dev"),
    service_version="1.0.0",
    get_actor=get_actor,
    emit_mode="sync",
)

app.add_middleware(AuditMiddleware, sink=sink, config=config)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/patients/{patient_id}")
def get_patient(patient_id: str) -> dict[str, str]:
    return {"patient_id": patient_id, "name": "Jane Doe"}


@app.post("/patients")
def create_patient() -> dict[str, str]:
    return {"patient_id": "pat_new", "status": "created"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Admin: verify the chain
# ---------------------------------------------------------------------------


@app.get("/admin/verify")
def verify_chain() -> dict[str, Any]:
    """Read back the ledger and verify every hash link."""
    from bh_fastapi_audit import compute_chain_hash

    if not LEDGER_PATH.exists():
        return {"status": "empty", "events": 0}

    import json

    events = 0
    errors: list[str] = []
    prev_hash: str | None = None

    with open(LEDGER_PATH) as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            event = json.loads(line)
            integrity = event.pop("integrity", None)
            if integrity is None:
                errors.append(f"event {i}: missing integrity block")
                continue

            recomputed = compute_chain_hash(event, prev_hash)
            if recomputed["event_hash"] != integrity["event_hash"]:
                errors.append(f"event {i}: hash mismatch")

            expected_prev = integrity.get("prev_event_hash")
            if prev_hash is not None and expected_prev != prev_hash:
                errors.append(f"event {i}: broken chain link")

            prev_hash = integrity["event_hash"]
            events += 1

    return {
        "status": "valid" if not errors else "tampered",
        "events": events,
        "errors": errors,
    }


@app.on_event("shutdown")
def shutdown() -> None:
    sink.close()
