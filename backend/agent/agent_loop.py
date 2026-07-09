"""Genuine Qwen function-calling agent for the quote-to-cash workflow.

The agent autonomously decides which tools to call (search the catalog, classify
an off-catalog item's HSN/GST, add line items, ask clarifying questions, finalize)
until it produces a quote. Returns the working line items + a trace of every tool
call so the UI can show the agent's reasoning.
"""
from __future__ import annotations

import json

from backend.agent import tools

_AGENT_SYSTEM = (
    "You are VyaparAI, an autonomous sales-desk agent for an Indian MSME. "
    "A customer sends an inquiry in English, Hindi, or Hinglish. Turn it into a "
    "GST-ready quote.\n"
    "Workflow:\n"
    "1. For each product the customer wants, call search_catalog.\n"
    "2. If the catalog returns a good match, call add_line_item using the catalog's "
    "product_id, hsn, unit_price and gst_rate.\n"
    "3. If there is NO catalog match, call classify_hsn to get the HSN + GST rate. "
    "Then, only if the customer stated a price, call add_line_item; otherwise call "
    "request_clarification asking for the target price/budget.\n"
    "4. Call request_clarification for anything genuinely ambiguous (spec, brand, "
    "delivery) without blocking the quote.\n"
    "5. When every item is handled, call finalize_quote.\n"
    "Use the catalog's real numbers. Never invent a price for a catalog item."
)

_TOOLS = [
    {"type": "function", "function": {
        "name": "search_catalog",
        "description": "Search the seller's catalog for items matching a free-text query "
                       "(EN/HI/Hinglish). Returns candidate products with id, name, hsn, "
                       "gst_rate, unit_price, unit, stock.",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "classify_hsn",
        "description": "Classify an off-catalog product to an Indian GST HSN code and rate "
                       "from its description. Use only when search_catalog has no good match.",
        "parameters": {"type": "object",
                       "properties": {"description": {"type": "string"}},
                       "required": ["description"]}}},
    {"type": "function", "function": {
        "name": "add_line_item",
        "description": "Add a confirmed line item to the working quote.",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"},
            "name": {"type": "string"},
            "hsn": {"type": "string"},
            "qty": {"type": "number"},
            "unit": {"type": "string"},
            "unit_price": {"type": "number"},
            "gst_rate": {"type": "number"}},
            "required": ["name", "hsn", "qty", "unit_price", "gst_rate"]}}},
    {"type": "function", "function": {
        "name": "request_clarification",
        "description": "Flag a clarifying question for the owner/customer. Non-blocking.",
        "parameters": {"type": "object",
                       "properties": {"question": {"type": "string"}},
                       "required": ["question"]}}},
    {"type": "function", "function": {
        "name": "finalize_quote",
        "description": "Finalize once all items are added; triggers GST computation.",
        "parameters": {"type": "object",
                       "properties": {"intra_state": {"type": "boolean"}},
                       "required": []}}},
]


def _dispatch(name, args, working, clarifications, finalized, qwen, trace):
    if name == "search_catalog":
        cands = tools.catalog_lookup(args.get("query", ""))
        top = cands[0] if cands else None
        trace.append({"tool": "search_catalog", "input": args.get("query", ""),
                      "output": (f'{top["name"]} · HSN {top["hsn"]} · {top["gst_rate"]}%'
                                 if top else "no catalog match")})
        return {"candidates": [
            {k: c.get(k) for k in ("id", "name", "hsn", "gst_rate", "unit_price", "unit", "stock")}
            for c in cands[:3]]}
    if name == "classify_hsn":
        c = qwen.classify_hsn(args.get("description", ""))
        trace.append({"tool": "classify_hsn", "input": args.get("description", ""),
                      "output": f'HSN {c["hsn"]} · {c["gst_rate"]}%'})
        return c
    if name == "add_line_item":
        line = {
            "product_id": args.get("product_id", "CUSTOM"),
            "name": args.get("name", "item"),
            "hsn": str(args.get("hsn", "0000")),
            "qty": float(args.get("qty", 1) or 1),
            "unit": args.get("unit", "pcs"),
            "unit_price": float(args.get("unit_price", 0) or 0),
            "gst_rate": float(args.get("gst_rate", 18) or 18),
        }
        working.append(line)
        trace.append({"tool": "add_line_item", "input": f'{line["qty"]:g} x {line["name"]}',
                      "output": f'Rs {line["unit_price"]:g} · {line["gst_rate"]:g}% GST'})
        return {"ok": True, "lines_so_far": len(working)}
    if name == "request_clarification":
        q = args.get("question", "")
        clarifications.append(q)
        trace.append({"tool": "request_clarification", "input": "", "output": q})
        return {"ok": True}
    if name == "finalize_quote":
        finalized["done"] = True
        if isinstance(args.get("intra_state"), bool):
            finalized["intra_state"] = args["intra_state"]
        trace.append({"tool": "finalize_quote", "input": "",
                      "output": f'{len(working)} line item(s)'})
        return {"ok": True}
    return {"error": f"unknown tool {name}"}


def run_agent(raw_text, qwen, intra_state=True, max_steps=8):
    """Run the Qwen tool-calling loop. Returns (lines, clarifications, intra_state, trace)."""
    client = qwen._ensure()
    working, clarifications, trace = [], [], []
    finalized = {"done": False, "intra_state": intra_state}
    messages = [
        {"role": "system", "content": _AGENT_SYSTEM},
        {"role": "user", "content": raw_text},
    ]
    for _ in range(max_steps):
        resp = client.chat.completions.create(
            model=qwen.model, messages=messages, tools=_TOOLS, temperature=0.1)
        msg = resp.choices[0].message
        amsg = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            amsg["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls]
        messages.append(amsg)
        if not msg.tool_calls:
            break
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            result = _dispatch(tc.function.name, args, working, clarifications,
                               finalized, qwen, trace)
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result)})
        if finalized["done"]:
            break
    return working, clarifications, finalized["intra_state"], trace
