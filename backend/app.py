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
from backend.models import Invoice, Quote  # noqa: E402

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
    q = agent.draft_quote(body.text, body.intra_state, body.customer_name)
    _QUOTES[q.quote_id] = q
    return q


@app.post("/approve/{quote_id}", response_model=Invoice)
def approve(quote_id: str):
    """Step 2 (human-in-the-loop): approve a quote -> GST e-invoice."""
    q = _QUOTES.get(quote_id)
    if not q:
        raise HTTPException(404, "quote not found")
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
