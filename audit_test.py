"""Full system audit test."""
import requests
import json

API = "http://127.0.0.1:8000/api"

def p(label, r):
    resp = r.get("response", "NO RESPONSE")[:120]
    intent = r.get("intent", "?")
    print(f"  [{intent}] {resp}")

print("=" * 70)
print("AUDIT 1: MULTI-TURN CONTEXT (slot-filling)")
print("=" * 70)
sid = "audit_mt_1"
r1 = requests.post(f"{API}/chat", json={"message": "Calculate EMI for 10 lakh at 8.5% for 20 years", "session_id": sid, "use_bert": True}).json()
print("T1 (EMI, missing currency):")
p("", r1)
r2 = requests.post(f"{API}/chat", json={"message": "INR", "session_id": sid, "use_bert": True}).json()
print("T2 (fill currency 'INR'):")
p("", r2)
r3 = requests.post(f"{API}/chat", json={"message": "What is the price of AAPL?", "session_id": sid, "use_bert": True}).json()
print("T3 (new question, same session):")
p("", r3)

print()
print("=" * 70)
print("AUDIT 2: SESSION ISOLATION (no bleed between sessions)")
print("=" * 70)
sid_a = "audit_iso_A"
sid_b = "audit_iso_B"
ra1 = requests.post(f"{API}/chat", json={"message": "Calculate EMI for 5 lakh at 10% for 5 years", "session_id": sid_a, "use_bert": True}).json()
print("Session A T1 (EMI start):")
p("", ra1)
rb1 = requests.post(f"{API}/chat", json={"message": "What is SIP?", "session_id": sid_b, "use_bert": True}).json()
print("Session B T1 (FAQ, separate user):")
p("", rb1)
ra2 = requests.post(f"{API}/chat", json={"message": "INR", "session_id": sid_a, "use_bert": True}).json()
print("Session A T2 (fill currency — should work even though B was between):")
p("", ra2)
rb2 = requests.post(f"{API}/chat", json={"message": "AAPL price", "session_id": sid_b, "use_bert": True}).json()
print("Session B T2 (stock — should NOT see any EMI context):")
p("", rb2)

print()
print("=" * 70)
print("AUDIT 3: LOCAL KNOWLEDGE BASE (Gemini OFF)")
print("=" * 70)
r = requests.post(f"{API}/chat", json={"message": "What is a savings account?", "session_id": "audit_faq1", "use_bert": True, "use_gemini": False}).json()
print("FAQ (savings account):")
p("", r)
r = requests.post(f"{API}/chat", json={"message": "explain mutual funds", "session_id": "audit_faq2", "use_bert": True, "use_gemini": False}).json()
print("FAQ (mutual funds):")
p("", r)
r = requests.post(f"{API}/chat", json={"message": "What is compound interest?", "session_id": "audit_faq3", "use_bert": True, "use_gemini": False}).json()
print("FAQ (compound interest):")
p("", r)

print()
print("=" * 70)
print("AUDIT 4: LOCAL DATA (CSV stock + exchange rate)")
print("=" * 70)
r = requests.post(f"{API}/chat", json={"message": "Price of AAPL", "session_id": "audit_stock", "use_bert": True, "use_gemini": False}).json()
print("Stock AAPL (Gemini OFF):")
p("", r)
r = requests.post(f"{API}/chat", json={"message": "USD to INR", "session_id": "audit_fx", "use_bert": True, "use_gemini": False}).json()
print("Exchange USD->INR (Gemini OFF):")
p("", r)

print()
print("=" * 70)
print("AUDIT 5: COMPLEX/MULTI QUERY")
print("=" * 70)
r = requests.post(f"{API}/chat", json={"message": "Explain inflation and show me AAPL stock price", "session_id": "audit_cx1", "use_bert": True, "use_gemini": False}).json()
print("Complex query (gemini OFF):")
p("", r)
r = requests.post(f"{API}/chat", json={"message": "compare SIP vs lump sum and check google stock", "session_id": "audit_cx2", "use_bert": True, "use_gemini": False}).json()
print("Complex multi-query (gemini OFF):")
p("", r)

print()
print("=" * 70)
print("AUDIT 6: EDGE CASES")
print("=" * 70)
# Empty-ish message
try:
    r = requests.post(f"{API}/chat", json={"message": " ", "session_id": "audit_edge1", "use_bert": True}).json()
    print("Empty message:", r.get("detail", r.get("response", "?"))[:80])
except Exception as e:
    print("Empty message error:", str(e)[:80])

# Very long message
long_msg = "explain " * 200
r = requests.post(f"{API}/chat", json={"message": long_msg[:1999], "session_id": "audit_edge2", "use_bert": True, "use_gemini": False}).json()
print("Very long message:", r.get("response", "?")[:80])

# Rapid fire — same session, 3 msgs fast
sid = "audit_rapid"
r = requests.post(f"{API}/chat", json={"message": "hello", "session_id": sid, "use_bert": True}).json()
print("Rapid 1 (hello):", r.get("response", "?")[:60])
r = requests.post(f"{API}/chat", json={"message": "AAPL price", "session_id": sid, "use_bert": True}).json()
print("Rapid 2 (stock):", r.get("response", "?")[:60])
r = requests.post(f"{API}/chat", json={"message": "bye", "session_id": sid, "use_bert": True}).json()
print("Rapid 3 (bye):", r.get("response", "?")[:60])

# Missing entities — ask for stock without ticker
r = requests.post(f"{API}/chat", json={"message": "show me the stock price", "session_id": "audit_edge3", "use_bert": True}).json()
print("Missing ticker:", r.get("response", "?")[:80])

# Server restart test — old session ID after restart
print("Old session re-use (after server restart): session state would be lost (IN-MEMORY)")

print()
print("AUDIT COMPLETE")
