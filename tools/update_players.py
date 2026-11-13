#!/usr/bin/env python3
"""Fetch the member lists of the State 646 alliances from the Whiteout Stats API
and write data/players.json + avatars/<id>.webp (small copies of the profile pictures).

- one API request per alliance (the roster holds all members), 15 requests per run
- data/players.json feeds svslb.html (avatars) and roster.html (members, power)
- API key comes from the environment variable WOS_API_KEY (never from a file)
- players that are not in any fetched alliance keep their last known entry
- if an alliance cannot be fetched, its players keep their last known entry
- data/history.json: log of alliance changes (who moved from which alliance to which, when)
- data/usage.json: remaining API allowance of the day (shown in access.html); changes with every run
- which alliances are fetched is chosen in access.html (Supabase table roster_alliances, read with the public URL/key from
  eventplan-config.js, or from the optional env variables SUPABASE_URL / SUPABASE_KEY); fallback = the last data/alliances.json, then DEFAULT_TAGS
- data/alliances_known.json: all alliances seen in the two alliance rankings (refreshed about once a day, 2 requests)
- data/alliances.json: the alliances that are fed right now (read by roster.html and the planners)
- nothing else is written when nothing changed, so there is no commit noise
"""
import io, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error, datetime, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import wos_history

API = os.environ.get('WOS_API_BASE', 'https://api.whiteoutstats.com/v1')
KID = 646
# case sensitive on purpose: TBR, TbR and tbr are three different alliances
DEFAULT_TAGS = ['AIR', 'BLP', 'TBR', 'TbR', 'osm', 'OMG', 'PKB', 'GYN', 'EVL', 'HYg', 'KOJ', 'NEW', 'DFT', 'HOS', 'tbr']
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'players.json'
HIST = ROOT / 'data' / 'history.json'
AV = ROOT / 'avatars'
FEED = ROOT / 'data' / 'alliances.json'
KNOWN = ROOT / 'data' / 'alliances_known.json'
SB_URL = os.environ.get('SUPABASE_URL', '').strip().rstrip('/')
SB_KEY = os.environ.get('SUPABASE_KEY', '').strip()
if not (SB_URL and SB_KEY):
    # no secrets needed: the pages already use the public URL and key from eventplan-config.js (window.EP_CONFIG = {url, key})
    try:
        import re
        cfg = (ROOT / 'eventplan-config.js').read_text(encoding='utf-8')
        mu = re.search(r'''\burl\b["']?\s*:\s*["']([^"']+)["']''', cfg); mk = re.search(r'''\bkey\b["']?\s*:\s*["']([^"']+)["']''', cfg)
        if mu and mk: SB_URL, SB_KEY = mu.group(1).strip().rstrip('/'), mk.group(1).strip()
    except Exception:
        pass
SIZE = 64          # px, square
MISS_LIMIT = 3     # days in a row without a picture before the stored one is removed
PAUSE = 1.2        # seconds between API requests (limit is 60 per minute)

key = os.environ.get('WOS_API_KEY', '').strip()
if not key:
    sys.exit('WOS_API_KEY is not set')

UA = 'state646-board/1.0 (+https://www.state646.com)'

def get(url, headers=None, tries=4):
    for i in range(tries):
        h = {'User-Agent': UA}
        h.update(headers or {})
        req = urllib.request.Request(url, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                wait = int(e.headers.get('Retry-After') or 20)
                print(f'  429, waiting {wait}s', flush=True); time.sleep(min(wait, 90)); continue
            try: body = e.read().decode('utf-8', 'replace')[:300]
            except Exception: body = ''
            print(f'  HTTP {e.code}: {body}', flush=True)
            raise
        except urllib.error.URLError:
            if i < tries - 1: time.sleep(5); continue
            raise

def write_usage(base, key, ua, path, by):
    """data/usage.json: remaining API allowance (GET /usage does not count against the limits). Never breaks the run."""
    try:
        req = urllib.request.Request(base + '/usage', headers={'Authorization': 'Bearer ' + key, 'User-Agent': ua, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode('utf-8'))
        dl = d.get('daily') or {}
        if not d.get('ok') or not isinstance(dl.get('remaining'), int): return
        out = {'frosty': bool(d.get('frosty')), 'daily': {k: dl.get(k) for k in ('limit', 'used', 'remaining', 'resets_at')},
               'minute_limit': (d.get('minute') or {}).get('limit'), 'updated': int(time.time()), 'by': by}
        os.makedirs(os.path.dirname(str(path)) or '.', exist_ok=True)
        tmp = str(path) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f: json.dump(out, f, separators=(',', ':'))
        os.replace(tmp, str(path))
        print(f"usage: {dl.get('remaining')} of {dl.get('limit')} requests left today", flush=True)
    except Exception as e:
        print(f'usage skipped: {e}', flush=True)


def read_json(path):
    try: return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    except Exception: return None

def write_json_if_changed(path, obj, ignore=('updated',)):
    old_j = read_json(path)
    strip = lambda o: json.dumps({k: v for k, v in (o or {}).items() if k not in ignore}, sort_keys=True, ensure_ascii=False)
    if old_j is not None and strip(old_j) == strip(obj): return False
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True), encoding='utf-8')
    return True

