"""Inspect the shape of the raw HeyReach conversation dump."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT, "outputs", "_raw_heyreach_conversations.json")

with open(path) as f:
    convos = json.load(f)

print(f"total conversations: {len(convos)}")
c = convos[0]
print("\nCONVERSATION KEYS:")
for k, v in c.items():
    prev = json.dumps(v, default=str)
    print(f"  {k}: {prev[:160]}")

msgs = c.get("messages") or []
print(f"\nmessages in first convo: {len(msgs)}")
if msgs:
    print("MESSAGE KEYS:")
    for k, v in msgs[0].items():
        print(f"  {k}: {json.dumps(v, default=str)[:160]}")
