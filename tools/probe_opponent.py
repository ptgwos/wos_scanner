#!/usr/bin/env python3
"""One-off probe: how can ALL alliances (and then all players) of another state be listed? Target state from WOS_KID (default 622).
Writes data/probe/opponent.json (raw answers, capped) and prints an overview. About 12 requests. Key from WOS_API_KEY (GitHub secret)."""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse

BASE = os.environ.get('WOS_API_BASE', 'https://api.whiteoutstats.com/v1')
KEY = os.environ.get('WOS_API_KEY', '').strip()
KID = os.environ.get('WOS_KID', '622')
OUT = os.environ.get('WOS_OUT', 'data/probe')
CAP = 30000
if not KEY: sys.exit('WOS_API_KEY is not set.')
res = {}


def find_list(d):
    """first list of dicts inside the answer (for counting rows)"""
    if isinstance(d, list): return d
    if isinstance(d, dict):
        for v in d.values():
            r = find_list(v)
            if isinstance(r, list) and r and isinstance(r[0], dict): return r
    return None


def call(path):
    req = urllib.request.Request(BASE + path, headers={'Authorization': 'Bearer ' + KEY, 'User-Agent': 'state646-probe/1.0', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=40) as r: status, body = r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:
        status, body = 'error', str(e)
    try: data = json.loads(body)
    except Exception: data = body[:CAP]
    rows = find_list(data)
    keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
    print(f'{status}  {path}  -> {keys}  rows={len(rows) if rows else "-"}  ({len(body)} bytes)', flush=True)
    res[path] = {'status': status, 'rows': len(rows) if rows else None, 'data': data if len(body) <= CAP else {'_truncated': True, 'text': body[:CAP]}}
    time.sleep(1.2)
    return data


st = call(f'/states/{KID}')
try: print('  alliance_count =', st['state']['alliance_count'], ' player_count =', st['state']['player_count'])
except Exception: pass
a100 = call(f'/states/{KID}/ranks?board=alliance_power&limit=100')
call(f'/states/{KID}/ranks?board=alliance_power&limit=200')
call(f'/states/{KID}/ranks?board=alliance_power&limit=100&offset=100')
call(f'/states/{KID}/ranks?board=alliance_power&limit=100&page=2')
call(f'/states/{KID}/ranks?board=alliance_kills&limit=100')
call(f'/states/{KID}/alliances')
call(f'/states/{KID}/alliances?limit=500')
call(f'/states/{KID}/ranks?board=personal_power&limit=100')
# one alliance with its roster (by tag)
rows = find_list(a100) or []
if rows:
    print('first row of alliance_power:', json.dumps(rows[0], ensure_ascii=False)[:300])
    tag = next((rows[0].get(k) for k in ('abbr', 'tag', 'alliance_abbr') if rows[0].get(k)), None)
    if tag: call(f'/alliances/{KID}/{urllib.parse.quote(tag, safe="")}?include=info,roster')
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'opponent.json'), 'w', encoding='utf-8') as f: json.dump(res, f, ensure_ascii=False, indent=1)
print('written:', os.path.join(OUT, 'opponent.json'))
