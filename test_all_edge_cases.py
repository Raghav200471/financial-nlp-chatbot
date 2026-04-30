import requests
import json
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

API = "http://127.0.0.1:8000/api"

def test_chat(msg, sid, use_bert=True, use_gemini=True, user_context=None):
    payload = {
        "message": msg,
        "session_id": sid,
        "use_bert": use_bert,
        "use_gemini": use_gemini
    }
    if user_context:
        payload["user_context"] = user_context

    try:
        r = requests.post(f"{API}/chat", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def p(label, res):
    print(f"\n[{label}]")
    if "response" in res:
        print(f"Intent: {res.get('intent', 'none')}")
        print(f"Entities: {res.get('entities', [])}")
        resp = res['response'].replace('\n', ' | ')
        print(f"Response: {resp[:150]}...")
        if "I don't have enough information" in res['response'] or "Gemini API Quota Exceeded" in res['response']:
            print(">>> FAILED: Gemini fallback triggered! <<<")
            return False
        return True
    else:
        print(f"Error: {res}")
        return False

successes = 0
total = 0

print("=========================================")
print("  EDGE CASE BATTERY TEST")
print("=========================================")

# Test 1: Conceptual + Math Overlap (The user's exact bug)
total += 1
print("\n--- Test 1: Conceptual + Math Overlap ---")
r1 = test_chat("okay what is my emi for 2 years at 5% for 10 lakhs ruppes", sid="test_1", user_context={"goal": "save money"})
if p("What is my EMI... ruppes", r1):
    # Should calculate immediately since ruppes is extracted, OR ask for something else
    # Wait, 'ruppes' should be extracted as CURRENCY now. So it should execute.
    if r1.get('intent') == 'calculate_emi' and 'Monthly EMI' in r1.get('response', ''):
        successes += 1
    else:
        print(">>> FAILED: Did not calculate EMI correctly <<<")

# Test 2: Extreme Typos
total += 1
print("\n--- Test 2: Extreme Typos ---")
r2 = test_chat("convert 1000 dolars to inr", sid="test_2")
if p("1000 dolars to inr", r2):
    if r2.get('intent') == 'get_exchange_rate' and '1000.0 USD' in r2.get('response', ''):
        successes += 1
    else:
        print(">>> FAILED: Did not extract dolars properly <<<")

# Test 3: Missing Slots + RAG Override
total += 1
print("\n--- Test 3: Missing Slots + RAG Override ---")
r3 = test_chat("Calculate EMI for 10 lakh at 8.5% for 20 years", sid="test_3", user_context={"goal": "buy house"})
p("Missing Currency", r3)
r4 = test_chat("inr", sid="test_3", user_context={"goal": "buy house"})
if p("Fill missing currency (RAG ON)", r4):
    if r4.get('intent') == 'calculate_emi' and 'Monthly EMI' in r4.get('response', ''):
        successes += 1
    else:
        print(">>> FAILED: RAG context hijacked the slot fill! <<<")

# Test 4: Context Switching
total += 1
print("\n--- Test 4: Context Switching ---")
r5 = test_chat("Calculate EMI for 10 lakh", sid="test_4")
p("Start EMI", r5)
r6 = test_chat("hello", sid="test_4")
p("Interrupt with hello", r6)
if r6.get('intent') == 'greeting':
    successes += 1
else:
    print(">>> FAILED: Did not switch context to greeting <<<")

# Test 5: Garbage Data Fallback
total += 1
print("\n--- Test 5: Garbage Data Fallback ---")
r7 = test_chat("Calculate EMI for xyz lakhs", sid="test_5")
p("Garbage amount", r7)
if r7.get('intent') == 'calculate_emi' and r7.get('action') == 'ask_slot':
    successes += 1
else:
    print(">>> FAILED: Handled garbage data improperly <<<")


print("\n=========================================")
print(f"  TESTS PASSED: {successes}/{total}")
print("=========================================")
if successes != total:
    sys.exit(1)
