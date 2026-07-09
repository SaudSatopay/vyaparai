"""Printable GST tax-invoice HTML (browser print -> PDF) + INR amount-in-words."""
from __future__ import annotations

from backend.models import Invoice

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n: int) -> str:
    return _ONES[n] if n < 20 else (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else ""))


def _three(n: int) -> str:
    h, r = divmod(n, 100)
    out = (_ONES[h] + " Hundred") if h else ""
    if r:
        out += (" " if out else "") + _two(r)
    return out


def inr_words(amount: float) -> str:
    """Indian numbering: crore / lakh / thousand. 21870.5 -> words with paise."""
    rupees = int(amount)
    paise = round((amount - rupees) * 100)
    if rupees == 0:
        words = "Zero"
    else:
        crore, rem = divmod(rupees, 10_000_000)
        lakh, rem = divmod(rem, 100_000)
        thousand, hundreds = divmod(rem, 1000)
        parts = []
        if crore:
            parts.append(_two(crore) + " Crore" if crore < 100 else _three(crore) + " Crore")
        if lakh:
            parts.append(_two(lakh) + " Lakh")
        if thousand:
            parts.append(_two(thousand) + " Thousand")
        if hundreds:
            parts.append(_three(hundreds))
        words = " ".join(parts)
    out = f"Rupees {words}"
    if paise:
        out += f" and {_two(paise)} Paise"
    return out + " Only"


