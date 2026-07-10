"""FastAPI surface for the Quote-to-Cash Autopilot.

Run: uvicorn backend.app:app --reload   (then open http://localhost:8000/)
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load .env before importing the agent (QwenClient reads QWEN_* at import time).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import io  # noqa: E402

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from backend.agent.orchestrator import QuoteToCashAgent  # noqa: E402
from backend.invoice_page import render_invoice_html  # noqa: E402
from backend.models import Invoice, Quote, Status  # noqa: E402

app = FastAPI(title="VyaparAI - Quote-to-Cash Autopilot", version="0.1.0")
agent = QuoteToCashAgent()

_INDEX = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

# In-memory stores for the scaffold; swap for a DB (Alibaba Cloud RDS) later.
_QUOTES: dict[str, Quote] = {}
_INVOICES: dict[str, Invoice] = {}


class InquiryIn(BaseModel):
    text: str
    intra_state: bool = True
    customer_name: str | None = None
    history: list[str] | None = None  # rolling chat context for follow-ups


class ReviseIn(BaseModel):
    instruction: str


@app.get("/health")
def health():
    return {"ok": True, "qwen": bool(agent.qwen.api_key)}


@app.get("/")
def index():
    """Serve the human-in-the-loop review UI."""
    return FileResponse(_INDEX)


@app.post("/inquiry", response_model=Quote)
def inquiry(body: InquiryIn):
    """Step 1: customer inquiry -> draft quote (pending human approval)."""
    q = agent.draft_quote(body.text, body.intra_state, body.customer_name, body.history)
    _QUOTES[q.quote_id] = q
    return q


@app.post("/revise/{quote_id}", response_model=Quote)
def revise(quote_id: str, body: ReviseIn):
    """Owner's change request ("bulb 40 kar do, 10% discount") -> revised quote."""
    q = _QUOTES.get(quote_id)
    if not q:
        raise HTTPException(404, "quote not found")
    new_q = agent.revise(q, body.instruction)
    _QUOTES[quote_id] = new_q
    return new_q


@app.post("/approve/{quote_id}", response_model=Invoice)
def approve(quote_id: str):
    """Step 2 (human-in-the-loop): approve a quote -> GST e-invoice."""
    q = _QUOTES.get(quote_id)
    if not q:
        raise HTTPException(404, "quote not found")
    if not q.lines:
        raise HTTPException(400, "quote has no line items — answer the agent's question first")
    inv = agent.approve_and_invoice(q)
    _INVOICES[inv.invoice_no] = inv
    return inv


@app.post("/send/{invoice_no}")
def send(invoice_no: str, channel: str = "whatsapp"):
    """Step 3: deliver the invoice (WhatsApp / email)."""
    inv = _INVOICES.get(invoice_no)
    if not inv:
        raise HTTPException(404, "invoice not found")
    return agent.send(inv, channel)


def _get_invoice(invoice_no: str) -> Invoice:
    inv = _INVOICES.get(invoice_no)
    if not inv:
        raise HTTPException(404, "invoice not found")
    return inv


@app.post("/paid/{invoice_no}")
def mark_paid(invoice_no: str):
    """Close the loop: record the UPI payment against the invoice."""
    from datetime import datetime

    inv = _get_invoice(invoice_no)
    inv.paid = True
    inv.paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"ok": True, "invoice_no": invoice_no, "amount": inv.quote.grand_total}


@app.get("/stats")
def stats():
    """Business pulse for the ledger strip: counts, collections, GST, recents."""
    invs = list(_INVOICES.values())
    paid = [i for i in invs if i.paid]
    return {
        "quotes": len(_QUOTES),
        "invoices": len(invs),
        "pending": sum(1 for q in _QUOTES.values() if q.status == Status.PENDING_APPROVAL),
        "collected": round(sum(i.quote.grand_total for i in paid), 2),
        "gst_collected": round(
            sum(i.quote.total_cgst + i.quote.total_sgst + i.quote.total_igst for i in paid), 2
        ),
        "recent": [
            {"id": i.invoice_no, "total": i.quote.grand_total, "paid": i.paid}
            for i in invs
        ][-6:][::-1],
    }


@app.get("/invoice/{invoice_no}", response_class=HTMLResponse)
def invoice_page(invoice_no: str):
    """Printable GST tax invoice (browser print -> PDF)."""
    return render_invoice_html(_get_invoice(invoice_no))


@app.get("/invoice/{invoice_no}/qr.svg")
def invoice_qr(invoice_no: str):
    """Scannable QR carrying the signed (JWS) e-invoice payload."""
    inv = _get_invoice(invoice_no)
    import segno

    buf = io.BytesIO()
    segno.make(inv.qr_jws or inv.invoice_no, error="m").save(
        buf, kind="svg", xmldecl=False, scale=3, border=1, dark="#211C15", light=None
    )
    return Response(buf.getvalue(), media_type="image/svg+xml")


@app.get("/invoice/{invoice_no}/inv01.json")
def invoice_inv01(invoice_no: str):
    """The raw NIC INV-01 v1.1 registration payload (what the IRP accepts)."""
    return JSONResponse(_get_invoice(invoice_no).inv01)


@app.get("/invoice/{invoice_no}/upi.svg")
def invoice_upi(invoice_no: str):
    """Scan-to-pay UPI QR — opens any UPI app with the invoice amount pre-filled."""
    from urllib.parse import quote as urlquote

    import segno

    from backend.agent.einvoice import seller_details

    inv = _get_invoice(invoice_no)
    upi = (
        "upi://pay?pa=vyaparai@upi"
        f"&pn={urlquote(seller_details()['LglNm'])}"
        f"&am={inv.quote.grand_total:.2f}&cu=INR&tn={urlquote(invoice_no)}"
    )
    buf = io.BytesIO()
    segno.make(upi, error="m").save(
        buf, kind="svg", xmldecl=False, scale=4, border=1, dark="#0B5C52", light=None
    )
    return Response(buf.getvalue(), media_type="image/svg+xml")


@app.get("/invoice/{invoice_no}/verify")
def invoice_verify(invoice_no: str):
    """Verify the e-invoice QR's JWS signature and return the decoded payload."""
    from backend.agent import einvoice

    inv = _get_invoice(invoice_no)
    payload = einvoice.verify_jws(inv.qr_jws or "")
    return {"valid": payload is not None, "signed_by": inv.signed_by, "payload": payload}
