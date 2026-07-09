"""Quote-to-Cash agent: ties the tools into an end-to-end autopilot.

Flow: inquiry -> (Qwen tool-calling agent) -> quote -> [HUMAN APPROVAL] -> invoice -> send.
The human-in-the-loop checkpoint sits between quote generation and invoicing.
"""
from __future__ import annotations

from backend.agent import tools
from backend.agent.agent_loop import run_agent
from backend.agent.qwen_client import QwenClient, _detect_lang
from backend.models import Invoice, Quote, Status


class QuoteToCashAgent:
    def __init__(self, qwen: QwenClient | None = None, seller_gstin: str = "29ABCDE1234F1Z5"):
        self.qwen = qwen or QwenClient()
        self.seller_gstin = seller_gstin
        self._seq = 1000

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq}"

    def draft_quote(self, raw_text: str, intra_state: bool = True,
                    customer_name: str | None = None) -> Quote:
        # Primary path: a genuine Qwen tool-calling agent.
        if self.qwen.api_key:
            try:
                return self._agentic_quote(raw_text, intra_state, customer_name)
            except Exception as e:
                # Never fail the request: fall back to the deterministic pipeline.
                quote = self._deterministic_quote(raw_text, intra_state)
                quote.notes.append(
                    f"Agent loop fell back to single-shot parse ({type(e).__name__})."
                )
                return quote
        quote = self._deterministic_quote(raw_text, intra_state)
        if customer_name and not quote.customer_name:
            quote.customer_name = customer_name
        return quote

    def _agentic_quote(self, raw_text: str, intra_state: bool,
                       customer_name: str | None = None) -> Quote:
        working, clarifications, intra, trace = run_agent(raw_text, self.qwen, intra_state)
        quote = tools.quote_from_lines(
            self._next_id("Q"), working, intra, customer_name=customer_name
        )
        quote.detected_language = _detect_lang(raw_text).value
        quote.agent_trace = trace
        quote.notes.extend(clarifications)
        if not working:
            quote.status = Status.NEEDS_INFO
        return quote

    def _deterministic_quote(self, raw_text: str, intra_state: bool) -> Quote:
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
