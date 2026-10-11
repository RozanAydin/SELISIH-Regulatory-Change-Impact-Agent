# tests/test_compliance.py
"""
Pengujian Unit Test Kepatuhan Regulasi Finansial.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.loan_service import LoanService
from app.core.config import MAX_LOAN_AMOUNT, MAX_DAILY_INTEREST_RATE

def test_compliant_loan_approval():
    service = LoanService()
    # Pinjaman standar Rp 10 Juta dengan bunga 0.1% harus disetujui
    result = service.validate_loan_application(
        borrower_id="CUST-001",
        requested_amount=10_000_000,
        daily_rate=0.001,
        kyc_level=2
    )
    assert result["status"] == "APPROVED"

def test_statutory_loan_limit_rejection():
    service = LoanService()
    # Mengajukan pinjaman di atas batas maksimum saat ini
    result = service.validate_loan_application(
        borrower_id="CUST-002",
        requested_amount=MAX_LOAN_AMOUNT + 5_000_000,
        daily_rate=0.001,
        kyc_level=2
    )
    assert result["status"] == "REJECTED"
    assert result["code"] == "EXCEEDS_STATUTORY_LOAN_LIMIT"

def test_daily_interest_rate_boundary():
    service = LoanService()
    # Mengajukan pinjaman dengan suku bunga melebihi batas legal
    result = service.validate_loan_application(
        borrower_id="CUST-003",
        requested_amount=5_000_000,
        daily_rate=MAX_DAILY_INTEREST_RATE + 0.001,
        kyc_level=2
    )
    assert result["status"] == "REJECTED"
    assert result["code"] == "EXCEEDS_MAX_INTEREST_RATE"

if __name__ == "__main__":
    print("Menjalankan pengujian...")
    test_compliant_loan_approval()
    test_statutory_loan_limit_rejection()
    test_daily_interest_rate_boundary()
    print("[SUCCESS] Seluruh 3 unit test kepatuhan berhasil lulus!")
