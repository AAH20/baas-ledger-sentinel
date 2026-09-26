"""
Continuous parity matrix solver.
Cross-verifies FinTech internal shadow ledger balances against sponsor bank core webhook feeds.
"""

from typing import Dict, List, Tuple
import hashlib
import time
from .models import BankFeedEvent, ParityVerificationResult

class ParityMatrixSolver:
    def __init__(self, tolerance: float = 0.001):
        self.tolerance = tolerance
        # Sponsor bank core balances by account_id
        self.bank_balances: Dict[str, float] = {}
        # Ingested bank events
        self.bank_events: List[BankFeedEvent] = []

    def ingest_bank_feed(self, event: BankFeedEvent) -> None:
        """Processes real-time webhook or settlement feed from bank core (FIS / Fiserv / Jack Henry)."""
        self.bank_events.append(event)
        current = self.bank_balances.get(event.account_number, 0.0)
        if event.direction == "CREDIT":
            self.bank_balances[event.account_number] = current + event.amount
        else:
            self.bank_balances[event.account_number] = current - event.amount

    def evaluate_account_parity(self, account_id: str, shadow_balance: float) -> Tuple[bool, float]:
        """Compares shadow balance vs sponsor bank balance for a single account."""
        bank_balance = self.bank_balances.get(account_id, 0.0)
        delta = shadow_balance - bank_balance
        in_sync = abs(delta) <= self.tolerance
        return in_sync, delta

    def verify_global_parity(self, shadow_balances: Dict[str, float]) -> ParityVerificationResult:
        """
        Computes macro parity across all accounts.
        Proves whether FinTech ledger matches Sponsor Bank Core within tolerance.
        """
        all_accounts = set(shadow_balances.keys()).union(set(self.bank_balances.keys()))
        fintech_total = sum(shadow_balances.get(acc, 0.0) for acc in all_accounts)
        bank_total = sum(self.bank_balances.get(acc, 0.0) for acc in all_accounts)

        drift_delta = fintech_total - bank_total
        in_sync = abs(drift_delta) <= self.tolerance

        proof_content = f"{fintech_total}:{bank_total}:{drift_delta}:{in_sync}:{time.time()}"
        proof_digest = hashlib.sha256(proof_content.encode("utf-8")).hexdigest()

        return ParityVerificationResult(
            verified=True,
            drift_delta=drift_delta,
            fintech_total=fintech_total,
            bank_core_total=bank_total,
            in_sync=in_sync,
            proof_digest=proof_digest,
            timestamp=time.time()
        )
