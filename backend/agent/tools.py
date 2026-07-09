"""Agent tools: catalog lookup, GST quoting, e-invoice generation, delivery.

These are the callable "skills" the Qwen agent orchestrates. The GST math is real;
the IRP e-invoice and WhatsApp/email delivery are stubbed with clear TODOs.
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

from backend.agent.qwen_client import QwenClient
from backend.models import Inquiry, Invoice, LineItem, ParsedItem, Quote, Status

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"
CATALOG: list[dict] = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _round2(x: float) -> float:
    return round(x + 1e-9, 2)


def parse_inquiry(raw_text: str, qwen: QwenClient | None = None) -> Inquiry:
    """Use Qwen to turn a free-text (EN/HI/Hinglish) inquiry into a structured Inquiry."""
    return (qwen or QwenClient()).extract_inquiry(raw_text)


def catalog_lookup(query: str, limit: int = 3) -> list[dict]:
    """Fuzzy-match a free-text product query against the catalog. Returns candidates."""
    q = query.lower()
    scored: list[tuple[float, dict]] = []
    for p in CATALOG:
        hay = f"{p['name']} {p.get('name_hi', '')} {' '.join(p.get('keywords', []))}".lower()
        score = difflib.SequenceMatcher(None, q, hay).ratio()
        if any(tok in hay for tok in q.split()):
            score += 0.3  # boost exact token containment
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]


def build_quote(
    quote_id: str,
    inquiry: Inquiry,
    matched: list[tuple[ParsedItem, dict]],
    intra_state: bool = True,
) -> Quote:
    """Compute a GST-correct quote. Intra-state -> CGST+SGST; inter-state -> IGST."""
    q = Quote(
        quote_id=quote_id,
        customer_name=inquiry.customer_name,
        customer_gstin=inquiry.customer_gstin,
        intra_state=intra_state,
    )
    for item, product in matched:
        taxable = _round2(item.qty * product["unit_price"])
        gst_amt = _round2(taxable * product["gst_rate"] / 100)
        line = LineItem(
            product_id=product["id"],
            name=product["name"],
            hsn=str(product["hsn"]),
            qty=item.qty,
            unit=product.get("unit", "pcs"),
            unit_price=product["unit_price"],
            gst_rate=product["gst_rate"],
            taxable_value=taxable,
        )
        if intra_state:
            line.cgst = _round2(gst_amt / 2)
            line.sgst = _round2(gst_amt / 2)
        else:
            line.igst = gst_amt
        line.line_total = _round2(taxable + gst_amt)
        q.lines.append(line)

    q.taxable_total = _round2(sum(l.taxable_value for l in q.lines))
    q.total_cgst = _round2(sum(l.cgst for l in q.lines))
    q.total_sgst = _round2(sum(l.sgst for l in q.lines))
    q.total_igst = _round2(sum(l.igst for l in q.lines))
    q.grand_total = _round2(
        q.taxable_total + q.total_cgst + q.total_sgst + q.total_igst
    )
    q.status = Status.PENDING_APPROVAL
    return q


def generate_gst_invoice(invoice_no: str, quote: Quote, seller_gstin: str) -> Invoice:
    """Build a GST invoice from an approved quote.

    TODO: integrate the IRP sandbox (einv-apisandbox.nic.in) to obtain a real IRN
    and signed QR. For now we emit a deterministic placeholder so the flow is testable.
    """
    inv = Invoice(
        invoice_no=invoice_no,
        quote=quote,
        seller_gstin=seller_gstin,
        status=Status.APPROVED,
    )
    inv.irn = "SANDBOX-" + invoice_no
    inv.qr_payload = f"{seller_gstin}|{invoice_no}|{quote.grand_total}"
    return inv


def send_quote(invoice: Invoice, channel: str = "whatsapp") -> dict:
    """Deliver the invoice. TODO: wire WhatsApp Cloud API / Twilio / SMTP."""
    return {
        "channel": channel,
        "invoice_no": invoice.invoice_no,
        "status": "sent (simulated)",
    }
