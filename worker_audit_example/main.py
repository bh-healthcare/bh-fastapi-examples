"""
Worker / batch job demonstrating bh-audit-logger (v0.2.0).

Shows how to emit audit events from non-HTTP contexts: Lambdas,
ETL jobs, CLI tools, cron scripts — anything that isn't FastAPI.

Run:
    python main.py
"""

from bh_audit_logger import AuditLogger, AuditLoggerConfig, LoggingSink

logger = AuditLogger(
    config=AuditLoggerConfig(
        service_name="bh-example-worker",
        service_environment="dev",
        service_version="0.2.0",
        metadata_allowlist={"batch_id", "record_count"},
        max_metadata_value_length=200,
        emit_failure_mode="log",
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
    process_batch("20260311-001", ["pat_001", "pat_002", "pat_003"])

    print()
    print("=== Sink failure isolation ===")
    simulate_sink_failure()

    print()
    print("=== Validation failure isolation ===")
    simulate_validation_failure()
