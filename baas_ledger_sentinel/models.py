"""
Data models for baas-ledger-sentinel.
Represents immutable double-entry journal items, core banking feeds, and parity verification receipts.
Uses pure standard library dataclasses for zero-dependency portability.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import time
import hashlib

class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
    FEE = "FEE"
    SETTLEMENT = "SETTLEMENT"
    ADJUSTMENT = "ADJUSTMENT"

class BankCoreProvider(str, Enum):
    FIS_SYSTEMATICS = "FIS_SYSTEMATICS"
    FISERV_DNA = "FISERV_DNA"
    JACK_HENRY_SILVERLAKE = "JACK_HENRY_SILVERLAKE"
    FEDNOW_DIRECT = "FEDNOW_DIRECT"
    MOCK_CORE = "MOCK_CORE"

@dataclass
class LedgerEntry:
    entry_id: str
    account_id: str
    amount: float
    currency: str = "USD"
    entry_type: str = "DEBIT"  # "DEBIT" or "CREDIT"
    timestamp: float = field(default_factory=time.time)

@dataclass
class DoubleEntryJournal:
    journal_id: str
    transaction_type: TransactionType
    description: str
    debits: List[LedgerEntry]
    credits: List[LedgerEntry]
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_debit(self) -> float:
        return sum(d.amount for d in self.debits)

    @property
    def total_credit(self) -> float:
        return sum(c.amount for c in self.credits)

    @property
    def is_balanced(self) -> bool:
        return abs(self.total_debit - self.total_credit) < 1e-6

    def compute_hash(self) -> str:
        payload = f"{self.journal_id}:{self.total_debit}:{self.total_credit}:{self.timestamp}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

@dataclass
class BankFeedEvent:
    event_id: str
    bank_core: BankCoreProvider
    account_number: str
    amount: float
    direction: str  # "CREDIT" or "DEBIT"
    core_settlement_ref: str
    timestamp: float = field(default_factory=time.time)
    raw_payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ParityVerificationResult:
    verified: bool
    drift_delta: float
    fintech_total: float
    bank_core_total: float
    in_sync: bool
    proof_digest: str
    timestamp: float = field(default_factory=time.time)
    a2zsoc_audit_seal: Optional[str] = None

@dataclass
class SuspenseQuarantineRecord:
    quarantine_id: str
    discrepancy_delta: float
    journal_id: Optional[str] = None
    bank_event_id: Optional[str] = None
    reason: str = ""
    quarantined_at: float = field(default_factory=time.time)
    circuit_breaker_tripped: bool = False
    resolved: bool = False

@dataclass
class FDICPart370Summary:
    report_id: str
    sponsor_bank: str
    total_deposit_accounts: int
    total_ledger_balance: float
    total_core_bank_balance: float
    uninsured_deposits: float
    parity_proof_hash: str
    generated_at: float = field(default_factory=time.time)
    compliance_attestation: str = "COMPLIANT_ZERO_DEFECT"
