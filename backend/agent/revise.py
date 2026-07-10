"""Natural-language quote revision — the owner's change requests, EN/HI/Hinglish.

"bulb 40 kar do", "10% discount de do", "AC hata do, 2 geyser add karo" — the agent
rewrites the draft line items accordingly, using catalog prices for catalog items.
"""
from __future__ import annotations

import json

from backend.agent import tools
from backend.agent.qwen_client import QwenClient, _extract_json
from backend.models import Quote

_SYSTEM = (
    "You revise draft GST quotes for an Indian MSME owner. The owner's instruction may be "
    "English, Hindi, or Hinglish: change quantities, add or remove items, apply a discount "
    "(reduce unit_price accordingly and mention it in change_summary), or swap items. "
    "Use CATALOG prices for catalog items (product_id from the catalog). For off-catalog "
    "items use product_id CUSTOM with a correct Indian GST HSN code and rate. "
    "Return STRICT JSON only, no prose:\n"
    '{"lines": [{"product_id": str, "name": str, "hsn": str, "qty": number, "unit": str, '
    '"unit_price": number, "gst_rate": number}], '
    '"change_summary": "one short line", "notes": ["optional clarifications"]}'
)


def _catalog_block() -> str:
    return "\n".join(
        f'{p["id"]} | {p["name"]} | Rs{p["unit_price"]} | {p["gst_rate"]}% | '
        f'{p["unit"]} | stock {p["stock"]}'
        for p in tools.CATALOG
    )


def revise_lines(qwen: QwenClient, quote: Quote, instruction: str):
    """Returns (new_line_dicts, change_summary, notes)."""
    current = [
        {"product_id": l.product_id, "name": l.name, "hsn": l.hsn, "qty": l.qty,
         "unit": l.unit, "unit_price": l.unit_price, "gst_rate": l.gst_rate}
        for l in quote.lines
    ]
    prompt = (
        "CURRENT QUOTE LINES:\n" + json.dumps(current, ensure_ascii=False)
        + "\n\nCATALOG (id | name | price | gst | unit | stock):\n" + _catalog_block()
        + "\n\nOWNER'S INSTRUCTION:\n" + instruction
    )
    data = json.loads(_extract_json(qwen.chat(prompt, system=_SYSTEM)))
    lines = [
        {
            "product_id": d.get("product_id", "CUSTOM"),
            "name": d.get("name", "item"),
            "hsn": str(d.get("hsn", "0000")),
            "qty": float(d.get("qty", 1) or 1),
            "unit": d.get("unit", "pcs"),
            "unit_price": float(d.get("unit_price", 0) or 0),
            "gst_rate": float(d.get("gst_rate", 18) or 18),
        }
        for d in data.get("lines", [])
    ]
    return (
        lines,
        str(data.get("change_summary", "Quote revised.")),
        [str(n) for n in data.get("notes", [])],
    )
