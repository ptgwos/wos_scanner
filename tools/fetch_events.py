#!/usr/bin/env python3
"""Fetch the event calendar of one state (Whiteout Stats API, Frosty key needed).
Reads the key ONLY from the environment (GitHub secret WOS_API_KEY); never prints or stores it.
Writes data/events_raw.json (untouched API answer) and data/events.json (flat, sorted list with ISO times)
and prints a readable table to the log."""
import os, sys, json, datetime, urllib.request, urllib.error

KID = int(os.environ.get("KID", "646"))
BASE = os.environ.get("API_BASE", "https://api.whiteoutstats.com").rstrip("/")
OUT = os.environ.get("OUT_DIR", "data")
key = os.environ.get("WOS_API_KEY", "").strip()
if not key:
    sys.exit("WOS_API_KEY is not set (GitHub secret missing).")

req = urllib.request.Request(f"{BASE}/v1/states/{KID}/events",
                             headers={"Authorization": "Bearer " + key, "Accept": "application/json", "User-Agent": "state646-events/1"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = json.loads(r.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    try:
        msg = json.loads(e.read().decode("utf-8")).get("error", "")
    except Exception:
        msg = ""
    sys.exit(f"API error: HTTP {e.code} {msg}")
except Exception as e:
    sys.exit(f"Request failed: {type(e).__name__}")

if not raw.get("ok"):
    sys.exit("API answered ok=false: " + str(raw.get("error")))

def iso(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts is not None else None

flat = []
for cat in raw.get("categories", []):
    for ev in cat.get("events", []):
        flat.append({"name": ev.get("name"), "category": ev.get("category") or cat.get("name"), "when": ev.get("when"),
                     "begin": iso(ev.get("begin_ts")), "end": iso(ev.get("end_ts")),
                     "begin_ts": ev.get("begin_ts"), "end_ts": ev.get("end_ts")})
flat.sort(key=lambda e: (e["begin_ts"] or 0, e["name"] or ""))
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "events_raw.json"), "w", encoding="utf-8") as f:
    json.dump(raw, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "events.json"), "w", encoding="utf-8") as f:
    json.dump({"kid": KID, "api_date": raw.get("date"), "fetched_at": now, "count": len(flat), "events": flat}, f, ensure_ascii=False, indent=1)

print(f"State {KID}: api date {raw.get('date')}, {len(flat)} events, categories: {[c.get('name') for c in raw.get('categories', [])]}")
if flat:
    print(f"Earliest begin: {min(e['begin'] for e in flat if e['begin'])}   Latest end: {max(e['end'] for e in flat if e['end'])}")
print("-" * 100)
for e in flat:
    print(f"{(e['category'] or '')[:14]:14} | {(e['name'] or '')[:34]:34} | {e['begin']} -> {e['end']} | {e['when']}")
