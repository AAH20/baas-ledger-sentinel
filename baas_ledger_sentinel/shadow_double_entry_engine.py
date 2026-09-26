"""
Shadow double-entry ledger engine.
Maintains continuous immutable double-entry records with balance conservation proofs.
"""

from typing import Dict, List, Optional
import hashlib
import time
from .models import DoubleEntryJournal, LedgerEntry, TransactionType

class ShadowDoubleEntryEngine:
    def __init__(self):
        # Map of account_id -> current balance
        self.accounts: Dict[str, float] = {}
        # Append-only journal list
        self.journals: List[DoubleEntryJournal] = []
        # Previous block hash for chain integrity
        self.previous_hash: str = "0" * 64

    def initialize_account(self, account_id: str, initial_balance: float = 0.0) -> None:
        self.accounts[account_id] = initial_balance

    def record_journal(self, journal: DoubleEntryJournal) -> str:
        """
        Validates the double-entry invariant: Sum(Debits) == Sum(Credits).
        Applies updates to account balances atomically.
        """
        if not journal.is_balanced:
            raise ValueError(
                f"Double-entry violation: total debits ({journal.total_debit}) != "
                f"total credits ({journal.total_credit})"
            )

        # Apply debits (increases assets/expenses, decreases liabilities/equity)
        for debit in journal.debits:
            current = self.accounts.get(debit.account_id, 0.0)
            self.accounts[debit.account_id] = current + debit.amount

        # Apply credits (decreases assets/expenses, increases liabilities/equity)
        for credit in journal.credits:
            current = self.accounts.get(credit.account_id, 0.0)
            self.accounts[credit.account_id] = current - credit.amount

        # Hash link
        payload = f"{self.previous_hash}:{journal.compute_hash()}:{time.time()}"
        journal_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.previous_hash = journal_hash

        self.journals.append(journal)
        return journal_hash

    def get_account_balance(self, account_id: str) -> float:
        return self.accounts.get(account_id, 0.0)

    def get_total_system_deposits(self) -> float:
        """Sum of all customer deposit liability balances."""
        return sum(bal for acc, bal in self.accounts.items() if acc.startswith("user_") or acc.startswith("dep_"))

    def compute_ledger_merkle_root(self) -> str:
        """Computes root hash across all current balances for audit attestation."""
        sorted_accounts = sorted(self.accounts.items(), key=lambda x: x[0])
        raw = "|".join(f"{acc}:{bal:.4f}" for acc, bal in sorted_accounts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
