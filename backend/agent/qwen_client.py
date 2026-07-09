"""Thin wrapper around Qwen Cloud (OpenAI-compatible Chat Completions).

Qwen Cloud exposes an OpenAI-compatible endpoint. Get your key + confirm the model
id at home.qwencloud.com/api-keys after redeeming the hackathon voucher, then set
them in .env (QWEN_API_KEY / QWEN_BASE_URL / QWEN_MODEL).
"""
from __future__ import annotations

import json
import os
import re

from backend.models import Inquiry, Language, ParsedItem

DEFAULT_BASE_URL = os.getenv(
    "QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)
DEFAULT_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

_SYSTEM = (
    "You are an order-intake assistant for an Indian MSME. "
    "Read a customer inquiry written in English, Hindi, or Hinglish and extract a clean order. "
    "Detect the language. Return STRICT JSON only, no prose."
)

_SCHEMA_HINT = """Return JSON exactly in this shape:
{
  "language": "en|hi|hinglish|other",
  "customer_name": string or null,
  "customer_gstin": string or null,
  "items": [{"query": string, "qty": number, "unit_hint": string or null}],
  "clarifications_needed": [string]
}"""


def _to_lang(v) -> Language:
    try:
        return Language(v)
    except Exception:
        return Language.OTHER


def _extract_json(s: str) -> str:
    i, j = s.find("{"), s.rfind("}")
    return s[i : j + 1] if i != -1 and j != -1 else s


# --- Offline heuristic parser: graceful degradation before a Qwen key is set ---
_CONNECTORS = re.compile(r"\b(?:aur|and|plus|evam)\b|[,&+]|और|तथा", re.I)
_FILLER = re.compile(
    r"\b(bhai|bhaiya|sir|madam|please|pls|kindly|ka|ki|ke|ko|quote|estimate|"
    r"bhej|bhejo|bhejdo|do|dena|chahiye|chaiye|need|want|mujhe|hume|hme|for|of|"
    r"the|a|an|price|rate|kitna|kitne)\b",
    re.I,
)


def _detect_lang(raw: str) -> Language:
    if re.search(r"[ऀ-ॿ]", raw):
        return Language.HI
    if re.search(r"\b(bhai|chahiye|bhej|kitna|kitne|do|dena|ka|ki|ke|aur|mujhe)\b", raw, re.I):
        return Language.HINGLISH
    return Language.EN


def _heuristic_parse(raw: str) -> list[ParsedItem]:
    items: list[ParsedItem] = []
    for seg in _CONNECTORS.split(raw):
        seg = (seg or "").strip()
        if not seg:
            continue
        m = re.search(r"\d+(?:\.\d+)?", seg)
        qty = float(m.group(0)) if m else 1.0
        query = _FILLER.sub(" ", re.sub(r"\d+(?:\.\d+)?", " ", seg))
        query = re.sub(r"\s+", " ", query).strip()
        if query:
            items.append(ParsedItem(query=query, qty=qty))
    return items or [ParsedItem(query=raw, qty=1)]


class QwenClient:
    def __init__(self, api_key=None, base_url=DEFAULT_BASE_URL, model=DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("QWEN_API_KEY", "")
        self.base_url = base_url
        self.model = model
        self._client = None

    def _ensure(self):
        if self._client is None:
            from openai import OpenAI  # OpenAI-compatible client pointed at Qwen Cloud

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def chat(self, prompt: str, system: str = _SYSTEM) -> str:
        client = self._ensure()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content

    def extract_inquiry(self, raw_text: str) -> Inquiry:
        """Turn raw EN/HI/Hinglish text into a structured Inquiry."""
        if not self.api_key:
            # Graceful degradation: heuristic parse so the pipeline runs/demos with no key.
            return Inquiry(
                raw_text=raw_text,
                language=_detect_lang(raw_text),
                items=_heuristic_parse(raw_text),
                clarifications_needed=[
                    "Heuristic offline parser in use (set QWEN_API_KEY for full Qwen NLU)."
                ],
            )
        data = json.loads(_extract_json(self.chat(f"{_SCHEMA_HINT}\n\nInquiry:\n{raw_text}")))
        return Inquiry(
            raw_text=raw_text,
            language=_to_lang(data.get("language", "en")),
            customer_name=data.get("customer_name"),
            customer_gstin=data.get("customer_gstin"),
            items=[ParsedItem(**it) for it in data.get("items", [])],
            clarifications_needed=data.get("clarifications_needed", []),
        )
