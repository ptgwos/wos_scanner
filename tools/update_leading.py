#!/usr/bin/env python3
"""Leading State: transfer score (board "state_transfer") of the top 100 of every state in the bracket (Whiteout Stats API).

    data/leading.json              latest status of all states (read by leading.html)
    data/leading/YYYY-MM-DD.json   one snapshot per day (history), date = day the game captured the boards (UTC)
    data/leading/index.json        list of the available days

Cost: ONE request per state (GET /states/<kid>/ranks?board=state_transfer&limit=100). Bracket 536-803 = 268 requests (the daily limit is 5000).
States that do not exist (any more), e.g. 631 after a merger, are detected (HTTP 4xx or an empty answer), remembered under "gone" and only
checked again every GONE_RECHECK days, so they cost (almost) nothing and never break the run.
A state that fails for other reasons (timeout, 5xx) keeps its old values and is marked "stale".
Settings (environment): WOS_FIRST / WOS_LAST (bracket), WOS_PAUSE (seconds between requests, default 1.2), WOS_MAXMIN (stop after this many minutes
and keep the rest as it was, default 40), WOS_FORCE_GONE=1 (check the "gone" states again now), WOS_KIDS="646,622" (only these states, for tests).
Only the Python standard library. The key comes from the environment variable WOS_API_KEY (GitHub secret).
"""
import json, os, re, sys, time, urllib.request, urllib.error

BASE = os.environ.get('WOS_API_BASE', 'https://api.whiteoutstats.com/v1')
UA = 'state646-board/1.0 (+https://www.state646.com)'
OUT = os.environ.get('WOS_OUT', 'data')
FIRST, LAST = int(os.environ.get('WOS_FIRST', '536') or 536), int(os.environ.get('WOS_LAST', '803') or 803)
PAUSE = float(os.environ.get('WOS_PAUSE', '1.2'))
MAXMIN = float(os.environ.get('WOS_MAXMIN', '40'))
GONE_RECHECK = 14                       # days
BOARD = 'state_transfer'
KEY = os.environ.get('WOS_API_KEY', '').strip()
if not KEY:
    sys.exit('WOS_API_KEY is not set.')
T0 = time.time()


