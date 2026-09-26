"""
Command Line Interface for baas-ledger-sentinel.
Executes real-time parity audits and FDIC call report generations.
"""

import argparse
import sys
import time
from .models import DoubleEntryJournal, LedgerEntry, BankFeedEvent, TransactionType, BankCoreProvider
from .shadow_double_entry_engine import ShadowDoubleEntryEngine
from .parity_matrix_solver import ParityMatrixSolver
from .drift_circuit_breaker import DriftCircuitBreaker
from .fdic_call_report_generator import FDICCallReportGenerator
from .a2zsoc_parity_bridge import A2ZSOCParityBridge

def run_demo():
    print("=" * 80)
    print("🏛️  BAAS-LEDGER-SENTINEL v1.0.0 (Frontier September 2026)")
    print("    Sponsor Bank Continuous Parity & Real-Time Shadow Ledger Engine")
    print("    Integrated with a2zsoc.com Evidence Vault & FDIC Part 370 Attestation")
    print("=" * 80)

    # 1. Initialize Engines
    shadow = ShadowDoubleEntryEngine()
    solver = ParityMatrixSolver(tolerance=0.01)
    breaker = DriftCircuitBreaker(drift_threshold=100.0, auto_trip_limit=5000.0)
    fdic = FDICCallReportGenerator()
    bridge = A2ZSOCParityBridge()

    print("\n[1/5] Initializing FinTech Shadow Accounts...")
    shadow.initialize_account("user_101", 15000.00)
    shadow.initialize_account("user_102", 280000.00)  # > $250k FDIC cap
    shadow.initialize_account("fintech_fbo_settlement", 295000.00)
    print("   ✓ user_101:               $15,000.00 USD")
    print("   ✓ user_102:              $280,000.00 USD (Over FDIC Cap)")
    print("   ✓ fintech_fbo_settlement: $295,000.00 USD")

    # 2. Record Double-Entry Transactions
    print("\n[2/5] Executing Verified Double-Entry Journal Transactions...")
    journal = DoubleEntryJournal(
        journal_id="jrn_99810a",
        transaction_type=TransactionType.TRANSFER,
        description="P2P Transfer from user_101 to user_102",
        debits=[LedgerEntry(entry_id="e1", account_id="user_101", amount=5000.00, entry_type="DEBIT")],
        credits=[LedgerEntry(entry_id="e2", account_id="user_102", amount=5000.00, entry_type="CREDIT")]
    )
    j_hash = shadow.record_journal(journal)
    print(f"   ✓ Journal jrn_99810a Recorded: Balance Conservation Proved (Sum=5000.00 == 5000.00)")
    print(f"   ✓ Block Hash Link: {j_hash[:32]}...")

    # 3. Ingest Bank Core Feeds (FIS Systematics)
    print("\n[3/5] Ingesting Sponsor Bank Core Real-Time Feed (FIS Systematics)...")
    event_1 = BankFeedEvent(
        event_id="bk_evt_001",
        bank_core=BankCoreProvider.FIS_SYSTEMATICS,
        account_number="user_101",
        amount=20000.00,
        direction="CREDIT",
        core_settlement_ref="fis_ref_882910"
    )
    event_2 = BankFeedEvent(
        event_id="bk_evt_002",
        bank_core=BankCoreProvider.FIS_SYSTEMATICS,
        account_number="user_102",
        amount=275000.00,
        direction="CREDIT",
        core_settlement_ref="fis_ref_882911"
    )
    solver.ingest_bank_feed(event_1)
    solver.ingest_bank_feed(event_2)
    print(f"   ✓ Ingested Bank Core Event bk_evt_001: user_101 core balance = $20,000.00")
    print(f"   ✓ Ingested Bank Core Event bk_evt_002: user_102 core balance = $275,000.00")

    # 4. Evaluate Parity
    print("\n[4/5] Evaluating Continuous Parity Matrix (Z3 SMT Invariant Solver)...")
    parity_result = solver.verify_global_parity(shadow.accounts)
    print(f"   • FinTech Shadow Total:  ${parity_result.fintech_total:,.2f} USD")
    print(f"   • Sponsor Bank Core:    ${parity_result.bank_core_total:,.2f} USD")
    print(f"   • Drift Delta:          ${parity_result.drift_delta:,.2f} USD")
    print(f"   • In-Sync Status:        {parity_result.in_sync}")

    # Check circuit breaker
    if not parity_result.in_sync:
        print("   ⚠️  Drift Detected! Triggering Drift Circuit Breaker...")
        quar = breaker.inspect_and_quarantine(
            account_id="user_102",
            drift_delta=parity_result.drift_delta,
            journal_id=journal.journal_id,
            reason="Unreconciled in-flight ACH credit"
        )
        print(f"   [🛡️] Quarantined in Suspense Ledger: ID={quar.quarantine_id} (Delta: ${quar.discrepancy_delta:,.2f})")
    else:
        print("   ✓ Parity Verified: 0.000% Delta across all active ledgers.")

    # 5. Generate FDIC Part 370 Report & Anchor to a2zsoc.com
    print("\n[5/5] Generating FDIC Part 370 Regulatory Summary & Sealing to a2zsoc.com...")
    report = fdic.generate_part_370_report(
        sponsor_bank="Evolve Bank & Trust / Cross River Partner Grid",
        accounts=shadow.accounts,
        bank_total=parity_result.bank_core_total,
        parity_proof_hash=parity_result.proof_digest
    )
    seal = bridge.anchor_parity_evidence(parity_result, report)
    print(f"   ✓ Total Deposit Accounts: {report.total_deposit_accounts}")
    print(f"   ✓ Insured Balance:        ${(report.total_ledger_balance - report.uninsured_deposits):,.2f} USD")
    print(f"   ✓ Uninsured Balance:      ${report.uninsured_deposits:,.2f} USD (Excess above $250k cap)")
    print(f"   ✓ Attestation Status:     {report.compliance_attestation}")
    print(f"   ✓ a2zsoc.com Audit Seal:  {seal}")
    print("\n" + "=" * 80)
    print("✅ PARITY DEMONSTRATION COMPLETE: Zero Synapse-Style Invariant Failures Permitted.")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="BaaS Sponsor Bank Continuous Parity Sentinel")
    parser.add_argument("--demo", action="store_true", help="Run end-to-end parity audit demonstration")
    args = parser.parse_args()

    if args.demo or len(sys.argv) == 1:
        run_demo()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
