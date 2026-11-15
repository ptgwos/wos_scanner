"""Alliance-change log for data/history.json (used by update_players.py).

Alliance change: {t: UTC time of the run, i: player id, n: name, f: from-tag, a: to-tag}
'unknown' = the player was not visible in any of our alliances (left, kicked, joined from outside, ...).
Name change (since 2026-11-15): {t, i, k: 'n', o: old name, n: new name}   (alliance changes have no 'k')
"""
import json, datetime

KEEP_DAYS = 60
KEEP_MAX = 4000


def membership(alliances, tags):
    """player id -> alliance tag (later tags win, like in update_players.py)"""
    m = {}
    for t in tags:
        for i in (alliances.get(t) or {}).get('m') or []:
            m[str(i)] = t
    return m


def diff(old_al, new_al, names, t, tags, skip_join=()):
    """Changes between two alliance snapshots. skip_join: tags fetched for the first time (no join messages for them)."""
    om, nm = membership(old_al, tags), membership(new_al, tags)
    out = []
    for i, nt in nm.items():
        ot = om.get(i)
        if ot == nt: continue
        if ot is None and nt in skip_join: continue
        out.append({'t': t, 'i': i, 'n': names.get(i, ''), 'f': ot or 'unknown', 'a': nt})
    for i, ot in om.items():
        if i not in nm:
            out.append({'t': t, 'i': i, 'n': names.get(i, ''), 'f': ot, 'a': 'unknown'})
    out.sort(key=lambda e: (e['n'].lower(), e['i']))
    return out


def renames(old_players, new_players, t):
    """Name changes between two player snapshots (matched by player id). Empty names are ignored."""
    out = []
    for i, p in new_players.items():
        o = (old_players.get(i) or {}).get('n')
        n = p.get('n')
        if not o or not n or str(o).strip() == str(n).strip(): continue
        out.append({'t': t, 'i': str(i), 'k': 'n', 'o': o, 'n': n})
    out.sort(key=lambda e: (e['n'].lower(), e['i']))
    return out


def merge(log, entries, now=None):
    """new entries first (newest on top), old ones trimmed by age and count"""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    cut = (now - datetime.timedelta(days=KEEP_DAYS)).strftime('%Y-%m-%dT%H:%MZ')
    res = list(entries) + list(log)
    res = [e for e in res if e['t'] >= cut]
    return res[:KEEP_MAX]


def dump(path, log):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'log': log}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
