#!/usr/bin/env python3
"""One-off probe: how many of a state's alliances can be found by combining ALL boards (each board is capped at 100 rows)?
Compares the union with `alliance_count` of the state and checks that an alliance request returns the complete roster.
Target state: WOS_KID (default 622). Writes data/probe/<kid>/coverage.json (alliance list + counts). About 22 requests.
Key from WOS_API_KEY (GitHub secret). Standard library only."""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse

BASE = os.environ.get('WOS_API_BASE', 'https://api.whiteoutstats.com/v1')
KEY = os.environ.get('WOS_API_KEY', '').strip()
KID = os.environ.get('WOS_KID', '622')
OUT = os.environ.get('WOS_OUT', f'data/probe/{KID}')
if not KEY: sys.exit('WOS_API_KEY is not set.')


def call(path):
    req = urllib.request.Request(BASE + path, headers={'Authorization': 'Bearer ' + KEY, 'User-Agent': 'state646-probe/1.0', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=40) as r: status, body = r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:
        status, body = 'error', str(e)
    try: data = json.loads(body)
    except Exception: data = None
    time.sleep(1.1)
    return status, data


st, d = call(f'/states/{KID}')
state = (d or {}).get('state') or {}
total = state.get('alliance_count')
slugs = [b['key'] for b in state.get('board_totals', []) if b.get('key')]
print(f'state {KID}: alliance_count={total} player_count={state.get("player_count")}  boards: {slugs}')
found = {}      # aid -> {abbr, name, via:set}
per_board = {}
for slug in slugs:
    st, d = call(f'/states/{KID}/ranks?board={slug}&limit=100')
    rows = ((d or {}).get('boards') or [{}])[0].get('rows') or []
    new = 0
    for r in rows:
        aid = r.get('aid')
        abbr = r.get('abbr') or r.get('alliance_abbr')
        if not aid: continue
        if aid not in found: found[aid] = {'abbr': abbr, 'name': r.get('name') or r.get('alliance_name'), 'via': []}; new += 1
        found[aid]['via'].append(slug)
    per_board[slug] = {'status': st, 'rows': len(rows), 'new_alliances': new}
    print(f'  {slug:18} status={st} rows={len(rows):3} new alliances={new:3}  total so far={len(found)}', flush=True)
print(f'UNION: {len(found)} alliances of {total}  ({100 * len(found) / total:.0f} %)' if total else f'UNION: {len(found)}')

# roster check: does ONE alliance request return the complete member list? (largest and a tiny alliance)
checks = []
cand = [a for a in found.values() if a['abbr']]
for a in cand[:1] + cand[-1:]:
    st, d = call(f'/alliances/{KID}/{urllib.parse.quote(a["abbr"], safe="")}?include=info,roster')
    al = (d or {}).get('alliance') or {}
    mem = (d or {}).get('members') or []
    checks.append({'abbr': a['abbr'], 'status': st, 'count_in_info': al.get('count'), 'members_returned': len(mem), 'member_count': (d or {}).get('member_count')})
    print('  roster', checks[-1])
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'coverage.json'), 'w', encoding='utf-8') as f:
    json.dump({'kid': KID, 'alliance_count': total, 'found': len(found), 'per_board': per_board, 'roster_checks': checks,
               'alliances': [{'aid': k, **v} for k, v in found.items()]}, f, ensure_ascii=False, indent=1)
print('written:', os.path.join(OUT, 'coverage.json'))
