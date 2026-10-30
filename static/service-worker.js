const CACHE_NAME = "nuestro-menu-static-v44";
const STATIC_ASSETS = [
  "/static/css/app.css",
  "/static/css/app.css?v=38",
  "/static/vendor/fontawesome/css/fontawesome.min.css",
  "/static/vendor/fontawesome/css/solid.min.css",
  "/static/vendor/fontawesome/css/regular.min.css",
  "/static/vendor/fontawesome/webfonts/fa-solid-900.woff2",
  "/static/vendor/fontawesome/webfonts/fa-regular-400.woff2",
  "/static/js/app.js",
  "/static/js/app.js?v=25",
  "/static/js/htmx.min.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png",
  "/static/manifest.webmanifest",
  "/offline/",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET") {
    return;
  }
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/cuentas/")) {
    return;
  }
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
    return;
  }
  event.respondWith(
    fetch(request).catch(() =>
      caches.match(request).then((cached) => cached || caches.match("/offline/"))
    )
  );
});

self.addEventListener("push", (event) => {
  let payload = { title: "Lista de compra", body: "", url: "/lista/" };
  try {
    payload = Object.assign(payload, event.data ? event.data.json() : {});
  } catch (err) {
    payload.body = event.data ? event.data.text() : "";
  }
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: "/static/icons/icon-192.png",
      data: { url: payload.url || "/lista/" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/lista/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if (client.url.indexOf("/lista/") !== -1 && "focus" in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow(target);
    })
  );
});
