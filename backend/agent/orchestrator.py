"""Quote-to-Cash agent: ties the tools into an end-to-end autopilot.

Flow: inquiry -> parse -> match -> quote -> [HUMAN APPROVAL] -> invoice -> send.
The human-in-the-loop checkpoint sits between quote generation and invoicing.
"""
from __future__ import annotations

from backend.agent import tools
from backend.agent.qwen_client import QwenClient
from backend.models import Invoice, Quote, Status


class QuoteToCashAgent:
    def __init__(self, qwen: QwenClient | None = None, seller_gstin: str = "29ABCDE1234F1Z5"):
        self.qwen = qwen or QwenClient()
        self.seller_gstin = seller_gstin
        self._seq = 1000

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq}"

    def draft_quote(self, raw_text: str, intra_state: bool = True) -> Quote:
        inquiry = tools.parse_inquiry(raw_text, self.qwen)
        matched, unresolved = [], list(inquiry.clarifications_needed)
        for item in inquiry.items:
            candidates = tools.catalog_lookup(item.query)
            if not candidates:
                unresolved.append(f"No catalog match for '{item.query}'.")
                continue
            matched.append((item, candidates[0]))

        quote = tools.build_quote(self._next_id("Q"), inquiry, matched, intra_state)
        quote.detected_language = inquiry.language.value
        quote.notes.extend(unresolved)
        if unresolved and not matched:
            quote.status = Status.NEEDS_INFO
        return quote

    def approve_and_invoice(self, quote: Quote) -> Invoice:
        """Called after a human approves the quote."""
        quote.status = Status.APPROVED
        return tools.generate_gst_invoice(self._next_id("INV"), quote, self.seller_gstin)

    def send(self, invoice: Invoice, channel: str = "whatsapp") -> dict:
        receipt = tools.send_quote(invoice, channel)
        invoice.status = Status.SENT
        return receipt