STYLE = {'colors': {}, 'battle': [], 'ok': False}

def load_selection():
    """Tags to fetch: the ticked alliances from Supabase; if that is not possible the last feed file, then the default list."""
    if SB_URL and SB_KEY:
        try:
            h = {'apikey': SB_KEY, 'Accept': 'application/json', 'User-Agent': UA}
            if SB_KEY.startswith('eyJ'): h['Authorization'] = 'Bearer ' + SB_KEY
            rows = json.loads(get(SB_URL + '/rest/v1/roster_alliances?select=tag,selected,color,battle&order=tag', h).decode('utf-8'))
            tags = [r['tag'] for r in rows if r.get('tag') and r.get('selected')]
            if tags:
                # tag colours and "battle alliance" flags set in access.html (used by the pages with a fallback of their own)
                STYLE['colors'] = {r['tag']: r['color'] for r in rows if r.get('tag') and re.fullmatch(r'#[0-9a-fA-F]{6}', r.get('color') or '')}
                STYLE['battle'] = sorted(r['tag'] for r in rows if r.get('tag') and r.get('battle'))
                STYLE['ok'] = True
                return tags, 'supabase'
            print('selection: Supabase list is empty - using the fallback', flush=True)
        except Exception as e:
            print(f'selection: Supabase not reachable ({type(e).__name__}) - using the fallback', flush=True)
    f = read_json(FEED)
    if f and f.get('tags'): return list(f['tags']), 'last feed file'
    return list(DEFAULT_TAGS), 'default list'

def discover(known_old):
    """All alliances visible in the two alliance rankings (top 100 each). Nothing is ever removed, only last_seen is updated."""
    day = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    kn = dict((known_old or {}).get('alliances', {}))
    ok_boards = 0
    for board in ('alliance_power', 'alliance_kills'):
        try:
            d = json.loads(get(f'{API}/states/{KID}/ranks?board={board}&limit=100', {'Authorization': 'Bearer ' + key, 'Accept': 'application/json'}))
        except Exception as e:
            print(f'discover {board}: failed ({type(e).__name__})', flush=True); continue
        for b in d.get('boards') or []:
            if b.get('key') != board: continue
            ok_boards += 1
            for r in b.get('rows') or []:
                t = r.get('abbr')
                if not t: continue
                e = kn.get(t, {'first': day})
                e.update({'name': r.get('name') or e.get('name', ''), 'aid': r.get('aid'), 'leader': r.get('leader_name') or e.get('leader', ''),
                          'count': r.get('member_count', e.get('count')), 'last': day})
                if board == 'alliance_power': e['power'] = r.get('score'); e['rank'] = r.get('rank')
                kn[t] = e
        time.sleep(PAUSE)
    return kn, ok_boards

TAGS, SEL_SRC = load_selection()
prev_feed = read_json(FEED) or {}
prev_tags = set(prev_feed.get('tags') or DEFAULT_TAGS)
print(f'alliances to fetch: {len(TAGS)} (source: {SEL_SRC})', flush=True)
known_old = read_json(KNOWN)
if not known_old or time.time() - (known_old.get('ts') or 0) > 20 * 3600:
    kn, nb = discover(known_old)
    if nb:
        KNOWN.parent.mkdir(parents=True, exist_ok=True)
        KNOWN.write_text(json.dumps({'kid': KID, 'ts': int(time.time()), 'updated': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                                     'alliances': kn}, ensure_ascii=False, separators=(',', ':'), sort_keys=True), encoding='utf-8')
    print(f'discovery: {len(kn)} alliances known', flush=True); known_old = read_json(KNOWN) or known_old
    time.sleep(PAUSE)
known = (known_old or {}).get('alliances', {})

old = json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else {'alliances': {}, 'players': {}}
players = {k: dict(v) for k, v in old.get('players', {}).items()}
alliances = dict(old.get('alliances', {}))
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
ok, failed, missing = [], [], []
seen_now = {}

