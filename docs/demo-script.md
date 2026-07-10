# VyaparAI — 3-minute demo video script (final feature set)

Record on **localhost:8000** (voice features need a secure context) in Chrome/Edge,
with your **phone in hand** for the QR moment. Target **≤ 3:00**. The two highlights:
the **off-catalog solar-panel classification** (~0:55) and the **natural-language
revision** (~1:25) — keep both readable on screen.

---

**[0:00–0:15] Hook**
*Show:* the app — WhatsApp panel + empty desk.
> "60 million Indian small businesses take orders on WhatsApp — in Hindi, English, or
> both mixed. Every order means price lookups, HSN codes, GST math, and a compliant
> invoice, all by hand. This is VyaparAI: an autonomous Qwen agent that runs the whole
> thing — with the owner in charge."

**[0:15–0:45] Voice order → the agent reasons**
*Action:* tap 🎤 and **speak**: *"bhai 500 LED bulb 9W, 10 ceiling fan aur 3 solar panel ka quote bhej do"*.
*Show:* transcript lands, typing dots, then the **agent trace** streaming tool calls.
> "I just *spoke* the order in Hinglish. The agent detects the language and gets to
> work — watch it reason: catalog search, real HSN codes, real GST rates."

**[0:45–1:10] The classification wow + stock alert**
*Show:* zoom the trace on `classify_hsn`; point at the amber notes.
> "Solar panels aren't in the catalog — the agent noticed the bad match and called its
> HSN classifier on its own: **HSN 8541, 5% GST — the correct Indian treatment.**
> And see this: I asked for 500 bulbs; it flags that only 420 are in stock. An
> autopilot with judgment."

**[1:10–1:40] "Ask for changes" — natural-language revision**
*Action:* click **Ask for changes**, type *"bulb 400 kar do aur 10% discount de do"* → Revise.
*Show:* the quote re-renders — **🔁 revision 2** chip, new totals; then tap **🔊**.
> "The owner doesn't fill forms — they just say what they want changed. Quantity fixed,
> ten percent off, totals recomputed exactly. And the agent reads the quote back —
> in Hindi. It speaks English too; the whole product does."

**[1:40–2:10] Approve → a real GST e-invoice**
*Action:* click **Approve & generate e-invoice**. Click the **e-invoice QR**.
*Show:* the modal: big QR + **✓ SIGNATURE VERIFIED** + decoded payload.
> "On approval: an e-invoice with the NIC INV-01 payload, an IRN computed with the
> exact NIC SHA-256 algorithm, and a JWS-signed QR — click it, and VyaparAI verifies
> the signature live. This is the compliance layer, built for real."

**[2:10–2:40] UPI scan-to-pay → paid → ledger**
*Action:* open the **UPI QR** modal; scan it with your **phone on camera** — GPay/PhonePe
opens with ₹ amount pre-filled. Click **Send on WhatsApp**, then **💰 Mark paid**.
*Show:* PAID stamp; the **ledger strip** ticks — collected ₹, GST ₹.
> "Every invoice carries a UPI scan-to-pay QR — the amount arrives pre-filled. Payment
> in, mark it paid — and the live ledger tracks collections and GST. Quote to cash,
> closed."

**[2:40–3:00] Close**
*Show:* the README architecture diagram, then the live URL bar (47.84.111.3:8000).
> "A Qwen function-calling agent on Qwen Cloud, deployed live on Alibaba Cloud, with
> graceful degradation so it never breaks. VyaparAI — a back office for Bharat's 60
> million MSMEs, in any language they type. Or speak."

---

### Recording tips
- **Practice the voice line once** — if the room is noisy, type it instead and lead
  with the 🎤 on the revision instead.
- Keep the chips visible: `🌐 Hinglish`, `✦ Qwen NLU`, `🔁 revision 2`.
- The phone-scanning-the-UPI-QR shot is the most memorable 5 seconds — frame it.
- One take in English afterwards if time allows ("I need 12 solar panels…") — flash it
  during the close to prove full English parity.
- Upload to YouTube/Vimeo **public or unlisted**; paste the link into SUBMISSION.md.
