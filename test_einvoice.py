"""Offline tests for the e-invoice layer (INV-01, IRN, JWS QR, words). No API key needed."""
from backend.agent import einvoice, tools
from backend.invoice_page import inr_words
from backend.models import Inquiry, ParsedItem

# Build a quote through the deterministic path
inq = Inquiry(raw_text="test", customer_name="Sharma Electricals",
              items=[ParsedItem(query="led bulb", qty=50), ParsedItem(query="ceiling fan", qty=10)])
matched = [(it, tools.catalog_lookup(it.query)[0]) for it in inq.items]
quote = tools.build_quote("Q-TEST", inq, matched, intra_state=True)

inv = tools.generate_gst_invoice("INV-9001", quote, einvoice.seller_details()["Gstin"])

# 1) IRN: 64-hex, deterministic per NIC algorithm
assert inv.irn and len(inv.irn) == 64 and int(inv.irn, 16) >= 0
fy = einvoice.financial_year(__import__("datetime").datetime.now())
assert inv.irn == einvoice.compute_irn(inv.seller_gstin, fy, "INV", "INV-9001")
print(f"IRN ok: {inv.irn[:20]}... (fy {fy})")

# 2) JWS QR: verifies with sandbox key, tamper breaks it
payload = einvoice.verify_jws(inv.qr_jws)
assert payload and payload["Irn"] == inv.irn and payload["TotInvVal"] == quote.grand_total
assert einvoice.verify_jws(inv.qr_jws[:-3] + "xxx") is None
print(f"JWS ok: verifies, tamper-proof. ItemCnt={payload['ItemCnt']} MainHsn={payload['MainHsnCode']}")

# 3) INV-01: structure + value reconciliation
d = inv.inv01
assert d["Version"] == "1.1" and d["TranDtls"]["SupTyp"] == "B2C"
assert len(d["ItemList"]) == 2
assert abs(sum(i["TotItemVal"] for i in d["ItemList"]) - d["ValDtls"]["TotInvVal"]) < 0.01
assert d["ValDtls"]["TotInvVal"] == quote.grand_total == 21870.0
assert d["BuyerDtls"]["LglNm"] == "Sharma Electricals"
print(f"INV-01 ok: TotInvVal={d['ValDtls']['TotInvVal']} Buyer={d['BuyerDtls']['LglNm']}")

# 4) Amount in words (Indian system)
w = inr_words(21870.0)
assert w == "Rupees Twenty One Thousand Eight Hundred Seventy Only", w
assert inr_words(12_34_567.50) == "Rupees Twelve Lakh Thirty Four Thousand Five Hundred Sixty Seven and Fifty Paise Only"
assert inr_words(2_50_00_000) == "Rupees Two Crore Fifty Lakh Only"
print(f"Words ok: '{w}'")

print("ALL_EINVOICE_TESTS_PASSED")
