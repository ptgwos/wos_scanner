// Minimaler Service Worker, nur damit Browser die Seite als installierbar einstufen.
// Bewusst KEIN Caching und KEIN Eingreifen in Anfragen: Das Portal arbeitet mit
// Live-Daten (Supabase, Discord-Login), die Seite verhält sich wie ohne Service Worker.

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

// Leerer fetch-Handler ohne respondWith(): Der Browser behandelt jede Anfrage ganz normal.
self.addEventListener('fetch', () => {});
