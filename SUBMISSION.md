# VyaparAI — Devpost submission copy (Autopilot Agent track)

Paste these into the matching Devpost fields. Fill the three links at the bottom
once the deploy, repo, and video are live.

## Elevator pitch (one line)
An autonomous Qwen agent that turns a WhatsApp inquiry — in English, Hindi, or
Hinglish — into an approved, GST-compliant e-invoice, with the shop owner in the loop.

## Inspiration
India has **60M+ MSMEs**, and most of them take orders over **WhatsApp** in a mix of
Hindi and English. Every order means manually looking up prices, guessing the right
**HSN code**, computing **GST**, and raising a compliant invoice — slow, error-prone,
and a compliance risk for the smallest businesses that can least afford a back office.
We wanted an agent that runs the entire **quote-to-cash** path the way a sharp
back-office clerk would — instantly, and in whatever language the customer types.

## What it does
1. Reads a free-text inquiry (EN / HI / Hinglish) from WhatsApp or email.
2. A **Qwen function-calling agent** autonomously: searches the catalog; for anything
   off-catalog, **classifies its HSN code + GST rate**; adds line items; asks
   clarifying questions when the request is ambiguous; and finalizes.
3. Computes a **correct GST quote** — CGST/SGST intra-state or IGST inter-state, with
   per-item HSN and rate.
4. **Human-in-the-loop:** the owner reviews and approves before anything is sent.
5. Generates a **GST e-invoice** (invoice no, IRN, QR) and delivers it back over
   WhatsApp with a UPI payment line.

## How we built it
- **Qwen Cloud (`qwen-plus`)** via the OpenAI-compatible endpoint — the agent's brain
  and tool-caller; also does HSN/GST classification and multilingual understanding.
- **A function-calling agent loop** (`backend/agent/agent_loop.py`) with five tools —
  `search_catalog`, `classify_hsn`, `add_line_item`, `request_clarification`,
  `finalize_quote` — orchestrated by the model, with a captured **reasoning trace**.
- **A GST engine** (`backend/agent/tools.py`): HSN-tagged catalog and CGST/SGST/IGST math.
- **FastAPI** service + a self-contained **WhatsApp-style review UI** for the human checkpoint.
- **Alibaba Cloud** deployment (Function Compute / ECS).
- **Graceful degradation:** a heuristic parser keeps the pipeline working even if the
  model or key is unavailable.

## The agent — why it's technically deep
It's not one LLM call; it's a real ReAct-style loop. Given
*"20 LED bulb, 5 ceiling fan, aur 3 solar panel 100W chahiye"*, the agent searched the
catalog, **recognized that the fuzzy match for "solar panel" was wrong** (it returned
insulation tape), and on its own called `classify_hsn` → **HSN 8541 @ 5% GST** — the
correct Indian GST treatment for solar panels — then finalized a correct three-rate
quote. The full tool-call trace is shown live in the UI.

## Challenges we ran into
- **Code-mixed (Hinglish) parsing** — solved with Qwen plus language detection.
- **GST correctness** (intra- vs inter-state, per-HSN rates) — a deterministic engine
  on top of the agent's structured output.
- **Tool-calling reliability** — a bounded step loop, strict tool schemas, and a
  deterministic fallback so a customer request never fails.

## Accomplishments we're proud of
- A genuine autonomous agent that classifies off-catalog items' HSN/GST correctly.
- Correct multi-rate GST invoices with CGST/SGST/IGST.
- **Standards-real e-invoicing:** NIC INV-01 v1.1 payload, IRN computed with the exact
  NIC SHA-256 algorithm, a JWS-signed **scannable** QR, and a printable tax invoice
  with amount-in-words (Indian lakh/crore system).
- Bilingual, WhatsApp-native, with a real human-in-the-loop approval step.
- Production-minded: graceful degradation, clean architecture, one-command deploy.

## What we learned
- Qwen's function-calling plus its Indian domain knowledge (HSN/GST) is strong enough
  to run real back-office workflows end to end.
- The winning UX for Bharat is **WhatsApp + the local language**, not a dashboard.

## What's next
- Live **IRP sandbox** integration for a real signed IRN + QR.
- **WhatsApp Cloud API** channel.
- **UPI** payment links + ledger / ERP sync.
- Multi-turn clarification loop directly with the customer.

## Built with
`Qwen Cloud` · `qwen-plus` · `Alibaba Cloud` · `Function Compute` · `Python` ·
`FastAPI` · `Pydantic` · `OpenAI SDK` · `HTML/CSS/JS`

## Links (fill in)
- **Live demo:** http://47.84.111.3:8000 (Alibaba Cloud ECS, Singapore — `ecs.e-c1m1.large`, Ubuntu 22.04, systemd service)
- **Repository:** {REPO_URL}
- **Video (≈3 min):** {VIDEO_URL}
- **Track:** Autopilot Agent
