#!/usr/bin/env python3
"""Probe: how can ALL alliances of a state be listed via the Whiteout Stats API?
Tries a few likely list endpoints, the ranking boards with bigger limits, and fetching an alliance by its id.
Writes data/alliances_probe.json (statuses, top-level keys, one sample item per answer) and prints a short report.
The key is read ONLY from the environment (GitHub secret WOS_API_KEY) and is never printed or stored."""
import os, sys, json, time, urllib.request, urllib.error

BASE = os.environ.get("API_BASE", "https://api.whiteoutstats.com/v1").rstrip("/")
KID = os.environ.get("KID", "646")
KEY = os.environ.get("WOS_API_KEY", "").strip()
if not KEY:
    sys.exit("WOS_API_KEY is not set (GitHub secret missing).")
PAUSE = 1.2

def get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + KEY, "Accept": "application/json", "User-Agent": "state646-probe/1"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read().decode("utf-8"))
        except Exception: body = None
        return e.code, body
    except Exception as e:
        return 0, {"error": type(e).__name__}

def shape(x, depth=0):
    """Compact description of a JSON value: keys, list lengths, first item."""
    if isinstance(x, dict):
        return {k: (shape(v, depth + 1) if depth < 2 else type(v).__name__) for k, v in list(x.items())[:25]}
    if isinstance(x, list):
        return {"_list": len(x), "first": shape(x[0], depth + 1) if x and depth < 3 else None}
    return x if isinstance(x, (int, float, bool)) or x is None else (x[:40] if isinstance(x, str) else str(type(x)))

paths = [
    f"/states/{KID}",
    f"/states/{KID}/alliances",
    f"/states/{KID}/alliances?limit=500",
    f"/alliances/{KID}",
    f"/alliances/{KID}?limit=500",
    f"/alliances?kid={KID}",
    f"/states/{KID}?include=alliances",
]
res = []
for p in paths:
    st, body = get(p)
    res.append({"path": p, "status": st, "shape": shape(body)})
    print(f"{st}  {p}", flush=True); time.sleep(PAUSE)

# ranking boards with bigger limits: how many alliances can we see?
found = {}
for board in ("alliance_power", "alliance_kills"):
    for lim in (100, 300, 1000):
        p = f"/states/{KID}/ranks?board={board}&limit={lim}"
        st, body = get(p)
        rows = []
        for b in ((body or {}).get("boards") or []):
            if b.get("key") == board: rows = b.get("rows") or []
        res.append({"path": p, "status": st, "rows": len(rows), "row_keys": sorted(rows[0].keys()) if rows else None})
        print(f"{st}  {p}  -> {len(rows)} rows", flush=True)
        for r in rows:
            ab = r.get("alliance_abbr") or r.get("abbr") or r.get("tag")
            if ab: found[ab] = r.get("alliance_name") or r.get("name") or ""
        time.sleep(PAUSE)
        if len(rows) < lim: break   # the board has no more rows than that, bigger limits are pointless

# one alliance by id (the ids look like <kid>000001 ...)
for n in (1, 2, 3):
    aid = int(KID) * 1000000 + n
    for p in (f"/alliances/{KID}/{aid}?include=info", f"/alliances/{aid}?include=info"):
        st, body = get(p)
        res.append({"path": p, "status": st, "shape": shape(body)})
        print(f"{st}  {p}", flush=True); time.sleep(PAUSE)

os.makedirs("data", exist_ok=True)
with open("data/alliances_probe.json", "w", encoding="utf-8") as f:
    json.dump({"kid": KID, "results": res, "alliances_seen_in_boards": found}, f, ensure_ascii=False, indent=1)
print(f"Alliances seen in the alliance boards: {len(found)}")
