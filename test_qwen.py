"""Quick live check that Qwen Cloud parsing works. Run: python test_qwen.py"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from backend.agent.qwen_client import QwenClient  # noqa: E402

c = QwenClient()
print(f"key set: {bool(c.api_key)} | base: {c.base_url} | model: {c.model}")
try:
    inq = c.extract_inquiry(
        "Sirji 30 modular switch socket 6A aur 5 inverter 1kVA chahiye, quote bhejo"
    )
    print("language:", inq.language.value)
    for it in inq.items:
        print(f"  - {it.qty} x {it.query}")
    print("clarifications:", inq.clarifications_needed)
    print("LIVE_QWEN_OK")
except Exception as e:
    print("QWEN_ERROR:", type(e).__name__, repr(str(e))[:500])
