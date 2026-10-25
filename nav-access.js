/* State 646 – adds the menu entries that depend on the permissions of the logged-in person
   (RALLY LEADS for people who may open it, ADMIN for the super admin). Uses the same login
   (localStorage ep_code) as the Event Planner. Without a login nothing is added.
   This only changes the menu; the real protection of the data sits in the database. */
(function(){
  var code = null; try { code = localStorage.getItem('ep_code'); } catch(e) {}
  if(!code) return;
  function run(){
    var C = window.EP_CONFIG; if(!C || !C.url || !C.key) return;
    var H = {apikey: C.key, 'Content-Type': 'application/json'}; if(/^eyJ/.test(C.key)) H.Authorization = 'Bearer ' + C.key;
    fetch(C.url.replace(/\/+$/, '') + '/rest/v1/rpc/sa_me', {method: 'POST', headers: H, body: JSON.stringify({p_code: code})})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(m){
        if(!m) return;
        var nav = document.querySelector('.sitenav'); if(!nav) return;
        var here = (location.pathname.split('/').pop() || '').toLowerCase();
        function add(href, long, short, ok){
          if(!ok || nav.querySelector('a[href="' + href + '"]') || nav.querySelector('[data-na="' + href + '"]')) return;
          var inner = '<span class="sn-l">' + long + '</span><span class="sn-s">' + short + '</span>', el;
          if(here === href){ el = document.createElement('span'); el.className = 'cur'; el.setAttribute('aria-current', 'page'); }
          else { el = document.createElement('a'); el.href = href; }
          el.setAttribute('data-na', href); el.innerHTML = inner; nav.appendChild(el);
        }
        add('rallyleads.html', 'RALLY LEADS', 'LEADS', !!m.rallyleads);
        add('admin.html', 'ADMIN', 'ADMIN', m.role === 'super');
      }).catch(function(){});
  }
  function start(){
    if(window.EP_CONFIG) return run();
    var sc = document.createElement('script'); sc.src = 'eventplan-config.js'; sc.onload = run; document.head.appendChild(sc);
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
