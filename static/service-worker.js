const CACHE_NAME = "nuestro-menu-static-v53";
const LIST_CACHE = "nuestro-menu-lista";
const STATIC_ASSETS = [
  "/static/css/app.css",
  "/static/css/app.css?v=44",
  "/static/vendor/fontawesome/css/fontawesome.min.css",
  "/static/vendor/fontawesome/css/solid.min.css",
  "/static/vendor/fontawesome/css/regular.min.css",
  "/static/vendor/fontawesome/webfonts/fa-solid-900.woff2",
  "/static/vendor/fontawesome/webfonts/fa-regular-400.woff2",
  "/static/js/app.js",
  "/static/js/app.js?v=30",
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
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key !== LIST_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

const tabPrefetches = new Map();

function prefetchKey(url) {
  return url.pathname + url.search;
}

function upstream(request, controller) {
  return fetch(new Request(request, { signal: controller.signal }));
}

function rememberTabPrefetch(request) {
  const key = prefetchKey(new URL(request.url));
  const previous = tabPrefetches.get(key);
  if (previous && !previous.claimed) previous.controller.abort();

  const controller = new AbortController();
  let settleCopy;
  let rejectCopy;
  const copyPromise = new Promise((resolve, reject) => {
    settleCopy = resolve;
    rejectCopy = reject;
  });
  copyPromise.catch(() => {});
  const entry = {
    controller: controller,
    claimed: false,
    seq: request.headers.get("X-Tab-Prefetch-Seq") || "",
    ready: copyPromise,
  };
  tabPrefetches.set(key, entry);

  return upstream(request, controller).then(
    (response) => {
      settleCopy(response.clone());
      setTimeout(() => {
        const current = tabPrefetches.get(key);
        if (current === entry && !current.claimed) tabPrefetches.delete(key);
      }, 4000);
      return response;
    },
    (error) => {
      rejectCopy(error);
      if (tabPrefetches.get(key) === entry) tabPrefetches.delete(key);
      throw error;
    }
  );
}

function takeTabPrefetch(request) {
  const key = prefetchKey(new URL(request.url));
  const entry = tabPrefetches.get(key);
  if (!entry) return null;
  entry.claimed = true;
  tabPrefetches.delete(key);
  return entry.ready.then((response) => {
    const headers = new Headers(response.headers);
    headers.delete("content-encoding");
    headers.delete("content-length");
    headers.set("X-Tab-Joined", "1");
    if (response.url) headers.set("X-Final-Url", response.url);
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: headers,
    });
  });
}

function storeList(request, response) {
  try {
    const url = new URL(request.url);
    if (url.origin !== self.location.origin || url.pathname !== "/lista/" || url.search) return;
    if (!response || !response.ok) return;
    const type = response.headers.get("content-type") || "";
    if (type.indexOf("text/html") === -1) return;
    const finalUrl = response.headers.get("X-Final-Url") || response.url || request.url;
    if (new URL(finalUrl, self.location.origin).pathname !== "/lista/") return;
    const copy = response.clone();
    caches.open(LIST_CACHE).then((cache) => cache.put("/lista/", copy)).catch(() => {});
  } catch (err) {
    /* la lista sigue disponible en red */
  }
}

function listFallback() {
  return caches.open(LIST_CACHE).then((cache) =>
    cache.match("/lista/").then((cached) => cached || caches.match("/offline/"))
  );
}

function networkOrOffline(request) {
  const list = new URL(request.url).pathname === "/lista/";
  return fetch(request).then(
    (response) => {
      storeList(request, response);
      return response;
    },
    () => (list ? listFallback() : caches.match(request).then((cached) => cached || caches.match("/offline/")))
  );
}

self.addEventListener("message", (event) => {
  const data = event.data;
  if (!data || data.type !== "drop-prefetch") return;
  const entry = tabPrefetches.get(data.key);
  if (!entry || entry.claimed || String(entry.seq) !== String(data.seq)) return;
  entry.controller.abort();
  tabPrefetches.delete(data.key);
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
  if (request.headers.get("X-Tab-Prefetch") === "1") {
    event.respondWith(rememberTabPrefetch(request));
    return;
  }
  const shared = takeTabPrefetch(request);
  if (shared) {
    event.respondWith(
      shared
        .then((response) => {
          storeList(request, response);
          return response;
        })
        .catch(() => networkOrOffline(request))
    );
    return;
  }
  event.respondWith(networkOrOffline(request));
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
