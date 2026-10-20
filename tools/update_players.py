#!/usr/bin/env python3
"""Fetch the member lists of the State 646 alliances from the Whiteout Stats API
and write data/players.json + avatars/<id>.webp (small copies of the profile pictures).

- one API request per alliance (the roster holds all members), 15 requests per run
- data/players.json feeds svslb.html (avatars) and roster.html (members, power)
- API key comes from the environment variable WOS_API_KEY (never from a file)
- players that are not in any fetched alliance keep their last known entry
- if an alliance cannot be fetched, its players keep their last known entry
- nothing is written when nothing changed, so there is no commit noise
"""
import io, json, os, sys, time, urllib.parse, urllib.request, urllib.error, datetime, pathlib

API = os.environ.get('WOS_API_BASE', 'https://api.whiteoutstats.com/v1')
KID = 646
# case sensitive on purpose: TBR, TbR and tbr are three different alliances
TAGS = ['AIR', 'BLP', 'TBR', 'TbR', 'osm', 'OMG', 'PKB', 'GYN', 'EVL', 'HYg', 'KOJ', 'NEW', 'DFT', 'HOS', 'tbr']
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'players.json'
AV = ROOT / 'avatars'
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

old = json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else {'alliances': {}, 'players': {}}
players = {k: dict(v) for k, v in old.get('players', {}).items()}
alliances = dict(old.get('alliances', {}))
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
ok, failed = [], []
seen_now = {}

for n, tag in enumerate(TAGS):
    if n: time.sleep(PAUSE)
    url = f"{API}/alliances/{KID}/{urllib.parse.quote(tag, safe='')}?include=info,roster"
    try:
        d = json.loads(get(url, {'Authorization': 'Bearer ' + key, 'Accept': 'application/json'}))
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
def stable(x): return json.dumps({'alliances': x.get('alliances'), 'players': x.get('players')}, sort_keys=True, ensure_ascii=False)
if stable(new) != stable(old):
    new['updated'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(new, ensure_ascii=False, separators=(',', ':'), sort_keys=True), encoding='utf-8')
    print(f'written: {len(players)} players, {dl} new pictures')
else:
    print('no changes')
if failed:
    print('FAILED alliances: ' + ', '.join(failed)); sys.exit(1)
