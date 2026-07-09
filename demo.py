"""Offline end-to-end demo of the Quote-to-Cash pipeline.

Runs WITHOUT a Qwen key: we simulate the one step that needs Qwen (parsing the
free-text inquiry) and exercise the REAL catalog-match + GST engine + e-invoice.
Amounts are INR.
"""
from backend.agent import tools
from backend.agent.orchestrator import QuoteToCashAgent
from backend.models import Inquiry, ParsedItem

raw = "bhai 50 led bulb 9w aur 10 ceiling fan ka quote bhej do"
print("Customer (Hinglish):", raw, "\n")

# --- The step the LIVE agent does with Qwen; simulated here since no key yet ---
inquiry = Inquiry(
    raw_text=raw,
    customer_name="Sharma Electricals",
    items=[ParsedItem(query="led bulb 9w", qty=50),
           ParsedItem(query="ceiling fan", qty=10)],
)
print("Parsed items (Qwen does this live):",
      [(i.query, i.qty) for i in inquiry.items], "\n")

agent = QuoteToCashAgent()
matched = [(it, tools.catalog_lookup(it.query)[0]) for it in inquiry.items]
quote = tools.build_quote("Q-DEMO", inquiry, matched, intra_state=True)

print(f"QUOTE {quote.quote_id}  ({quote.status.value})")
for l in quote.lines:
    print(f"  {l.qty:>4g} x {l.name:<28} HSN {l.hsn}  "
          f"@Rs{l.unit_price:>6.0f}  GST{l.gst_rate:>3.0f}%  "
          f"CGST {l.cgst:>8.2f}  SGST {l.sgst:>8.2f}  = Rs{l.line_total:>10.2f}")
print(f"  {'Taxable value':>41}: Rs{quote.taxable_total:>11.2f}")
print(f"  {'CGST + SGST':>41}: Rs{quote.total_cgst + quote.total_sgst:>11.2f}")
print(f"  {'GRAND TOTAL':>41}: Rs{quote.grand_total:>11.2f}\n")

# --- Human-in-the-loop approval -> GST e-invoice ---
invoice = agent.approve_and_invoice(quote)
print(f"APPROVED -> INVOICE {invoice.invoice_no}")
print(f"  IRN:        {invoice.irn}")
print(f"  QR payload: {invoice.qr_payload}")