def get(path, timeout=40, tries=3):
    """Returns (status, json). status: 200 ok | 'gone' (HTTP 400/403/404/410: the state does not exist or is not served) | 'err' (everything else)."""
    for attempt in range(tries):
        req = urllib.request.Request(BASE + path, headers={'Authorization': 'Bearer ' + KEY, 'User-Agent': UA, 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return 200, json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 20
                try: wait = max(5, min(70, int(e.headers.get('Retry-After', '20'))))
                except Exception: pass
                print(f'  429, waiting {wait}s', flush=True); time.sleep(wait); continue
            if e.code in (400, 403, 404, 410): return 'gone', None
            if e.code == 401: sys.exit('HTTP 401: the API key is not accepted (WOS_API_KEY).')
            if e.code >= 500: time.sleep(5 * (attempt + 1)); continue
            return 'err', None
        except Exception as e:
            print(f'  error: {e}', flush=True); time.sleep(5 * (attempt + 1))
    return 'err', None


def write_usage(path, by):
    """data/usage.json: remaining API allowance (GET /usage is free). Never breaks the run."""
    try:
        req = urllib.request.Request(BASE + '/usage', headers={'Authorization': 'Bearer ' + KEY, 'User-Agent': UA, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as r: d = json.loads(r.read().decode('utf-8'))
        dl = d.get('daily') or {}
        if not d.get('ok') or not isinstance(dl.get('remaining'), int): return
        out = {'frosty': bool(d.get('frosty')), 'daily': {k: dl.get(k) for k in ('limit', 'used', 'remaining', 'resets_at')},
               'minute_limit': (d.get('minute') or {}).get('limit'), 'updated': int(time.time()), 'by': by}
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path + '.tmp', 'w', encoding='utf-8') as f: json.dump(out, f, separators=(',', ':'))
        os.replace(path + '.tmp', path)
        print(f"usage: {dl.get('remaining')} of {dl.get('limit')} requests left today", flush=True)
    except Exception as e:
        print(f'usage skipped: {e}', flush=True)


def load(p):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except Exception:
        return None


def stamp(t):
    return time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(t)) if t else 'unknown'


def fetch_state(kid):
    """-> ('ok', entry) | ('gone', None) | ('err', None)"""
    code, d = get(f'/states/{kid}/ranks?board={BOARD}&limit=100')
    if code != 200: return code, None
    b = None
    for x in (d or {}).get('boards') or []:
        if x.get('key') == BOARD: b = x
    rows = [r for r in ((b or {}).get('rows') or []) if isinstance(r.get('score'), (int, float))]
    if not rows: return 'gone', None                       # answered, but there is no ranking: the state does not exist (any more)
    scores = [float(r['score']) for r in rows]
    cap = (b or {}).get('captured_at')
    return 'ok', {'s': int(sum(scores)), 'n': len(scores), 't1': int(max(scores)), 'c': int(min(scores)), 'cap': int(float(cap)) if cap else None}


def main():
    only = [int(x) for x in re.findall(r'\d+', os.environ.get('WOS_KIDS', ''))]
    kids = only or list(range(FIRST, LAST + 1))
    old = load(os.path.join(OUT, 'leading.json')) or {}
    if old.get('sample'): old = {}
    states, gone = dict(old.get('states') or {}), dict(old.get('gone') or {})
    today = time.strftime('%Y-%m-%d', time.gmtime())
    force_gone = os.environ.get('WOS_FORCE_GONE', '') == '1'
    n_req = n_ok = n_err = n_gone = n_skip = 0
    fails_in_row = 0
    print(f'Leading State: {len(kids)} states ({kids[0]}-{kids[-1]}), board {BOARD}', flush=True)
    for kid in kids:
        k = str(kid)
        if k in gone and not force_gone:
            try: age = (time.mktime(time.strptime(today, '%Y-%m-%d')) - time.mktime(time.strptime(gone[k], '%Y-%m-%d'))) / 86400
            except Exception: age = 99
            if age < GONE_RECHECK: n_skip += 1; continue
        if (time.time() - T0) / 60 > MAXMIN:
            print(f'Time limit of {MAXMIN:g} min reached at state {kid}; the remaining states keep their old values.', flush=True); break
        code, e = fetch_state(kid); n_req += 1
        if code == 'ok':
            states[k] = e; gone.pop(k, None); n_ok += 1; fails_in_row = 0
        elif code == 'gone':
            states.pop(k, None); gone[k] = today; n_gone += 1; fails_in_row = 0
        else:
            n_err += 1; fails_in_row += 1
            if k in states: states[k]['stale'] = True
            if fails_in_row >= 8: print('8 failures in a row: the API seems to have a problem, stopping. Old values are kept.', flush=True); break
        time.sleep(PAUSE)
    caps = [v['cap'] for v in states.values() if v.get('cap') and not v.get('stale')]
    cap = max(caps) if caps else old.get('captured')
    for k, v in states.items():
        if k in {str(x) for x in kids} and not v.get('stale'): v.pop('stale', None)
    out = {'sample': False, 'board': BOARD, 'first': FIRST, 'last': LAST, 'captured': cap, 'updated': int(time.time()),
           'states': dict(sorted(states.items(), key=lambda kv: int(kv[0]))), 'gone': dict(sorted(gone.items(), key=lambda kv: int(kv[0])))}
    print(f'{n_req} requests: {n_ok} ok, {n_gone} without ranking (gone), {n_err} failed, {n_skip} known-gone skipped. Game capture {stamp(cap)}.', flush=True)
    if n_ok == 0:
        print('Nothing usable was fetched, files left as they were.'); return 1
    same = old.get('states') == out['states'] and old.get('gone') == out['gone'] and old.get('captured') == cap
    if same:
        print('Nothing changed since the last run, nothing written.'); write_usage(os.path.join(OUT, 'usage.json'), 'leading state job'); return 0
    os.makedirs(os.path.join(OUT, 'leading'), exist_ok=True)
    day = time.strftime('%Y-%m-%d', time.gmtime(cap)) if cap else today
    snap = {'captured': cap, 's': {k: [v['s'], v['n']] for k, v in out['states'].items() if not v.get('stale')}}
    for path, data in ((os.path.join(OUT, 'leading.json'), out), (os.path.join(OUT, 'leading', day + '.json'), snap)):
        with open(path + '.tmp', 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(path + '.tmp', path)
    d = os.path.join(OUT, 'leading')
    days = sorted(f[:-5] for f in os.listdir(d) if re.fullmatch(r'\d{4}-\d{2}-\d{2}\.json', f))
    with open(os.path.join(d, 'index.json') + '.tmp', 'w', encoding='utf-8') as f: json.dump({'dates': days}, f, separators=(',', ':'))
    os.replace(os.path.join(d, 'index.json') + '.tmp', os.path.join(d, 'index.json'))
    print(f'Written: data/leading.json and data/leading/{day}.json ({len(days)} days of history).', flush=True)
    write_usage(os.path.join(OUT, 'usage.json'), 'leading state job')
    return 1 if n_err > max(3, len(kids) // 20) else 0      # a few failed states are no reason to mark the whole run as failed


if __name__ == '__main__':
    sys.exit(main())
