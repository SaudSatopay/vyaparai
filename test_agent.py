"""Live test of the Qwen tool-calling agent. Run: python test_agent.py"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from backend.agent.orchestrator import QuoteToCashAgent  # noqa: E402

agent = QuoteToCashAgent()
q = agent.draft_quote(
    "namaste, mujhe 20 LED bulb 9W, 5 ceiling fan, aur 3 solar panel 100W chahiye - quote bhej do"
)

print(f"language={q.detected_language}  status={q.status.value}")
print("\n--- AGENT TRACE ---")
for t in q.agent_trace:
    print(f"  [{t['tool']}] {t.get('input','')}  ->  {t.get('output','')}")
print("\n--- LINE ITEMS ---")
for l in q.lines:
    print(f"  {l.qty:g} x {l.name}  HSN {l.hsn}  {l.gst_rate:g}%  = Rs {l.line_total:g}")
print(f"\nGRAND TOTAL: Rs {q.grand_total:g}")
print("NOTES:", q.notes)
