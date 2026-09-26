"""
Unit tests for baas-ledger-sentinel.
Verifies double-entry invariants, parity verification, circuit breakers, and FDIC reports.
"""

import unittest
from baas_ledger_sentinel.models import (
    DoubleEntryJournal,
    LedgerEntry,
    TransactionType,
    BankFeedEvent,
    BankCoreProvider,
)
from baas_ledger_sentinel.shadow_double_entry_engine import ShadowDoubleEntryEngine
from baas_ledger_sentinel.parity_matrix_solver import ParityMatrixSolver
from baas_ledger_sentinel.drift_circuit_breaker import DriftCircuitBreaker
from baas_ledger_sentinel.fdic_call_report_generator import FDICCallReportGenerator
from baas_ledger_sentinel.a2zsoc_parity_bridge import A2ZSOCParityBridge

class TestBaaSLedgerSentinel(unittest.TestCase):
    def setUp(self):
        self.shadow = ShadowDoubleEntryEngine()
        self.solver = ParityMatrixSolver(tolerance=0.01)
        self.breaker = DriftCircuitBreaker(drift_threshold=50.0, auto_trip_limit=1000.0)
        self.fdic = FDICCallReportGenerator(deposit_insurance_cap=250000.0)
        self.bridge = A2ZSOCParityBridge()

    def test_double_entry_invariant_success(self):
        self.shadow.initialize_account("user_a", 1000.0)
        self.shadow.initialize_account("user_b", 500.0)

        journal = DoubleEntryJournal(
            journal_id="j_001",
            transaction_type=TransactionType.TRANSFER,
            description="Test Transfer",
            debits=[LedgerEntry(entry_id="d1", account_id="user_a", amount=200.0, entry_type="DEBIT")],
            credits=[LedgerEntry(entry_id="c1", account_id="user_b", amount=200.0, entry_type="CREDIT")]
        )
        self.assertTrue(journal.is_balanced)
        j_hash = self.shadow.record_journal(journal)
        self.assertIsNotNone(j_hash)
        self.assertEqual(self.shadow.get_account_balance("user_a"), 1200.0)
        self.assertEqual(self.shadow.get_account_balance("user_b"), 300.0)

    def test_double_entry_invariant_failure(self):
        journal = DoubleEntryJournal(
            journal_id="j_unbalanced",
            transaction_type=TransactionType.TRANSFER,
            description="Unbalanced Transfer",
            debits=[LedgerEntry(entry_id="d1", account_id="acc_1", amount=100.0, entry_type="DEBIT")],
            credits=[LedgerEntry(entry_id="c1", account_id="acc_2", amount=50.0, entry_type="CREDIT")]
        )
        self.assertFalse(journal.is_balanced)
        with self.assertRaises(ValueError):
            self.shadow.record_journal(journal)

    def test_parity_evaluation_in_sync(self):
        self.shadow.initialize_account("acc_x", 5000.0)
        event = BankFeedEvent(
            event_id="evt_1",
            bank_core=BankCoreProvider.FISERV_DNA,
            account_number="acc_x",
            amount=5000.0,
            direction="CREDIT",
            core_settlement_ref="ref_123"
        )
        self.solver.ingest_bank_feed(event)
        parity = self.solver.verify_global_parity(self.shadow.accounts)
        self.assertTrue(parity.in_sync)
        self.assertAlmostEqual(parity.drift_delta, 0.0, places=2)

    def test_drift_circuit_breaker_quarantine(self):
        quarantine = self.breaker.inspect_and_quarantine(
            account_id="acc_flagged",
            drift_delta=1500.0,
            reason="Unreconciled wire drift"
        )
        self.assertIsNotNone(quarantine)
        self.assertTrue(quarantine.circuit_breaker_tripped)
        self.assertTrue(self.breaker.is_tripped)
        self.assertEqual(len(self.breaker.get_unresolved_quarantines()), 1)

    def test_fdic_part_370_report_calculation(self):
        accounts = {
            "dep_1": 150000.0,
            "dep_2": 350000.0,  # 100k uninsured
        }
        report = self.fdic.generate_part_370_report(
            sponsor_bank="Cross River Test Enclave",
            accounts=accounts,
            bank_total=500000.0,
            parity_proof_hash="hash_mock_123"
        )
        self.assertEqual(report.total_deposit_accounts, 2)
        self.assertEqual(report.total_ledger_balance, 500000.0)
        self.assertEqual(report.uninsured_deposits, 100000.0)
        self.assertEqual(report.compliance_attestation, "COMPLIANT_ZERO_DEFECT")

        # Test A2Z SOC seal
        mock_parity = self.solver.verify_global_parity(accounts)
        seal = self.bridge.anchor_parity_evidence(mock_parity, report)
        self.assertTrue(seal.startswith("a2z_parity_seal_"))

if __name__ == "__main__":
    unittest.main()
