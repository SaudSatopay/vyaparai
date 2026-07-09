# VyaparAI — 3-minute demo video script

Screen-record the app (deployed URL or localhost) with a voiceover. Target **≤ 3:00**.
The **solar-panel moment (0:50–1:30) is the highlight** — make sure the agent trace is
readable on screen.

---

**[0:00–0:20] Hook + problem**
*Show:* the WhatsApp chat panel.
> "60 million small businesses in India run on WhatsApp. A customer messages in Hindi,
> English, or a mix — and the owner has to look up prices, figure out HSN codes,
> calculate GST, and raise a compliant invoice by hand. It's slow and error-prone.
> This is VyaparAI — an autonomous agent that does the whole thing."

**[0:20–0:50] Inquiry → the agent reasons**
*Show:* the Hinglish message arrive — *"bhai 50 LED bulb 9W aur 10 ceiling fan ka quote bhej do"* — then the agent trace appear.
> "The customer asks for a quote in Hinglish. VyaparAI's Qwen agent detects the
> language and goes to work — and you can watch it reason: it searches the catalog and
> pulls the real HSN codes and GST rates."

**[0:50–1:30] The wow — off-catalog HSN classification**
*Show:* send a message including *"3 solar panel 100W"*; zoom the trace on `classify_hsn`.
> "Now watch something that isn't in the catalog. The agent notices the catalog match
> is wrong — and on its own calls a classification tool. Solar panel: HSN 8541, 5% GST —
> the correct Indian GST treatment, figured out live by the model. No hardcoding."

**[1:30–2:05] GST quote + human-in-the-loop**
*Show:* the quote card — line items, CGST/SGST split, grand total.
> "The result is a proper GST quote: per-item HSN, the correct CGST and SGST split, and
> the grand total. Nothing goes out automatically — the owner reviews and approves.
> That's the human-in-the-loop checkpoint."
*Action:* click **Approve & generate e-invoice**.

**[2:05–2:35] E-invoice + delivery**
*Show:* the invoice card (invoice no, IRN, QR, APPROVED stamp); click **Send on WhatsApp**; the invoice bubble drops into the chat.
> "On approval, VyaparAI generates a GST e-invoice — invoice number, IRN, QR — and
> sends it straight back to the customer on WhatsApp with a UPI payment line.
> Quote to cash, done."

**[2:35–3:00] Tech + close**
*Show:* the architecture diagram in the README.
> "Under the hood: a Qwen function-calling agent on Qwen Cloud, deployed on Alibaba
> Cloud, with a graceful-degradation fallback so it never breaks. VyaparAI — a back
> office for Bharat's 60 million MSMEs, in any language they type."

---

### Recording tips
- Do the two-item demo first, then a second message with the solar panel so the
  `classify_hsn` step is unmistakable.
- Let the agent-trace steps be on screen long enough to read (pause/scroll if needed).
- Keep the language pill (`Hinglish`) and NLU pill (`Qwen NLU`) visible.
- Upload to YouTube/Vimeo as **public or unlisted**; put the link in the submission.
