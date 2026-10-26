/* State 646 – menu entries that depend on the permissions of the logged-in person.
   RALLY LEADS is shown for everybody; without access it is greyed out and shows a message when clicked.
   ADMIN appears only for the super admin. Uses the same login as the Event Planner (localStorage ep_code).
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
      '#naToast.show{opacity:1;transform:translate(-50%,0)}';
    document.head.appendChild(s);
  }
  function put(href, long, short, state){   // state: 'on' | 'off' | null (remove)
    var nav = document.querySelector('.sitenav'); if(!nav) return;
    var old = nav.querySelector('[data-na="' + href + '"]');
    if(state === null){ if(old && old.parentNode) old.parentNode.removeChild(old); return; }
    var inner = '<span class="sn-l">' + long + '</span><span class="sn-s">' + short + '</span>', el;
    if(here === href){ el = document.createElement('span'); el.className = 'cur'; el.setAttribute('aria-current', 'page'); }
    else if(state === 'on'){ el = document.createElement('a'); el.href = href; }
    else {
      el = document.createElement('span'); el.className = 'na-off'; el.setAttribute('aria-disabled', 'true'); el.tabIndex = 0;
      el.title = 'Kein Zugriff';
      var go = function(){ note(code ? 'Kein Zugriff! Bitte kontaktiere Peter the Great im Spiel oder in Discord' : 'Kein Zugriff! Bitte zuerst mit deinem persönlichen Link anmelden (z. B. im Event Planner). Fragen: Peter the Great im Spiel oder in Discord'); };
      el.addEventListener('click', go); el.addEventListener('keydown', function(e){ if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); go(); } });
    }
    el.setAttribute('data-na', href); el.innerHTML = inner;
    if(old && old.parentNode) old.parentNode.replaceChild(el, old); else nav.appendChild(el);
  }
  function apply(mm){
    css();
    put('assignfsh.html', 'FORTRESS/SH PLAN', 'FSH', 'on');
    put('rallyleads.html', 'RALLY LEADS', 'LEADS', mm && mm.rallyleads ? 'on' : 'off');
    put('access.html', 'ADMIN', 'ADMIN', mm && mm.role === 'super' ? 'on' : null);
  }
  function run(){
    var C = window.EP_CONFIG; if(!code || !C || !C.url || !C.key) return;
    var H = {apikey: C.key, 'Content-Type': 'application/json'}; if(/^eyJ/.test(C.key)) H.Authorization = 'Bearer ' + C.key;
    fetch(C.url.replace(/\/+$/, '') + '/rest/v1/rpc/sa_me', {method: 'POST', headers: H, body: JSON.stringify({p_code: code})})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(j){
        try { sessionStorage.setItem('na_m', JSON.stringify({c: code, m: j || null})); } catch(e) {}
        apply(j);
      }).catch(function(){});
  }
  function start(){
    apply(m);
    if(!code) return;
    if(window.EP_CONFIG) return run();
    var sc = document.createElement('script'); sc.src = 'eventplan-config.js'; sc.onload = run; document.head.appendChild(sc);
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
