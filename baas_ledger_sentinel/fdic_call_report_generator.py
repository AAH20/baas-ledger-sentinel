"""
FDIC Part 370 / OCC regulatory exam call report generator.
Generates institutional deposit recordkeeping summaries with cryptographic ledger proofs.
"""

from typing import Dict
import uuid
import time
from .models import FDICPart370Summary

class FDICCallReportGenerator:
    def __init__(self, deposit_insurance_cap: float = 250000.0):
        self.insurance_cap = deposit_insurance_cap

    def generate_part_370_report(
        self,
        sponsor_bank: str,
        accounts: Dict[str, float],
        bank_total: float,
        parity_proof_hash: str
    ) -> FDICPart370Summary:
        """
        Analyzes user deposit balances against FDIC insurance caps.
        Calculates total insured vs uninsured deposits.
        """
        deposit_accounts = {k: v for k, v in accounts.items() if v > 0}
        total_ledger = sum(deposit_accounts.values())

        uninsured_total = sum(
            max(0.0, bal - self.insurance_cap)
            for bal in deposit_accounts.values()
        )

        return FDICPart370Summary(
            report_id=f"fdic370_{uuid.uuid4().hex[:12]}",
            sponsor_bank=sponsor_bank,
            total_deposit_accounts=len(deposit_accounts),
            total_ledger_balance=round(total_ledger, 2),
            total_core_bank_balance=round(bank_total, 2),
            uninsured_deposits=round(uninsured_total, 2),
            parity_proof_hash=parity_proof_hash,
            generated_at=time.time(),
            compliance_attestation="COMPLIANT_ZERO_DEFECT" if abs(total_ledger - bank_total) < 0.01 else "EXAMINATION_FLAG_DISCREPANCY"
        )
