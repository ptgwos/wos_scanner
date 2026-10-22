"""Alliance-change log for data/history.json (used by update_players.py).

Every entry: {t: UTC time of the run, i: player id, n: name, f: from-tag, a: to-tag}
'unknown' = the player was not visible in any of our alliances (left, kicked, joined from outside, ...).
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
