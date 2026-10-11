# app/services/loan_service.py
"""
Layanan Validasi & Pengajuan Pinjaman Fintech.
Memvalidasi pinjaman terhadap batas kepatuhan regulasi OJK.
"""

from app.core.config import MAX_LOAN_AMOUNT, MAX_DAILY_INTEREST_RATE, MIN_KYC_LEVEL

class LoanService:
    def __init__(self):
        self.max_loan = MAX_LOAN_AMOUNT
        self.max_rate = MAX_DAILY_INTEREST_RATE

    def validate_loan_application(self, borrower_id: str, requested_amount: float, daily_rate: float, kyc_level: int) -> dict:
        """
        Validasi kepatuhan hukum sebelum pinjaman disetujui.
        """
        if kyc_level < MIN_KYC_LEVEL:
            return {
                "status": "REJECTED",
                "code": "KYC_INSUFFICIENT",
                "message": f"KYC level {kyc_level} berada di bawah syarat minimum {MIN_KYC_LEVEL}"
            }

        # Validasi batas plafon pinjaman sesuai regulasi
        if requested_amount > self.max_loan:
            return {
                "status": "REJECTED",
                "code": "EXCEEDS_STATUTORY_LOAN_LIMIT",
                "message": f"Pinjaman Rp {requested_amount:,.0f} melebihi batas legal maksimum Rp {self.max_loan:,.0f}"
            }

        # Validasi batas suku bunga harian
        if daily_rate > self.max_rate:
            return {
                "status": "REJECTED",
                "code": "EXCEEDS_MAX_INTEREST_RATE",
                "message": f"Suku bunga {daily_rate*100:.2f}% per hari melebihi batas legal {self.max_rate*100:.2f}%"
            }

        return {
            "status": "APPROVED",
            "code": "COMPLIANCE_VERIFIED",
            "borrower_id": borrower_id,
            "approved_amount": requested_amount,
            "daily_rate": daily_rate,
            "message": "Pinjaman memenuhi seluruh persyaratan regulasi yang berlaku."
        }
