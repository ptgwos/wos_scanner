#!/usr/bin/env python3
"""State Power: daily pull of the state totals and the top-100 boards (Whiteout Stats API).

Writes   data/power.json              latest status (read by statepower.html)
         data/power/YYYY-MM-DD.json   one snapshot per day (history), date = day the game captured the boards (UTC)

Cost per run: 1 request (state) + 20 requests (boards) = 21 of the 5000 per day.
Only the Python standard library. The key comes from the environment variable WOS_API_KEY (GitHub secret).
If a board fails, the previous values of that board are kept and the key is listed under "stale".
"""
import json, os, sys, time, urllib.request, urllib.error

BASE = os.environ.get('WOS_API_BASE', 'https://api.whiteoutstats.com/v1')
KID = os.environ.get('WOS_KID', '646')
UA = 'state646-board/1.0 (+https://www.state646.com)'
PAUSE = float(os.environ.get('WOS_PAUSE', '1.2'))
OUT = os.environ.get('WOS_OUT', 'data')
BOARDS = ['personal_power', 'kills', 'single_hero', 'hero_total', 'troop_power', 'building_power', 'research_power',
          'chief_gear', 'chief_charm', 'pet_power', 'island_prosperity',
          'land_of_heroes', 'cave_of_monsters', 'charm_mine', 'research_center', 'gear_forge', 'gaia_heart',
          'state_transfer', 'labyrinth', 'master_power']
KEY = os.environ.get('WOS_API_KEY', '').strip()
if not KEY:
    sys.exit('WOS_API_KEY is not set.')


def get(path):
    """GET with retries (429 -> wait, 5xx -> retry). Returns parsed JSON or None."""
    for attempt in range(4):
        req = urllib.request.Request(BASE + path, headers={'Authorization': 'Bearer ' + KEY, 'User-Agent': UA, 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 20
                try: wait = max(5, min(70, int(e.headers.get('Retry-After', '20'))))
                except Exception: pass
                print(f'  429 on {path}, waiting {wait}s', flush=True); time.sleep(wait); continue
            if e.code >= 500:
                time.sleep(5 * (attempt + 1)); continue
            print(f'  HTTP {e.code} on {path}', flush=True); return None
        except Exception as e:
            print(f'  error on {path}: {e}', flush=True); time.sleep(5 * (attempt + 1))
    return None


def load(p):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except Exception:
        return None


old = load(os.path.join(OUT, 'power.json')) or {}
if old.get('sample'): old = {}                      # never carry sample data over
boards, players, captured, stale = {}, {}, [], []

st = get(f'/states/{KID}')
state = None
if st and isinstance(st.get('state'), dict):
    s = st['state']
    state = {k: s.get(k) for k in ('player_count', 'active_7d', 'alliance_count', 'power')}
    for b in s.get('board_totals') or []:
        state[b.get('key')] = b.get('total')
else:
    state = old.get('state'); stale.append('state')
time.sleep(PAUSE)

for slug in BOARDS:
    d = get(f'/states/{KID}/ranks?board={slug}&limit=100')
    b = None
    for x in (d or {}).get('boards') or []:
        if x.get('key') == slug: b = x
    if not b or not b.get('rows'):
        stale.append(slug)
        if slug in (old.get('boards') or {}): boards[slug] = old['boards'][slug]
        time.sleep(PAUSE); continue
    if b.get('captured_at'): captured.append(float(b['captured_at']))
    rows = []
    for r in b['rows']:
        uid = r.get('uid')
        if not uid: continue
        rows.append([uid, r.get('score'), r.get('rank')])
        players[str(uid)] = {'n': r.get('nick_name') or '?', 'a': r.get('alliance_abbr') or '', 'v': r.get('avatar_url') or '',
                             'c': r.get('chief_id') or None}
    boards[slug] = rows
    time.sleep(PAUSE)

# players that only live in old (stale) boards keep their names
for slug in stale:
    for uid, _s, _r in boards.get(slug, []):
        if str(uid) not in players and str(uid) in (old.get('players') or {}): players[str(uid)] = old['players'][str(uid)]

fresh = [k for k in BOARDS if k in boards and k not in stale]
if not fresh and not state:
    sys.exit('Nothing could be fetched, files left as they were.')

cap = max(captured) if captured else old.get('captured')
out = {'sample': False, 'kid': int(KID), 'captured': cap, 'updated': int(time.time()), 'stale': stale,
       'state': state, 'boards': boards, 'players': players}

if old.get('captured') == cap and not stale and old.get('boards') == boards:
    print('Boards unchanged since the last run, nothing written.'); sys.exit(0)

os.makedirs(os.path.join(OUT, 'power'), exist_ok=True)
day = time.strftime('%Y-%m-%d', time.gmtime(cap)) if cap else time.strftime('%Y-%m-%d', time.gmtime())
txt = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
snap = dict(out); snap['players'] = {k: {'n': v['n'], 'a': v['a'], 'c': v.get('c')} for k, v in players.items()}   # history: no avatar URLs
for path, data in ((os.path.join(OUT, 'power.json'), txt), (os.path.join(OUT, 'power', day + '.json'), json.dumps(snap, ensure_ascii=False, separators=(',', ':')))):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: f.write(data)
    os.replace(tmp, path)
print(f'OK {day}: {len(fresh)}/{len(BOARDS)} boards, {len(players)} players' + (f', stale: {stale}' if stale else ''))