def render_invoice_html(inv: Invoice) -> str:
    q = inv.quote
    d = inv.inv01 or {}
    seller = d.get("SellerDtls", {})
    buyer = d.get("BuyerDtls", {})
    doc = d.get("DocDtls", {})
    inter = (q.total_igst or 0) > 0

    rows = ""
    for i, l in enumerate(q.lines, start=1):
        tax_cols = (f"<td class='r'>{l.igst:,.2f}</td>" if inter
                    else f"<td class='r'>{l.cgst:,.2f}</td><td class='r'>{l.sgst:,.2f}</td>")
        rows += (f"<tr><td>{i}</td><td class='l'>{l.name}</td><td>{l.hsn}</td>"
                 f"<td class='r'>{l.qty:g} {l.unit}</td><td class='r'>{l.unit_price:,.2f}</td>"
                 f"<td class='r'>{l.taxable_value:,.2f}</td><td class='r'>{l.gst_rate:g}%</td>"
                 f"{tax_cols}<td class='r'><b>{l.line_total:,.2f}</b></td></tr>")

    tax_head = ("<th>IGST (₹)</th>" if inter else "<th>CGST (₹)</th><th>SGST (₹)</th>")
    tax_totals = (f"<div>IGST: <b>₹{q.total_igst:,.2f}</b></div>" if inter else
                  f"<div>CGST: <b>₹{q.total_cgst:,.2f}</b></div>"
                  f"<div>SGST: <b>₹{q.total_sgst:,.2f}</b></div>")

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Tax Invoice {inv.invoice_no}</title>
<style>
 body{{font-family:'Segoe UI',system-ui,sans-serif;color:#1c1710;margin:0;background:#f2ede2}}
 .page{{max-width:860px;margin:24px auto;background:#fff;padding:34px 40px;box-shadow:0 8px 30px #0002}}
 h1{{font-size:21px;margin:0;letter-spacing:.04em}}
 .muted{{color:#77694f;font-size:11.5px}}
 .top{{display:flex;justify-content:space-between;gap:18px;border-bottom:2.5px solid #1c1710;padding-bottom:14px}}
 .qr{{text-align:center}} .qr img{{width:118px;height:118px}}
 .qr .cap{{font-size:9px;color:#77694f;margin-top:2px}}
 .meta{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0;font-size:12.5px}}
 .box{{border:1px solid #ddd2bb;border-radius:8px;padding:10px 13px}}
 .box .h{{font-size:10px;letter-spacing:.1em;color:#a5541b;font-weight:700;margin-bottom:5px}}
 .irn{{font-family:Consolas,monospace;font-size:10.5px;word-break:break-all}}
 table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}}
 th{{background:#f6efdd;border:1px solid #ddd2bb;padding:7px 6px;font-size:10.5px;letter-spacing:.03em}}
 td{{border:1px solid #e7ddc8;padding:7px 6px;text-align:center}}
 td.l{{text-align:left}} td.r,th.r{{text-align:right}}
 .sums{{display:flex;justify-content:flex-end;gap:26px;margin-top:12px;font-size:13px;align-items:baseline}}
 .grand{{font-size:19px;font-weight:800;color:#12805c}}
 .words{{margin-top:9px;font-size:12px;font-style:italic;color:#4b4232}}
 .foot{{margin-top:26px;display:flex;justify-content:space-between;align-items:flex-end;font-size:11.5px}}
 .sign{{text-align:center;color:#4b4232}} .sign .line{{border-top:1px solid #999;padding-top:5px;margin-top:44px}}
 @media print{{body{{background:#fff}} .page{{box-shadow:none;margin:0}} .noprint{{display:none}}}}
 .noprint{{text-align:center;margin:14px}}
 .noprint button{{padding:10px 22px;border:none;border-radius:9px;background:#dc6b18;color:#fff;font-weight:700;cursor:pointer}}
</style></head><body>
<div class="page">
  <div class="top">
    <div>
      <h1>TAX INVOICE</h1>
      <div class="muted">e-Invoice · NIC INV-01 v1.1 · {'B2B' if buyer.get('Gstin','URP')!='URP' else 'B2C'}</div>
      <div style="margin-top:10px;font-size:14px"><b>{seller.get('LglNm','')}</b></div>
      <div class="muted">{seller.get('Addr1','')}, {seller.get('Loc','')} – {seller.get('Pin','')}<br>
      GSTIN: <b>{seller.get('Gstin','')}</b> · State: {seller.get('Stcd','')}</div>
    </div>
    <div class="qr">
      <img src="/invoice/{inv.invoice_no}/qr.svg" alt="signed e-invoice QR">
      <div class="cap">signed e-invoice QR<br>scan to verify</div>
    </div>
  </div>

  <div class="meta">
    <div class="box"><div class="h">INVOICE</div>
      No: <b>{inv.invoice_no}</b><br>Date: <b>{doc.get('Dt','')}</b><br>
      Ack No: {inv.ack_no or '—'} · Ack Dt: {inv.ack_dt or '—'}
    </div>
    <div class="box"><div class="h">BILL TO</div>
      <b>{buyer.get('LglNm','Walk-in Customer')}</b><br>
      GSTIN: {buyer.get('Gstin','URP')}{' (unregistered)' if buyer.get('Gstin')=='URP' else ''}<br>
      Place of supply: {buyer.get('Pos','')}
    </div>
  </div>
  <div class="box" style="margin-bottom:4px"><div class="h">IRN (INVOICE REFERENCE NUMBER)</div>
    <span class="irn">{inv.irn or ''}</span></div>

  <table>
    <tr><th>#</th><th>Item</th><th>HSN</th><th class="r">Qty</th><th class="r">Rate (₹)</th>
        <th class="r">Taxable (₹)</th><th>GST</th>{tax_head}<th class="r">Amount (₹)</th></tr>
    {rows}
  </table>

  <div class="sums">
    <div class="muted">Taxable: <b>₹{q.taxable_total:,.2f}</b></div>
    {tax_totals}
    <div class="grand">TOTAL: ₹{q.grand_total:,.2f}</div>
  </div>
  <div class="words">{inr_words(q.grand_total)}</div>

  <div class="foot">
    <div class="muted">Signed: {inv.signed_by or ''}<br>
    This is a computer-generated e-invoice; the QR carries a JWS-signed payload.</div>
    <div class="sign"><div class="line">Authorised Signatory<br>{seller.get('LglNm','')}</div></div>
  </div>
</div>
<div class="noprint"><button onclick="print()">🖨️ Print / Save as PDF</button></div>
</body></html>"""
