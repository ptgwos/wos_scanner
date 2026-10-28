/* State 646 – menu entries that depend on the permissions of the logged-in person.
   RALLY LEADS is shown for everybody; without access it is greyed out and shows a message when clicked.
   ADMIN appears only for the super admin (red dot = open Discord access requests; admins see a REQUESTS entry with the dot).
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
    s.textContent = '.sitenav .na-off{opacity:.42;cursor:not-allowed}.sitenav .na-off:hover{opacity:.6}' +
      '#naToast{position:fixed;left:50%;bottom:28px;transform:translate(-50%,12px);background:var(--panel-2,#161d33);color:var(--text,#e6ebff);border:1px solid var(--gold,#ffb400);border-radius:8px;padding:10px 16px;font-size:13px;box-shadow:0 8px 24px rgba(0,0,0,.4);opacity:0;pointer-events:none;transition:opacity .2s,transform .2s;z-index:9999;max-width:min(92vw,460px);text-align:center}' +
      '#naToast.show{opacity:1;transform:translate(-50%,0)}' +
      '.sitenav .na-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#ff3b3b;margin-left:5px;vertical-align:super;box-shadow:0 0 0 2px rgba(255,59,59,.25)}' +
      '.sitenav .na-login{cursor:pointer}';
    document.head.appendChild(s);
  }
  function put(href, long, short, state, o){
    o = o || {};   // state: 'on' | 'off' | null (remove)
    var nav = document.querySelector('.sitenav'); if(!nav) return;
    var old = nav.querySelector('[data-na="' + href + '"]') || nav.querySelector('a[href="' + href + '"]');
    if(!old && here === href && nav.querySelector('.cur')) return;
    if(state === null){ if(old && old.parentNode) old.parentNode.removeChild(old); return; }
    var inner = '<span class="sn-l">' + long + '</span><span class="sn-s">' + short + '</span>', el;
    if(here === href){ el = document.createElement('span'); el.className = 'cur'; el.setAttribute('aria-current', 'page'); }
    else if(state === 'on'){ el = document.createElement('a'); el.href = href; }
    else {
      el = document.createElement('span'); el.className = 'na-off'; el.setAttribute('aria-disabled', 'true'); el.tabIndex = 0;
      el.title = 'No access';
      var go = function(){ if(o.msg){ note(o.msg); return; } note(code ? 'No access! Please contact Peter the Great in game or on Discord.' : 'No access! Please log in first (Log in with Discord in the menu, or your personal link). Please contact Peter the Great in game or on Discord.'); };
      el.addEventListener('click', go); el.addEventListener('keydown', function(e){ if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); go(); } });
    }
    el.setAttribute('data-na', href); el.innerHTML = inner;
    if(o.dot){ var d = document.createElement('span'); d.className = 'na-dot'; d.title = o.dot; el.appendChild(d); }
    if(old && old.parentNode) old.parentNode.replaceChild(el, old); else nav.appendChild(el);
  }
  function apply(mm){
    css();
    put('assignfsh.html', 'FORTRESS/SH PLAN', 'FSH', 'on');
    put('facilityplan.html', 'FACILITY PLANNER', 'FACILITY', 'on');
    put('rallyleads.html', 'RALLY LEADS', 'LEADS', mm && mm.rallyleads ? 'on' : 'off');
    var pend = mm && mm.pending > 0 ? mm.pending : 0, dt = pend + ' open access request' + (pend === 1 ? '' : 's');
    put('access.html', 'ADMIN', 'ADMIN', mm && mm.role === 'super' ? 'on' : null, pend ? {dot: dt} : null);
    put('requests', 'REQUESTS', 'REQ', mm && mm.role === 'admin' && pend ? 'off' : null, {dot: dt, msg: dt + ' waiting. Please log in with the super admin link to approve them.'});
    loginItem(!mm);
  }
  function loginItem(show){
    var nav = document.querySelector('.sitenav'); if(!nav) return;
    var old = nav.querySelector('[data-na="dclogin"]'), C = window.EP_CONFIG;
    if(!show || !C || !C.url){ if(old && old.parentNode) old.parentNode.removeChild(old); return; }
    if(old) return;
    var el = document.createElement('a'); el.href = '#'; el.className = 'na-login'; el.setAttribute('data-na', 'dclogin');
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
