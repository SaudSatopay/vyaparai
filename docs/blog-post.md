# Building VyaparAI: an autonomous Qwen agent that quotes and GST-invoices for Bharat's MSMEs — in Hinglish

*Submitted for the Global AI Hackathon Series with Qwen Cloud — Autopilot Agent track.*
*Live demo: http://47.84.111.3:8000 · Code: https://github.com/SaudSatopay/vyaparai (MIT)*

## The problem hiding in 60 million WhatsApp chats

India has more than 60 million MSMEs — the electrical trader, the furniture shop, the
hardware distributor. Almost all of them sell over **WhatsApp**, and almost none of
them have a back office. A typical order looks like this:

> *"bhai 50 LED bulb 9W aur 10 ceiling fan ka quote bhej do"*

Behind that one casual message is real work: understand the mixed Hindi-English, find
each product, look up the right **HSN code**, apply the correct **GST rate**, split it
into **CGST/SGST** (or **IGST** for another state), total it, and raise a compliant
invoice. Do that fifty times a day, by hand, and mistakes — and lost hours — are
guaranteed.

**VyaparAI** is an autonomous agent that runs this entire *quote-to-cash* workflow, in
whatever language the customer types, with the owner approving before anything is sent.

## What it does

1. A customer message arrives (WhatsApp/email) in English, Hindi, or Hinglish.
2. A **Qwen function-calling agent** turns it into a GST-ready quote.
3. The owner **reviews and approves** — the human-in-the-loop checkpoint.
4. VyaparAI issues a **GST e-invoice** (invoice number, IRN, QR) and sends it back on
   WhatsApp with a UPI payment line.

## The agent is a real agent

The interesting part isn't a single prompt — it's a genuine tool-calling loop built on
Qwen Cloud (`qwen-plus`, via the OpenAI-compatible API). The agent has five tools:

- `search_catalog` — find products in the seller's catalog
- `classify_hsn` — classify an **off-catalog** item to its HSN code + GST rate
- `add_line_item` — add a confirmed line to the quote
- `request_clarification` — ask about anything genuinely ambiguous
- `finalize_quote` — trigger GST computation

The model decides which tools to call and in what order. Here's a real trace from the
demo, when we asked for *"20 LED bulb, 5 ceiling fan, aur 3 solar panel 100W"*:

```
🔍 search_catalog  "LED bulb 9W"      → LED Bulb 9W · HSN 8539 · 12%
🔍 search_catalog  "ceiling fan"      → Ceiling Fan 1200mm · HSN 8414 · 18%
🔍 search_catalog  "solar panel 100W" → (bad match: insulation tape)
➕ add_line_item   20 × LED Bulb 9W
➕ add_line_item   5 × Ceiling Fan
🏷️  classify_hsn   "solar panel 100W" → HSN 8541 · 5%
➕ add_line_item   3 × solar photovoltaic panel
✅ finalize_quote  → 3 line items
```

Look at the fifth step. The catalog had no solar panel, so the fuzzy search returned
something wrong (insulation tape). **The agent recognized the mismatch and called
`classify_hsn` on its own** — landing on **HSN 8541 at 5% GST**, which is exactly how
solar panels are treated under Indian GST. That's not hardcoded; it's the model using a
tool because the situation called for it. We surface the whole trace in the UI so the
owner (and the judges) can see the agent think.

## Getting GST right

LLMs are great at understanding and classification, and unreliable at arithmetic — so
we split the work. The agent produces structured line items; a **deterministic GST
engine** does the money:

- per-item taxable value and GST amount,
- **CGST + SGST** for intra-state sales, **IGST** for inter-state,
- an HSN-wise breakup and a correct grand total.

For *"50 LED bulbs + 10 ceiling fans"* that's ₹18,750 taxable + ₹1,560 CGST + ₹1,560
SGST = **₹21,870**, to the rupee, every time.

## The e-invoice is a real document

Approval doesn't produce a toast — it produces a **GST e-invoice built to the standard**:
the NIC **INV-01 v1.1** registration payload, an **IRN** computed with the exact NIC
SHA-256 algorithm (GSTIN + financial year + doc type + doc number), and a **JWS-signed
QR**. Click the QR in the app and it expands to phone-scannable size and **verifies its
own signature in-app**. Next to it sits a **UPI scan-to-pay QR** — point GPay or PhonePe
at it and the invoice amount arrives pre-filled. A printable tax invoice (HSN table,
CGST/SGST columns, amount-in-words in the lakh/crore system) is one click away.

## The owner stays in charge — conversationally

The human-in-the-loop checkpoint isn't just an approve button. The owner can **ask for
changes in natural language** — *"bulb 40 kar do, fan hata do, 2 geyser add karo"* or
*"reduce the bulbs to 20 and give 5% discount"* — and the agent rewrites the quote with
exact math, bumping it to revision 2 with the change logged in the trace. Orders can be
**spoken** (speech recognition in `hi-IN` or `en-IN`), and the agent **reads the quote
back aloud** in the inquiry's language. Over-asks get flagged against stock — *"asked
500, only 420 in stock"* — before anything is approved. **Mark paid** on UPI receipt
and a live ledger strip tracks quotes, invoices, collections, and GST for the day.

## WhatsApp-native, and bilingual by default

The UI is a WhatsApp-style review desk, because that's where Indian commerce actually
happens — not a dashboard. Qwen's multilingual strength means the same agent handles
pure English, Devanagari Hindi, and code-mixed Hinglish without special-casing. The app
detects and labels the language on every quote.

## Built on Qwen Cloud + Alibaba Cloud

- **Qwen Cloud (`qwen-plus`)** — the agent, the classifier, the reviser, the translator.
- **Alibaba Cloud** — live on an ECS instance in Singapore (systemd service; the
  Function Compute path is documented too).
- **FastAPI + Pydantic** — a small, typed service.
- **Graceful degradation** — if the model or key is unavailable, a heuristic parser
  keeps the pipeline running. An autopilot that breaks isn't production-ready.

## What we learned

Two things. First, Qwen's function-calling combined with its Indian domain knowledge
(HSN codes, GST rates) is strong enough to run a real back-office workflow — not a toy.
Second, the right interface for Bharat's smallest businesses is the one they already
use: **WhatsApp, in their own language**.

## What's next

Live IRP registration for an NIC-signed IRN and QR (the code seam is ready), the
WhatsApp Cloud API as a real channel, payment reconciliation with ledger/ERP sync, and
a two-way clarification loop with the customer.

*VyaparAI — a back office for Bharat's 60 million MSMEs, in any language they type.*
