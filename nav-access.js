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
    s.textContent = '#naToast{position:fixed;left:50%;bottom:28px;transform:translate(-50%,12px);background:var(--panel-2,#161d33);color:var(--text,#e6ebff);border:1px solid var(--gold,#ffb400);border-radius:8px;padding:10px 16px;font-size:13px;box-shadow:0 8px 24px rgba(0,0,0,.4);opacity:0;pointer-events:none;transition:opacity .2s,transform .2s;z-index:300;max-width:90vw;text-align:center}' +
      '#naToast.show{opacity:1;transform:translate(-50%,0)}' +
      '.sitenav.na-g{overflow:visible!important;flex-wrap:wrap;position:relative;z-index:60;gap:4px;align-items:stretch}' +
      '.sitenav.na-g > *{position:relative}' +
      '.sitenav.na-g .na-b{display:inline-flex;align-items:center;gap:6px;padding:6px 13px;border-radius:7px;border:0;background:none;color:var(--text-dim);font:inherit;letter-spacing:inherit;text-decoration:none;cursor:pointer;white-space:nowrap}' +
      '.sitenav.na-g .na-b:hover,.sitenav.na-g .na-grp.open > .na-b{color:var(--strong);background:rgba(120,140,190,.14)}' +
      '.sitenav.na-g .na-b.na-cur{color:var(--gold);background:rgba(255,180,0,.12);box-shadow:inset 0 -2px 0 var(--gold)}' +
      '.sitenav.na-g .na-b svg{width:9px;height:9px;fill:none;stroke:currentColor;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round;transition:transform .15s}' +
      '.sitenav.na-g .na-grp.open > .na-b svg{transform:rotate(180deg)}' +
      '.sitenav.na-g .na-dd{display:none;position:absolute;top:calc(100% + 6px);left:0;min-width:210px;background:var(--panel,#10172b);border:1px solid var(--border,#26304d);border-radius:9px;padding:5px;box-shadow:0 14px 36px rgba(0,0,0,.45);z-index:80}' +
      '.sitenav.na-g .na-dd.r{left:auto;right:0}' +
      '.sitenav.na-g .na-grp.open > .na-dd{display:block}' +
      '.sitenav.na-g .na-dd a,.sitenav.na-g .na-dd span.na-i{display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:6px;color:var(--text-dim);text-decoration:none;white-space:nowrap;font-size:12px}' +
      '.sitenav.na-g .na-dd a:hover{color:var(--strong);background:rgba(120,140,190,.16)}' +
      '.sitenav.na-g .na-dd .na-cur{color:var(--gold);background:rgba(255,180,0,.12)}' +
      '.sitenav.na-g .na-off{opacity:.42;cursor:not-allowed}.sitenav.na-g .na-off:hover{opacity:.6}' +
      '.sitenav .na-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#ff3b3b;margin-left:5px;vertical-align:super;box-shadow:0 0 0 2px rgba(255,59,59,.25)}' +
      '.sitenav.na-g .na-login{margin-left:auto}' +
      '@media (max-width:640px){.sitenav.na-g{gap:1px}.sitenav.na-g .na-b{padding:6px 7px;gap:4px}.sitenav.na-g .na-login{margin-left:0}.sitenav.na-g .na-dd{min-width:190px}}';
    document.head.appendChild(s);
  }
  var GROUPS = [
    {k: 'home', f: 'index.html', l: 'HOME', s: 'HOME'},
    {k: 'info', l: 'INFORMATION', s: 'INFO', items: [['roster.html', 'Roster'], ['svslb.html', 'SvS Leaderboards'], ['rallyleads.html', 'Rally Leads']]},
    {k: 'plan', l: 'PLANNING', s: 'PLAN', items: [['eventplan.html', 'Event Planner'], ['rallyplan.html', 'Rally Planner'], ['assignfsh.html', 'Fortress/SH Plan'], ['appointments.html', 'Appointments']]},
    {k: 'tool', l: 'TOOLS', s: 'TOOLS', items: [['formations.html', 'Formations'], ['chests.html', 'Presidential Chests']]},
    {k: 'admin', f: 'access.html', l: 'ADMIN', s: 'ADMIN'}
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
    if(f === 'access.html') return !!(mm && mm.role === 'super');
    return true;
  }
  function itemEl(f, label, mm, dot){
    var ok = allowed(f, mm), el;
    if(f === hereF){ el = document.createElement('span'); el.className = 'na-i na-cur'; el.setAttribute('aria-current', 'page'); }
    else if(ok){ el = document.createElement('a'); el.href = f; }
    else { el = document.createElement('span'); el.className = 'na-i na-off'; el.setAttribute('aria-disabled', 'true'); el.tabIndex = 0; el.title = 'No access';
      var go = function(){ note(offMsg(f, mm)); }; el.addEventListener('click', go); el.addEventListener('keydown', function(e){ if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); go(); } }); }
    el.setAttribute('data-na', f); el.innerHTML = '<span class="na-t">' + label + '</span>';
    if(dot){ var d = document.createElement('span'); d.className = 'na-dot'; d.title = dot; el.appendChild(d); }
    return el;
  }
  function apply(mm){
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
      g.items.forEach(function(it){ dd.appendChild(itemEl(it[0], it[1], mm)); });
      wrap.appendChild(btn); wrap.appendChild(dd); nav.appendChild(wrap);
      function setOpen(v){
        if(v){ closeAll(wrap); dd.classList.remove('r'); wrap.classList.add('open'); var r = dd.getBoundingClientRect(); if(r.right > window.innerWidth - 6) dd.classList.add('r'); }
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
      var rq = document.createElement('span'); rq.className = 'na-b na-off'; rq.setAttribute('data-na', 'requests'); rq.tabIndex = 0; rq.innerHTML = '<span class="sn-l">REQUESTS</span><span class="sn-s">REQ</span><span class="na-dot" title="' + dt + '"></span>';
      rq.addEventListener('click', function(){ note(dt + ' waiting. Please log in with the super admin link to approve them.'); }); nav.appendChild(rq);
    }
    loginItem(!mm);
  }
  if(!window.__naBound){ window.__naBound = 1;
    document.addEventListener('click', function(e){ if(!e.target.closest || !e.target.closest('.sitenav .na-grp')) closeAll(); });
    document.addEventListener('keydown', function(e){ if(e.key === 'Escape') closeAll(); });
  }
  function loginItem(show){
    var nav = document.querySelector('.sitenav'); if(!nav) return;
    var old = nav.querySelector('[data-na="dclogin"]'), C = window.EP_CONFIG;
    if(!show || !C || !C.url){ if(old && old.parentNode) old.parentNode.removeChild(old); return; }
    if(old) return;
    var el = document.createElement('a'); el.href = '#'; el.className = 'na-b na-login'; el.setAttribute('data-na', 'dclogin');
    el.innerHTML = '<span class="sn-l">LOG IN WITH DISCORD</span><span class="sn-s">LOGIN</span>';
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
