#!/usr/bin/env python3
"""One-off probe of the Whiteout Stats API (Frosty SvS endpoints). Writes data/probe/frosty.json with the raw answers
(capped) and prints a short overview. About 30 requests. Only the standard library. Key from WOS_API_KEY (GitHub secret)."""
import json, os, sys, time, urllib.request, urllib.error

BASE = os.environ.get('WOS_API_BASE', 'https://api.whiteoutstats.com/v1')
KEY = os.environ.get('WOS_API_KEY', '').strip()
KID = os.environ.get('WOS_KID', '646')
OUT = os.environ.get('WOS_OUT', 'data/probe')
CAP = 40000
if not KEY: sys.exit('WOS_API_KEY is not set.')
res = {}


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
    if len(body) > CAP: data = {'_truncated': True, 'text': body[:CAP]}
    res[path] = {'status': status, 'data': data}
    keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
    print(f'{status}  {path}  -> {keys}  ({len(body)} bytes)', flush=True)
    time.sleep(1.2)
    return data


call('/usage')
call(f'/states/{KID}')
sv = call(f'/states/{KID}/svs')
call(f'/states/{KID}/svs/scores')
mm = call('/svs/matchups')
call(f'/states/{KID}/events')
# past events: try a season parameter in several spellings
prev = sv.get('previous_season') if isinstance(sv, dict) else None
cur = sv.get('season') if isinstance(sv, dict) else None
for s in [x for x in (prev, (cur - 2) if isinstance(cur, int) else None) if x]:
    for p in (f'/states/{KID}/svs?season={s}', f'/states/{KID}/svs/scores?season={s}', f'/states/{KID}/svs/{s}', f'/states/{KID}/svs/scores/{s}', f'/svs/matchups?season={s}'):
        call(p)
# is there a per-player / per-alliance SvS board?
for b in ('svs', 'svs_points', 'svs_score', 'svs_prep', 'state_of_power', 'nonexistent_board_test'):
    call(f'/states/{KID}/ranks?board={b}&limit=3')
# a player, to see which includes exist
try:
    pid = next(iter(json.load(open('data/players.json'))['players']))
    call(f'/players/{pid}?include=base,ranks,events,svs')
except Exception as e:
    print('player probe skipped:', e)
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'frosty.json'), 'w', encoding='utf-8') as f: json.dump(res, f, ensure_ascii=False, indent=1)
print('written:', os.path.join(OUT, 'frosty.json'))