for n, tag in enumerate(TAGS):
    if n: time.sleep(PAUSE)
    url = f"{API}/alliances/{KID}/{urllib.parse.quote(tag, safe='')}?include=info,roster"
    try:
        d = json.loads(get(url, {'Authorization': 'Bearer ' + key, 'Accept': 'application/json'}))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f'{tag}: NOT FOUND in state {KID} - check the tag (upper/lower case counts)', flush=True); missing.append(tag); continue
        print(f'{tag}: FAILED ({e}) - keeping the old entries', flush=True); failed.append(tag); continue
    except Exception as e:
        print(f'{tag}: FAILED ({e}) - keeping the old entries', flush=True); failed.append(tag); continue
    a = d.get('alliance') or {}
    members = d.get('members') or []
    ids = [str(m.get('chief_id') or m.get('fid')) for m in members if (m.get('chief_id') or m.get('fid'))]
    alliances[tag] = {'name': a.get('name', ''), 'aid': a.get('aid'), 'count': d.get('member_count', len(members)),
                      'power': a.get('power'), 'power_rank': a.get('power_rank'), 'leader': a.get('leader_name', ''),
                      'm': ids}   # m = current members (ids) as of the last successful fetch
    for m in members:
        cid = str(m.get('chief_id') or m.get('fid') or '')
        if not cid: continue
        seen_now[cid] = tag
        p = players.get(cid, {})
        p.update({'n': m.get('nick_name', p.get('n', '')), 'a': tag, 'r': m.get('alliance_rank_label', ''),
                  'p': m.get('power'), 'f': m.get('furnace_level'), 's': now})
        if m.get('avatar_url'):
            p['u'] = m['avatar_url']; p.pop('nm', None); p.pop('nd', None)
        elif p.get('u'):
            # the API sends no picture (default in-game avatar): keep the old one for 2 days, drop it on the 3rd day in a row
            if p.get('nd') != now:          # count each missing picture once per day, however often the script runs
                p['nm'] = p.get('nm', 0) + 1; p['nd'] = now
            if p['nm'] >= MISS_LIMIT:
                for k in ('u', 'au', 'nm', 'nd'): p.pop(k, None)
                try: (AV / f'{cid}.webp').unlink()
                except FileNotFoundError: pass
                print(f'  avatar removed: {cid} {p.get("n")}', flush=True)
        players[cid] = p
    print(f'{tag}: {len(members)} members', flush=True); ok.append(tag)

# profile pictures: download only when the URL is new
dl = 0
if ok:
    try:
        from PIL import Image
    except ImportError:
        Image = None; print('Pillow missing, pictures skipped')
    if Image:
        AV.mkdir(parents=True, exist_ok=True)
        for cid, p in players.items():
            u = p.get('u')
            if not u: continue
            f = AV / f'{cid}.webp'
            if p.get('au') == u and f.exists(): continue
            try:
                im = Image.open(io.BytesIO(get(u))).convert('RGBA')
                w, h = im.size; s = min(w, h)
                im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((SIZE, SIZE), Image.LANCZOS)
                im.save(f, 'WEBP', quality=80, method=6)
                p['au'] = u; dl += 1
            except Exception as e:
                print(f'  picture {cid} failed: {e}', flush=True)
            time.sleep(0.05)

new = {'alliances': alliances, 'players': players}

# alliance-change log (alliances that failed keep their old member list, so they produce no entries)
try:
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    first_time = [t for t in ok if t not in old.get('alliances', {}) or t not in prev_tags]   # newly ticked: no 'moves' against old data
    ents = wos_history.diff(old.get('alliances', {}), alliances, {k: v.get('n', '') for k, v in players.items()},
                            now_dt.strftime('%Y-%m-%dT%H:%MZ'), TAGS, first_time) if old.get('alliances') else []
    oldlog = json.loads(HIST.read_text(encoding='utf-8')).get('log', []) if HIST.exists() else []
    if ents or not HIST.exists():
        wos_history.dump(HIST, wos_history.merge(oldlog, ents, now_dt))
    print(f'history: {len(ents)} change(s)', flush=True)
except Exception as e:
    print(f'history skipped: {e}', flush=True)
def stable(x): return json.dumps({'alliances': x.get('alliances'), 'players': x.get('players')}, sort_keys=True, ensure_ascii=False)
if stable(new) != stable(old):
    new['updated'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(new, ensure_ascii=False, separators=(',', ':'), sort_keys=True), encoding='utf-8')
    print(f'written: {len(players)} players, {dl} new pictures')
else:
    print('no changes')
# feed file for roster.html and the planners: which alliances are active right now
if not STYLE['ok']:   # Supabase not reachable: keep the colours of the last feed file
    STYLE['colors'] = prev_feed.get('colors') or {}; STYLE['battle'] = prev_feed.get('battle') or []
feed = {'kid': KID, 'source': SEL_SRC, 'colors': STYLE['colors'], 'battle': STYLE['battle'], 'tags': [t for t in TAGS if t not in missing], 'missing': missing, 'failed': failed,
        'alliances': {t: {'name': (alliances.get(t) or {}).get('name') or (known.get(t) or {}).get('name', ''),
                          'count': (alliances.get(t) or {}).get('count'), 'power': (alliances.get(t) or {}).get('power')} for t in TAGS if t in alliances}}
if write_json_if_changed(FEED, dict(feed, updated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))): print('data/alliances.json written', flush=True)
write_usage(API, key, UA, ROOT / 'data' / 'usage.json', 'player update')
if failed:
    print('FAILED alliances: ' + ', '.join(failed)); sys.exit(1)
