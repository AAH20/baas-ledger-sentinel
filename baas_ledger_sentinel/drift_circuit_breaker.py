"""
Drift circuit breaker and suspense account quarantine.
Automatically intercepts and quarantines ledger balance discrepancies before payout execution.
"""

from typing import List, Optional
import uuid
import time
from .models import SuspenseQuarantineRecord

class DriftCircuitBreaker:
    def __init__(self, drift_threshold: float = 100.0, auto_trip_limit: float = 5000.0):
        self.drift_threshold = drift_threshold
        self.auto_trip_limit = auto_trip_limit
        self.is_tripped = False
        self.quarantine_ledger: List[SuspenseQuarantineRecord] = []

    def inspect_and_quarantine(
        self,
        account_id: str,
        drift_delta: float,
        journal_id: Optional[str] = None,
        bank_event_id: Optional[str] = None,
        reason: str = "Parity discrepancy detected"
    ) -> Optional[SuspenseQuarantineRecord]:
        """
        Evaluates drift delta against thresholds.
        If delta exceeds threshold, logs a quarantine entry and optionally trips the circuit breaker.
        """
        if abs(drift_delta) < 1e-4:
            return None

        tripped = False
        if abs(drift_delta) >= self.auto_trip_limit:
            self.is_tripped = True
            tripped = True

        record = SuspenseQuarantineRecord(
            quarantine_id=f"quar_{uuid.uuid4().hex[:12]}",
            discrepancy_delta=drift_delta,
            journal_id=journal_id,
            bank_event_id=bank_event_id,
            reason=f"{reason} (Delta: ${drift_delta:.2f} on {account_id})",
            quarantined_at=time.time(),
            circuit_breaker_tripped=tripped,
            resolved=False
        )

        self.quarantine_ledger.append(record)
        return record

    def reset_circuit_breaker(self) -> None:
        self.is_tripped = False

    def get_unresolved_quarantines(self) -> List[SuspenseQuarantineRecord]:
        return [q for q in self.quarantine_ledger if not q.resolved]
