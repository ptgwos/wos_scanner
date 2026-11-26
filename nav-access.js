/* State 646 – menu entries that depend on the permissions of the logged-in person.
   Builds the whole menu bar (HOME, INFORMATION, PLANNING, TOOLS drop-downs, ADMIN) on every page, so new pages only need an entry in GROUPS below.
   RALLY LEADS and ADMIN are shown for everybody; without access they are greyed out and show a message when clicked (red dot at ADMIN = open Discord access requests; admins see a REQUESTS entry with the dot).
   Also handles "Log in with Discord" (menu entry + return from Discord). Uses the same login as the Event Planner (localStorage ep_code).
   This only changes the menu; the real protection of the data sits in the database. */
(function(){
  var code = null; try { code = localStorage.getItem('ep_code'); } catch(e) {}
  var cache = null; try { cache = JSON.parse(sessionStorage.getItem('na_m') || 'null'); } catch(e) {}
  var m = (cache && cache.c === code) ? cache.m : null;
  var here = (location.pathname.split('/').pop() || '').toLowerCase();
  var msgT = null;
  function note(txt){
    var t = document.getElementById('naToast');
    if(!t){ t = document.createElement('div'); t.id = 'naToast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = txt; t.className = 'show'; clearTimeout(msgT); msgT = setTimeout(function(){ t.className = ''; }, 4500);
  }
  function css(){
    if(document.getElementById('naCss')) return;
    var s = document.createElement('style'); s.id = 'naCss';
    s.textContent = '#naToast{position:fixed;left:50%;bottom:28px;transform:translate(-50%,12px);background:var(--panel-2,#161d33);color:var(--text,#e6ebff);border:1px solid var(--gold,#ffb400);border-radius:10px;padding:10px 16px;font-size:13px;box-shadow:0 8px 24px rgba(0,0,0,.4);opacity:0;pointer-events:none;transition:opacity .2s,transform .2s;z-index:300;max-width:90vw;text-align:center}' +
      '#naToast.show{opacity:1;transform:translate(-50%,0)}' +
      '.sitenav.na-g{overflow:visible!important;flex-wrap:wrap;position:relative;z-index:60;gap:2px;align-items:stretch;padding:4px;border-radius:12px;font-size:13.5px;font-weight:500;letter-spacing:0;text-transform:none;font-variant-caps:normal}' +
      '.sitenav.na-g > *{position:relative}' +
      '.sitenav.na-g .na-b{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:9px;border:0;background:none;color:var(--text-dim);font:inherit;font-size:13.5px;font-weight:500;letter-spacing:0;text-transform:none;font-variant-caps:normal;text-decoration:none;cursor:pointer;white-space:nowrap;transition:background .15s,color .15s}' +
      '.sitenav.na-g .na-b:hover,.sitenav.na-g .na-grp.open > .na-b{color:var(--strong);background:rgba(120,140,190,.14)}' +
      '.sitenav.na-g .na-b:focus-visible,.sitenav.na-g .na-dd a:focus-visible{outline:2px solid var(--gold,#ffb400);outline-offset:1px}' +
      '.sitenav.na-g .na-b.na-cur{color:var(--gold);background:rgba(255,180,0,.13);box-shadow:none}' +
      '.sitenav.na-g .na-b svg{width:10px;height:10px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;opacity:.7;transition:transform .18s}' +
      '.sitenav.na-g .na-grp.open > .na-b svg{transform:rotate(180deg)}' +
      '.sitenav.na-g .na-dd{display:none;position:absolute;top:calc(100% + 8px);left:0;min-width:220px;background:var(--panel,#10172b);border:1px solid var(--border,#26304d);border-radius:12px;padding:6px;box-shadow:0 16px 40px rgba(0,0,0,.42);z-index:80;transform-origin:top left}' +
      '.sitenav.na-g .na-dd.r{left:auto;right:0;transform-origin:top right}' +
      '.sitenav.na-g .na-grp.open > .na-dd{display:block;animation:naIn .14s ease-out}' +
      '@keyframes naIn{from{opacity:0;transform:translateY(-4px) scale(.98)}to{opacity:1;transform:none}}' +
      '@media (prefers-reduced-motion:reduce){.sitenav.na-g .na-grp.open > .na-dd{animation:none}.sitenav.na-g .na-b,.sitenav.na-g .na-b svg{transition:none}}' +
      '.sitenav.na-g .na-dd{min-width:300px;max-width:calc(100vw - 16px)}' +
      '.sitenav.na-g .na-dd a,.sitenav.na-g .na-dd span.na-i{display:flex;align-items:flex-start;gap:12px;padding:9px 12px;border-radius:9px;color:var(--text-dim);text-decoration:none;white-space:normal;font-size:14px;font-weight:500;letter-spacing:0;text-transform:none;font-variant-caps:normal;line-height:1.3}' +
      '.sitenav.na-g .na-dd a:hover{color:var(--strong);background:rgba(120,140,190,.16)}' +
      '.sitenav.na-g .na-ic{flex:0 0 auto;width:20px;height:20px;margin-top:1px;opacity:.75;display:inline-flex}.sitenav.na-g .na-ic svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;opacity:1;transition:none}' +
      '.sitenav.na-g .na-dd a:hover .na-ic{opacity:1}' +
      '.sitenav.na-g .na-tx{display:flex;flex-direction:column;gap:2px;min-width:0;flex:1}' +
      '.sitenav.na-g .na-t{display:flex;align-items:center;gap:8px;color:var(--strong);font-weight:600}' +
      '.sitenav.na-g .na-ds{font-size:12px;font-weight:400;color:var(--text-faint,var(--text-dim));line-height:1.35}' +
      '.sitenav.na-g .na-bg{display:inline-block;padding:1px 7px;border-radius:20px;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;line-height:1.5}' +
      '.sitenav.na-g .na-bg.f{background:rgba(52,190,110,.15);color:#25a35f}' +
      '.sitenav.na-g .na-bg.m{background:rgba(255,180,0,.16);color:var(--gold,#ffb400)}' +
      '.sitenav.na-g .na-lg{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;margin:6px 4px 2px;padding:9px 8px 4px;border-top:1px solid var(--border,#26304d);font-size:11.5px;color:var(--text-faint,var(--text-dim))}' +
      '.sitenav.na-g .na-dd .na-cur{background:rgba(255,180,0,.1)}.sitenav.na-g .na-dd .na-cur .na-t{color:var(--gold)}' +
      '.sitenav.na-g .na-dd .na-cur::before{display:none}' +
      '.sitenav.na-g .na-off{opacity:.42;cursor:not-allowed}.sitenav.na-g .na-off:hover{opacity:.6}' +
      '.sitenav .na-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#ff3b3b;margin-left:5px;vertical-align:super;box-shadow:0 0 0 2px rgba(255,59,59,.25)}' +
      '.sitenav.na-g .na-login{margin-left:auto;color:var(--gold);background:rgba(255,180,0,.12)}' +
      '.sitenav.na-g .na-login:hover{background:rgba(255,180,0,.22);color:var(--gold)}' +
      '@media (max-width:640px){.sitenav.na-g{gap:1px;padding:3px}.sitenav.na-g .na-b{padding:7px 9px;gap:4px;font-size:13px}.sitenav.na-g .na-login{margin-left:0}.sitenav.na-g .na-dd,.sitenav.na-g .na-dd.r{position:fixed;left:8px;right:8px;top:var(--na-top,120px);min-width:0;max-width:none;max-height:calc(100vh - var(--na-top,120px) - 12px);overflow-y:auto}.sitenav.na-g .na-grp{position:static}}';
    document.head.appendChild(s);
  }
  // icons: small line symbols (24x24, stroke = currentColor)
  var IC = {
    users: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M16 5.2a3.2 3.2 0 0 1 0 5.6M18 14.4c1.8.8 3 2.6 3 5.6"/>',
    trophy: '<path d="M8 4h8v5a4 4 0 0 1-8 0V4z"/><path d="M8 6H4v1.5A3.5 3.5 0 0 0 8 11M16 6h4v1.5A3.5 3.5 0 0 1 16 11"/><path d="M12 13v4M8.5 20h7M10 17h4"/>',
    bars: '<path d="M5 20V11M12 20V4M19 20v-6"/>',
    crown: '<path d="M3.5 18h17M4.5 18L3 7l5 4 4-6 4 6 5-4-1.5 11"/>',
    flag: '<path d="M6 21V4M6 5h11l-2 4 2 4H6"/>',
    calcheck: '<rect x="4" y="5" width="16" height="15" rx="2.5"/><path d="M4 10h16M8 3v4M16 3v4M9 15l2 2 4-4"/>',
    cal: '<rect x="4" y="5" width="16" height="15" rx="2.5"/><path d="M4 10h16M8 3v4M16 3v4"/>',
    target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r=".8"/>',
    waves: '<path d="M4 8c2-2 4-2 6 0s4 2 6 0 3-1.5 4-1M4 14c2-2 4-2 6 0s4 2 6 0 3-1.5 4-1M4 20c2-2 4-2 6 0s4 2 6 0 3-1.5 4-1"/>',
    castle: '<path d="M4 20V8h3v2h2V8h6v2h2V8h3v12H4zM10 20v-5a2 2 0 0 1 4 0v5"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3 2"/>',
    grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
    shield: '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/>',
    stopwatch: '<circle cx="12" cy="13.5" r="7.5"/><path d="M12 13.5V9.5M9.5 2.5h5M12 2.5V6M18.2 7.2l1.6-1.6"/>',
    buff: '<circle cx="12" cy="12" r="8.5"/><path d="M12 16.5V8M8.5 11.5L12 8l3.5 3.5"/>',
    manage: '<path d="M5 6h14M5 12h14M5 18h14"/><circle cx="9" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>',
    map: '<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2V6z"/><path d="M9 4v14M15 6v14"/>',
    gift: '<rect x="4" y="9" width="16" height="11" rx="2"/><path d="M3 9h18M12 9v11M12 9c-2-4-6-3-5 0M12 9c2-4 6-3 5 0"/>'
  };
  // items: [page, label, icon, short description, badge]  badge f = open to everyone (you may need a login to edit), m = members of state 646 with access only
  var GROUPS = [
    {k: 'home', f: 'index.html', l: 'Home', s: 'Home'},
    {k: 'info', l: 'Information', s: 'Info', items: [
      ['roster.html', 'Roster', 'users', 'Alliance members, power and changes', 'f'],
      ['svslb.html', 'SvS Leaderboards', 'trophy', 'Results of every SvS event', 'f'],
      ['statepower.html', 'State Power', 'bars', 'Power ranking of the whole state', 'f'],
      ['leading.html', 'Leading State', 'crown', 'Transfer scores of the states in the bracket', 'f'],
      ['facilities.html', 'Facility Map', 'map', 'Where the facilities are and who holds them', 'f'],
      ['rallyleads.html', 'Rally Leads', 'flag', 'Rally leaders with heroes and stats', 'm']]},
    {k: 'plan', l: 'Planning', s: 'Plan', items: [
      ['eventplan.html', 'Event Planner', 'calcheck', 'Teams and hours for alliance events', 'f'],
      ['eventcal.html', 'Event Calendar', 'cal', 'Game events on a timeline', 'f'],
      ['rallyplan.html', 'Rally Planner', 'target', 'Rally slots, pets and Battle Buddies', 'm'],
      ['rallytimer.html', 'Rally Timer', 'stopwatch', 'Countdown so all rallies land together (PIN)', 'f'],
      ['pool.html', 'Rally Pool', 'waves', 'Pool of players for rallies', 'f'],
      ['assignfsh.html', 'Fortress/SH Plan', 'castle', 'Fortress and stronghold assignments', 'f'],
      ['buff_recipients.html', 'Buff Recipients', 'buff', 'Who gets the fortress buffs', 'f'],
      ['appointments.html', 'Appointments', 'clock', 'Sign up for minister office slots', 'f'],
      ['manageappt.html', 'Manage Appointments', 'manage', 'Sign-up overview, auto-fill and final assignment', 'm'],
      ['foundryplaner.html', 'Foundry/TAL Planner', 'grid', 'Team plan for the Foundry and TAL', 'f']]},
    {k: 'tool', l: 'Tools', s: 'Tools', items: [
      ['formations.html', 'Formations', 'shield', 'Hero formations for garrison and rally', 'f'],
      ['chests.html', 'Presidential Chests', 'gift', 'Chest distribution calculator', 'f']]},
    {k: 'admin', f: 'access.html', l: 'Admin', s: 'Admin'}
  ];
  var CHEV = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M1.5 3.5L5 7l3.5-3.5"/></svg>';
  var hereF = here === '' ? 'index.html' : (here.indexOf('.') < 0 ? here + '.html' : here);
  function closeAll(except){ var g = document.querySelectorAll('.sitenav .na-grp.open'); for(var i = 0; i < g.length; i++) if(g[i] !== except) g[i].classList.remove('open'); }
  function offMsg(k, mm){
    if(k === 'access.html') return code ? 'No access! This page is for the super admin only. Please contact Peter the Great in game or on Discord.' : 'No access! This page is for the super admin only. Please log in first.';
    return code ? 'No access! Please contact Peter the Great in game or on Discord.' : 'No access! Please log in first (Log in with Discord in the menu, or your personal link). Please contact Peter the Great in game or on Discord.';
  }
  function allowed(f, mm){
    if(f === 'rallyleads.html') return !!(mm && mm.rallyleads);
    if(f === 'manageappt.html') return !!(mm && (mm.role === 'super' || (mm.pages || []).indexOf('appointments') >= 0));
    if(f === 'access.html') return !!(mm && mm.role === 'super');
    return true;
  }
  function itemEl(f, label, mm, dot, ic, ds, bg){
    var ok = allowed(f, mm), el;
    if(f === hereF){ el = document.createElement('span'); el.className = 'na-i na-cur'; el.setAttribute('aria-current', 'page'); }
    else if(ok){ el = document.createElement('a'); el.href = f; }
    else { el = document.createElement('span'); el.className = 'na-i na-off'; el.setAttribute('aria-disabled', 'true'); el.tabIndex = 0; el.title = 'No access';
      var go = function(){ note(offMsg(f, mm)); }; el.addEventListener('click', go); el.addEventListener('keydown', function(e){ if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); go(); } }); }
    el.setAttribute('data-na', f);
    el.innerHTML = '<span class="na-ic"><svg viewBox="0 0 24 24" aria-hidden="true">' + (IC[ic] || '') + '</svg></span><span class="na-tx"><span class="na-t">' + label +
      (bg ? ' <span class="na-bg ' + bg + '" title="' + (bg === 'f' ? 'Open to everyone' : 'Members of state 646 with access') + '">' + (bg === 'f' ? 'Free' : '646') + '</span>' : '') + '</span>' + (ds ? '<span class="na-ds">' + ds + '</span>' : '') + '</span>';
    if(dot){ var d = document.createElement('span'); d.className = 'na-dot'; d.title = dot; el.appendChild(d); }
    return el;
  }
  function publish(mm){   // lets the page know what the logged-in person may see (e.g. the Lucy tab in svslb.html)
    window.NAV_ME = mm || null;
    try { window.dispatchEvent(new CustomEvent('na:me', {detail: mm || null})); } catch(e) {}
  }
  function apply(mm){
    publish(mm);
    css();
    var nav = document.querySelector('.sitenav'); if(!nav) return;
    var open = null; var o = nav.querySelector('.na-grp.open'); if(o) open = o.getAttribute('data-g');
    nav.className = 'sitenav na-g'; nav.innerHTML = '';
    var pend = mm && mm.pending > 0 ? mm.pending : 0, dt = pend + ' open access request' + (pend === 1 ? '' : 's');
    GROUPS.forEach(function(g){
      if(g.f){   // single link (HOME, ADMIN)
        var f = g.f, ok = allowed(f, mm), el;
        if(f === hereF){ el = document.createElement('span'); el.className = 'na-b na-cur'; el.setAttribute('aria-current', 'page'); }
        else if(ok){ el = document.createElement('a'); el.className = 'na-b'; el.href = f; }
        else { el = document.createElement('span'); el.className = 'na-b na-off'; el.setAttribute('aria-disabled', 'true'); el.tabIndex = 0; el.title = 'No access';
          var go = function(){ note(offMsg(f, mm)); }; el.addEventListener('click', go); el.addEventListener('keydown', function(e){ if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); go(); } }); }
        el.setAttribute('data-na', f); el.innerHTML = '<span class="sn-l">' + g.l + '</span><span class="sn-s">' + g.s + '</span>';
        if(f === 'access.html' && pend && ok){ var d = document.createElement('span'); d.className = 'na-dot'; d.title = dt; el.appendChild(d); }
        nav.appendChild(el); return;
      }
      var wrap = document.createElement('div'); wrap.className = 'na-grp'; wrap.setAttribute('data-g', g.k);
      var inHere = g.items.some(function(it){ return it[0] === hereF; });
      var btn = document.createElement('button'); btn.type = 'button'; btn.className = 'na-b' + (inHere ? ' na-cur' : ''); btn.setAttribute('aria-haspopup', 'true'); btn.setAttribute('aria-expanded', 'false');
      btn.innerHTML = '<span class="sn-l">' + g.l + '</span><span class="sn-s">' + g.s + '</span>' + CHEV;
      var dd = document.createElement('div'); dd.className = 'na-dd'; dd.setAttribute('role', 'menu');
      g.items.forEach(function(it){ dd.appendChild(itemEl(it[0], it[1], mm, null, it[2], it[3], it[4])); });
      var lg = document.createElement('div'); lg.className = 'na-lg'; lg.innerHTML = '<span><span class="na-bg f">Free</span> open to everyone</span><span><span class="na-bg m">646</span> members with access</span>'; dd.appendChild(lg);
      wrap.appendChild(btn); wrap.appendChild(dd); nav.appendChild(wrap);
      function setOpen(v){
        if(v){ closeAll(wrap); dd.classList.remove('r'); wrap.classList.add('open'); nav.style.setProperty('--na-top', Math.round(nav.getBoundingClientRect().bottom + 6) + 'px'); var r = dd.getBoundingClientRect(); if(r.right > window.innerWidth - 6) dd.classList.add('r'); }
        else wrap.classList.remove('open');
        btn.setAttribute('aria-expanded', v ? 'true' : 'false');
      }
      var tOpen = 0;
      btn.addEventListener('click', function(e){ e.stopPropagation(); if(Date.now() - tOpen < 600) return; setOpen(!wrap.classList.contains('open')); });
      var ht = null, fine = window.matchMedia && window.matchMedia('(hover:hover) and (pointer:fine)').matches;
      if(fine){ wrap.addEventListener('mouseenter', function(){ clearTimeout(ht); if(!wrap.classList.contains('open')) tOpen = Date.now(); setOpen(true); }); wrap.addEventListener('mouseleave', function(){ clearTimeout(ht); ht = setTimeout(function(){ setOpen(false); }, 180); }); }
      if(open === g.k) setOpen(true);
    });
    if(mm && mm.role === 'admin' && pend){
      var rq = document.createElement('span'); rq.className = 'na-b na-off'; rq.setAttribute('data-na', 'requests'); rq.tabIndex = 0; rq.innerHTML = '<span class="sn-l">Requests</span><span class="sn-s">Req</span><span class="na-dot" title="' + dt + '"></span>';
      rq.addEventListener('click', function(){ note(dt + ' waiting. Please log in with the super admin link to approve them.'); }); nav.appendChild(rq);
    }
    loginItem(!mm);
  }
  if(!window.__naBound){ window.__naBound = 1;
    document.addEventListener('click', function(e){ if(!e.target.closest || !e.target.closest('.sitenav .na-grp')) closeAll(); });
    document.addEventListener('keydown', function(e){ if(e.key === 'Escape') closeAll(); });
    window.addEventListener('scroll', function(){ if(window.matchMedia && window.matchMedia('(max-width:640px)').matches) closeAll(); }, {passive: true});
  }
  function loginItem(show){
    var nav = document.querySelector('.sitenav'); if(!nav) return;
    var old = nav.querySelector('[data-na="dclogin"]'), C = window.EP_CONFIG;
    if(!show || !C || !C.url){ if(old && old.parentNode) old.parentNode.removeChild(old); return; }
    if(old) return;
    var el = document.createElement('a'); el.href = '#'; el.className = 'na-b na-login'; el.setAttribute('data-na', 'dclogin');
    el.innerHTML = '<span class="sn-l">Log in with Discord</span><span class="sn-s">Log in</span>';
    el.addEventListener('click', function(e){ e.preventDefault(); window.EPDiscord.start(); });
    nav.appendChild(el);
  }
  // ---- Log in with Discord (Supabase Auth, implicit flow: Discord sends the person back with a token in the URL hash) ----
  window.EPDiscord = {start: function(){
    var C = window.EP_CONFIG; if(!C || !C.url){ note('Login is not available right now.'); return; }
    location.href = C.url.replace(/\/+$/, '') + '/auth/v1/authorize?provider=discord&redirect_to=' + encodeURIComponent(location.origin + location.pathname);
  }};
  function flash(txt){ try { sessionStorage.setItem('na_msg', txt); } catch(e) {} }
  function showFlash(){ var t = null; try { t = sessionStorage.getItem('na_msg'); sessionStorage.removeItem('na_msg'); } catch(e) {} if(t) note(t); }
  function cleanUrl(){ try { history.replaceState(null, '', location.pathname + location.search); } catch(e) {} }
  function handleReturn(){
    var h = location.hash || '', q = location.search || '';
    var isErr = /[#&?]error(_description)?=/.test(h + q) && /sb-|provider|discord|access_denied|server_error|error_code/.test(h + q);
    var tok = (h.match(/access_token=([^&]+)/) || [])[1];
    if(!tok && !isErr) return false;
    if(!tok){ flash('Discord login was cancelled or failed. Please try again.'); cleanUrl(); return false; }
    cleanUrl();
    var go = function(){
      var C = window.EP_CONFIG; if(!C || !C.url){ flash('Login failed (no connection settings).'); return; }
      var H = {apikey: C.key, 'Content-Type': 'application/json', Authorization: 'Bearer ' + tok};
      fetch(C.url.replace(/\/+$/, '') + '/rest/v1/rpc/dc_login', {method: 'POST', headers: H, body: '{}'})
        .then(function(r){ return r.json().then(function(j){ if(!r.ok) throw new Error((j && (j.message || j.hint)) || ('HTTP ' + r.status)); return j; }); })
        .then(function(j){
          if(j && j.status === 'ok' && j.code){
            try { localStorage.setItem('ep_code', j.code); sessionStorage.removeItem('na_m'); } catch(e) {}
            flash('Logged in with Discord as ' + (j.name || '') + '.'); location.replace(location.pathname + location.search);
          } else if(j && j.status === 'blocked'){ flash('Your account is blocked. Please contact Peter the Great in game or on Discord.'); showFlash(); }
          else { flash('Thank you' + (j && j.name ? ', ' + j.name : '') + '! Your access request was sent. The super admin will unlock your access.'); showFlash(); }
        }).catch(function(e){ flash('Discord login failed: ' + e.message); showFlash(); });
    };
    if(window.EP_CONFIG) go(); else { var sc = document.createElement('script'); sc.src = 'eventplan-config.js'; sc.onload = go; document.head.appendChild(sc); }
    return true;
  }
  function run(){
    var C = window.EP_CONFIG; if(!C || !C.url || !C.key) return;
    if(!code){ apply(null); return; }
    var H = {apikey: C.key, 'Content-Type': 'application/json'}; if(/^eyJ/.test(C.key)) H.Authorization = 'Bearer ' + C.key;
    fetch(C.url.replace(/\/+$/, '') + '/rest/v1/rpc/sa_me', {method: 'POST', headers: H, body: JSON.stringify({p_code: code})})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(j){
        try { sessionStorage.setItem('na_m', JSON.stringify({c: code, m: j || null})); } catch(e) {}
        apply(j);
      }).catch(function(){});
  }
  function start(){
    handleReturn();
    showFlash();
    apply(m);
    if(window.EP_CONFIG) return run();
    var sc = document.createElement('script'); sc.src = 'eventplan-config.js'; sc.onload = run; document.head.appendChild(sc);
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
