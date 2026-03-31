"""
Worker / batch job demonstrating bh-audit-logger (v0.4.0).

Shows how to emit audit events from non-HTTP contexts: Lambdas,
ETL jobs, CLI tools, cron scripts — anything that isn't FastAPI.

v0.4 additions:
- audit_access_denied() for DENIED outcomes
- validate_events for runtime schema validation
- target_schema_version for schema negotiation
- owner_org_id for cross-org access detection

Run:
    python main.py
"""

from bh_audit_logger import AuditLogger, AuditLoggerConfig, LoggingSink

logger = AuditLogger(
    config=AuditLoggerConfig(
        service_name="bh-example-worker",
        service_environment="dev",
        service_version="0.4.0",
        metadata_allowlist=frozenset({"batch_id", "record_count"}),
        max_metadata_value_length=200,
        emit_failure_mode="log",
        # v0.4: Runtime validation (log_and_emit is safe for dev)
        validate_events=True,
        validation_failure_mode="log_and_emit",
        # v0.4: Explicit schema version (default is "1.1")
        target_schema_version="1.1",
    ),
    sink=LoggingSink(logger_name="bh.audit", level="INFO"),
)


def process_batch(batch_id: str, patient_ids: list[str]) -> None:
    """Simulate a batch export job that touches PHI."""
    logger.audit(
        "EXPORT",
        actor={"subject_id": "svc_nightly_export", "subject_type": "service"},
        resource={"type": "PatientExport"},
        phi_touched=True,
        data_classification="PHI",
        correlation={"request_id": f"batch-{batch_id}"},
        metadata={"batch_id": batch_id, "record_count": len(patient_ids)},
    )

    for pid in patient_ids:
        logger.audit(
            "READ",
            actor={"subject_id": "svc_nightly_export", "subject_type": "service"},
            resource={"type": "Patient", "id": pid},
            phi_touched=True,
            data_classification="PHI",
            correlation={"request_id": f"batch-{batch_id}"},
        )

    print(f"Processed batch {batch_id}: {len(patient_ids)} records")
    print(f"Stats: {logger.stats.snapshot()}")


def demonstrate_denied_outcomes() -> None:
    """Show DENIED outcomes with audit_access_denied() (v0.4)."""
    from bh_audit_logger import MemorySink

    sink = MemorySink()
    denied_logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="bh-example-worker",
            service_environment="dev",
            emit_failure_mode="log",
            target_schema_version="1.1",
        ),
        sink=sink,
    )

    denied_logger.audit_access_denied(
        "READ",
        error_type="RoleDenied",
        actor={
            "subject_id": "user_frontdesk_042",
            "subject_type": "human",
            "roles": ["front_desk"],
            "org_id": "org_overstory",
        },
        resource={"type": "Note", "id": "note_5567", "patient_id": "pat_1234"},
        phi_touched=True,
        data_classification="PHI",
    )

    denied_logger.audit_access_denied(
        "READ",
        error_type="ConsentRequired",
        error_message="Patient consent not on file for external provider",
        actor={
            "subject_id": "user_therapist_017",
            "subject_type": "human",
            "org_id": "org_partner_clinic",
            "owner_org_id": "org_overstory",
        },
        resource={"type": "Patient", "id": "pat_5678", "patient_id": "pat_5678"},
        phi_touched=True,
        data_classification="PHI",
    )

    print(f"DENIED events emitted: {len(sink)}")
    for event in sink.events:
        status = event["outcome"]["status"]
        error_type = event["outcome"].get("error_type", "N/A")
        print(f"  {status} / {error_type}")


def simulate_sink_failure() -> None:
    """Show that a broken sink doesn't crash the worker."""

    class _BrokenSink:
        def emit(self, event: dict) -> None:
            raise ConnectionError("database unavailable")

    broken_logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="bh-example-worker",
            service_environment="dev",
            emit_failure_mode="log",
        ),
        sink=_BrokenSink(),
    )

    broken_logger.audit(
        "READ",
        actor={"subject_id": "svc_test", "subject_type": "service"},
        resource={"type": "Patient"},
    )
    print(f"Sink failed gracefully. Stats: {broken_logger.stats.snapshot()}")


def simulate_validation_failure() -> None:
    """Show that a malformed pre-built event doesn't crash the worker."""
    from bh_audit_logger import MemorySink

    sink = MemorySink()
    safe_logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="bh-example-worker",
            service_environment="dev",
            emit_failure_mode="log",
        ),
        sink=sink,
    )

    safe_logger.emit({"bad": "event", "missing": "required fields"})
    print(f"Validation failure isolated. Stats: {safe_logger.stats.snapshot()}")
    print(f"  Events in sink: {len(sink)} (should be 0 — invalid event was dropped)")


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")

    print("=== Batch export example ===")
    process_batch("20260330-001", ["pat_001", "pat_002", "pat_003"])

    print()
    print("=== DENIED outcomes (v0.4) ===")
    demonstrate_denied_outcomes()

    print()
    print("=== Sink failure isolation ===")
    simulate_sink_failure()

    print()
    print("=== Validation failure isolation ===")
    simulate_validation_failure()
