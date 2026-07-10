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
_BY_ID: dict[str, dict] = {p["id"]: p for p in CATALOG}


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


def quote_from_lines(
    quote_id: str,
    lines: list[dict],
    intra_state: bool = True,
    customer_name: str | None = None,
    customer_gstin: str | None = None,
) -> Quote:
    """Compute a GST-correct quote from raw line dicts
    (name/hsn/qty/unit_price/gst_rate). Intra-state -> CGST+SGST; inter-state -> IGST."""
    q = Quote(
        quote_id=quote_id,
        customer_name=customer_name,
        customer_gstin=customer_gstin,
        intra_state=intra_state,
    )
    for d in lines:
        taxable = _round2(d["qty"] * d["unit_price"])
        gst_amt = _round2(taxable * d["gst_rate"] / 100)
        line = LineItem(
            product_id=d.get("product_id", "CUSTOM"),
            name=d["name"],
            hsn=str(d["hsn"]),
            qty=d["qty"],
            unit=d.get("unit", "pcs"),
            unit_price=d["unit_price"],
            gst_rate=d["gst_rate"],
            taxable_value=taxable,
        )
        if intra_state:
            line.cgst = _round2(gst_amt / 2)
            line.sgst = _round2(gst_amt / 2)
        else:
            line.igst = gst_amt
        line.line_total = _round2(taxable + gst_amt)
        q.lines.append(line)

        # Stock awareness: flag over-asks so the owner sees them before approving.
        prod = _BY_ID.get(line.product_id)
        if prod is not None and line.qty > float(prod.get("stock", 0)):
            q.notes.append(
                f"Stock alert: {line.name} — customer asked {line.qty:g} {line.unit}, "
                f"only {prod['stock']} in stock."
            )

    q.taxable_total = _round2(sum(l.taxable_value for l in q.lines))
    q.total_cgst = _round2(sum(l.cgst for l in q.lines))
    q.total_sgst = _round2(sum(l.sgst for l in q.lines))
    q.total_igst = _round2(sum(l.igst for l in q.lines))
    q.grand_total = _round2(q.taxable_total + q.total_cgst + q.total_sgst + q.total_igst)
    q.status = Status.PENDING_APPROVAL if q.lines else Status.NEEDS_INFO
    return q


def build_quote(
    quote_id: str,
    inquiry: Inquiry,
    matched: list[tuple[ParsedItem, dict]],
    intra_state: bool = True,
) -> Quote:
    """Deterministic quote from catalog matches (fallback path)."""
    lines = [
        {
            "product_id": p["id"],
            "name": p["name"],
            "hsn": p["hsn"],
            "qty": item.qty,
            "unit": p.get("unit", "pcs"),
            "unit_price": p["unit_price"],
            "gst_rate": p["gst_rate"],
        }
        for item, p in matched
    ]
    return quote_from_lines(
        quote_id, lines, intra_state, inquiry.customer_name, inquiry.customer_gstin
    )


def generate_gst_invoice(invoice_no: str, quote: Quote, seller_gstin: str) -> Invoice:
    """Build a GST e-invoice from an approved quote.

    Uses the einvoice layer: NIC INV-01 payload, the real IRN algorithm, and a
    sandbox-signed JWS QR (live IRP registration drops into einvoice.register_invoice).
    """
    from backend.agent import einvoice

    reg = einvoice.register_invoice(
        quote, invoice_no,
        buyer_name=quote.customer_name,
        buyer_gstin=quote.customer_gstin,
    )
    return Invoice(
        invoice_no=invoice_no,
        quote=quote,
        seller_gstin=seller_gstin,
        irn=reg["irn"],
        ack_no=reg["ack_no"],
        ack_dt=reg["ack_dt"],
        qr_jws=reg["qr_jws"],
        inv01=reg["inv01"],
        signed_by=reg["signed_by"],
        status=Status.APPROVED,
    )


def send_quote(invoice: Invoice, channel: str = "whatsapp") -> dict:
    """Deliver the invoice. TODO: wire WhatsApp Cloud API / Twilio / SMTP."""
    return {
        "channel": channel,
        "invoice_no": invoice.invoice_no,
        "status": "sent (simulated)",
    }
