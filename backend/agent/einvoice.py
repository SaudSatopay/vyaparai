"""Indian GST e-invoice layer (NIC INV-01 schema, IRN, signed QR).

What's REAL here:
- The INV-01 v1.1 payload structure the IRP (Invoice Registration Portal) accepts.
- The IRN algorithm: SHA-256 over supplier GSTIN + financial year + doc type + doc no,
  exactly as the NIC e-invoice system computes it.
- A JWS (HS256) signed QR payload with the same fields the IRP embeds in its QR.

What's SANDBOX here:
- The JWS is self-signed with a local secret (kid: vyaparai-sandbox). Production swaps
  this for NIC's RS256 signature returned by the live IRP — the payload is identical.
- AckNo/AckDt are simulated deterministically from the IRN.

Live IRP integration (einv-apisandbox.nic.in) requires GSTIN-gated credentials; the
`register_invoice()` seam below is where that call drops in.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime

from backend.models import Quote

SANDBOX_SECRET = os.getenv("EINV_SIGNING_SECRET", "vyaparai-sandbox-secret")

# NIC UQC codes for our catalog units
_UQC = {"pcs": "PCS", "pack": "PAC", "coil": "ROL", "length": "NOS"}


def seller_details() -> dict:
    """Demo seller profile (override via env)."""
    gstin = os.getenv("SELLER_GSTIN", "29ABCDE1234F1Z5")
    return {
        "Gstin": gstin,
        "LglNm": os.getenv("SELLER_LGL_NAME", "Gupta Electrical Mart"),
        "Addr1": os.getenv("SELLER_ADDR1", "42, SP Road, Chickpet"),
        "Loc": os.getenv("SELLER_LOC", "Bengaluru"),
        "Pin": int(os.getenv("SELLER_PIN", "560002")),
        "Stcd": gstin[:2],  # state code is the GSTIN prefix
    }


def financial_year(d: datetime) -> str:
    """Indian FY runs April-March: 2026-07-10 -> '2026-27'."""
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{str(y + 1)[-2:]}"


def compute_irn(seller_gstin: str, fy: str, doc_type: str, doc_no: str) -> str:
    """IRN per the NIC e-invoice spec: SHA-256 hex of GSTIN + FY + DocType + DocNo."""
    return hashlib.sha256(f"{seller_gstin}{fy}{doc_type}{doc_no}".encode()).hexdigest()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign_jws(payload: dict, secret: str = SANDBOX_SECRET) -> str:
    """Compact JWS (HS256). Production: the IRP returns an RS256 JWS signed by NIC."""
    header = {"alg": "HS256", "typ": "JWT", "kid": "vyaparai-sandbox"}
    signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}." \
                    f"{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(sig)}"


def verify_jws(token: str, secret: str = SANDBOX_SECRET) -> dict | None:
    """Verify a sandbox JWS; returns the payload dict or None."""
    try:
        head, body, sig = token.split(".")
        expect = hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url(expect), sig):
            return None
        pad = "=" * (-len(body) % 4)
        return json.loads(base64.urlsafe_b64decode(body + pad))
    except Exception:
        return None


def build_inv01(quote: Quote, doc_no: str, when: datetime, seller: dict,
                buyer_name: str | None, buyer_gstin: str | None) -> dict:
    """Assemble the NIC INV-01 v1.1 registration payload from a computed quote."""
    intra = quote.intra_state
    pos = seller["Stcd"] if intra else (buyer_gstin[:2] if buyer_gstin else "27")
    items = []
    for i, l in enumerate(quote.lines, start=1):
        items.append({
            "SlNo": str(i),
            "PrdDesc": l.name,
            "IsServc": "N",
            "HsnCd": l.hsn,
            "Qty": l.qty,
            "Unit": _UQC.get(l.unit, "NOS"),
            "UnitPrice": l.unit_price,
            "TotAmt": l.taxable_value,
            "AssAmt": l.taxable_value,
            "GstRt": l.gst_rate,
            "CgstAmt": l.cgst,
            "SgstAmt": l.sgst,
            "IgstAmt": l.igst,
            "TotItemVal": l.line_total,
        })
    return {
        "Version": "1.1",
        "TranDtls": {
            "TaxSch": "GST",
            "SupTyp": "B2B" if buyer_gstin else "B2C",
            "RegRev": "N",
            "IgstOnIntra": "N",
        },
        "DocDtls": {"Typ": "INV", "No": doc_no, "Dt": when.strftime("%d/%m/%Y")},
        "SellerDtls": seller,
        "BuyerDtls": {
            "Gstin": buyer_gstin or "URP",  # URP = unregistered person, per spec
            "LglNm": buyer_name or "Walk-in Customer",
            "Pos": pos,
            "Addr1": "-",
            "Loc": "-",
            "Stcd": pos,
        },
        "ItemList": items,
        "ValDtls": {
            "AssVal": quote.taxable_total,
            "CgstVal": quote.total_cgst,
            "SgstVal": quote.total_sgst,
            "IgstVal": quote.total_igst,
            "TotInvVal": quote.grand_total,
        },
    }


def register_invoice(quote: Quote, doc_no: str,
                     buyer_name: str | None = None,
                     buyer_gstin: str | None = None) -> dict:
    """Register an invoice and return IRP-style artifacts.

    Sandbox implementation: computes the IRN locally with the real algorithm and
    self-signs the QR. Live IRP integration point: POST this same INV-01 payload to
    the NIC endpoint (auth + AES/RSA credential exchange) and return its response.
    """
    now = datetime.now()
    seller = seller_details()
    fy = financial_year(now)
    irn = compute_irn(seller["Gstin"], fy, "INV", doc_no)
    inv01 = build_inv01(quote, doc_no, now, seller, buyer_name, buyer_gstin)

    main_hsn = max(quote.lines, key=lambda l: l.line_total).hsn if quote.lines else ""
    qr_payload = {
        "SellerGstin": seller["Gstin"],
        "BuyerGstin": buyer_gstin or "URP",
        "DocNo": doc_no,
        "DocTyp": "INV",
        "DocDt": now.strftime("%d/%m/%Y"),
        "TotInvVal": quote.grand_total,
        "ItemCnt": len(quote.lines),
        "MainHsnCode": main_hsn,
        "Irn": irn,
        "IrnDt": now.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return {
        "irn": irn,
        "ack_no": str(int(irn[:12], 16))[:15],  # simulated, deterministic from IRN
        "ack_dt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "qr_jws": sign_jws(qr_payload),
        "inv01": inv01,
        "signed_by": "vyaparai-sandbox (production: NIC IRP RS256)",
    }
