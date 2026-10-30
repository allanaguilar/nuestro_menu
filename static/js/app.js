(function () {
  if (window.__nuestroMenuReady) return;
  window.__nuestroMenuReady = true;

  document.addEventListener("click", function (event) {
    const clear = event.target.closest(".search-clear");
    if (clear) {
      const field = clear.closest(".search-field");
      const input = field && field.querySelector('input[name="q"]');
      const form = clear.closest("form.filters");
      if (input && form) {
        event.preventDefault();
        input.value = "";
        clear.hidden = true;
        form.requestSubmit();
      }
      return;
    }
    const copy = event.target.closest(".copy-invite");
    if (copy) {
      const code = document.getElementById("invite-url");
      const text = code ? code.textContent.trim() : "";
      if (!text) return;
      const finish = function () {
        copy.textContent = "Copiado";
        window.setTimeout(function () {
          copy.textContent = "Copiar enlace";
        }, 2000);
      };
      const fallback = function () {
        const area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.left = "-9999px";
        document.body.appendChild(area);
        area.select();
        let ok = false;
        try {
          ok = document.execCommand("copy");
        } catch (err) {
          ok = false;
        }
        area.remove();
        if (ok) finish();
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(finish).catch(fallback);
      } else {
        fallback();
      }
      return;
    }
    const more = event.target.closest(".nav-more-toggle, .tabbar-more-toggle");
    if (more) {
      const panel = document.getElementById(more.getAttribute("aria-controls"));
      if (!panel) return;
      const open = panel.hidden;
      panel.hidden = !open;
      more.setAttribute("aria-expanded", open ? "true" : "false");
      return;
    }
    if (!event.target.closest(".nav-more, .tabbar-more")) {
      document.querySelectorAll(".nav-more-panel, .tabbar-more-panel").forEach(function (panel) {
        if (panel.hidden) return;
        panel.hidden = true;
        const toggle = document.querySelector('[aria-controls="' + panel.id + '"]');
        if (toggle) toggle.setAttribute("aria-expanded", "false");
      });
    }
    const day = event.target.closest(".day-open, .recipe-preview");
    if (day) {
      const panel = document.getElementById(day.getAttribute("aria-controls"));
      if (!panel) return;
      const open = panel.hidden;
      panel.hidden = !open;
      day.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) {
        window.requestAnimationFrame(function () {
          panel.scrollIntoView({ block: "nearest" });
        });
      }
      return;
    }
    const toggle = event.target.closest(".nav-toggle");
    if (!toggle) return;
    const nav = document.getElementById("menu-principal");
    if (!nav) return;
    const open = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.setAttribute("aria-label", open ? "Cerrar menú" : "Abrir menú");
  });

  let confirming = false;
  document.addEventListener("submit", function (event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.classList.contains("shop-add")) {
      event.preventDefault();
      event.stopPropagation();
      const field = form.querySelector('input[name="client_key"]');
      if (field) field.value = shopClient();
      const input = form.querySelector('input[name="name"]');
      if (input) submitShopAdd(input);
      return;
    }
    const button = event.submitter;
    if (form.classList.contains("day-rail-pick")) {
      document.querySelectorAll("form.day-rail-pick").forEach(function (other) {
        if (other === form) return;
        const select = other.querySelector("select.dish-select");
        if (!select || !select.value || !select.dataset.day) return;
        if (select.dataset.current && select.value === select.dataset.current) return;
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "tambien";
        input.value = select.dataset.day + "|" + select.value;
        form.appendChild(input);
      });
    }
    if (form.closest("#shop-live")) {
      event.preventDefault();
      event.stopPropagation();
      queueShopForm(form);
      return;
    }
    const message = button && button.getAttribute("data-confirm");
    if (!message) {
      form.classList.add("is-loading");
      return;
    }
    if (form.dataset.confirmed === "1") {
      delete form.dataset.confirmed;
      form.classList.add("is-loading");
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    if (confirming) return;
    confirming = true;
    let accepted = false;
    try {
      accepted = window.confirm(message);
    } finally {
      confirming = false;
    }
    if (!accepted) return;
    form.dataset.confirmed = "1";
    window.setTimeout(function () {
      form.requestSubmit(button);
    }, 0);
  }, true);

  function releaseForm(event) {
    const form = event.detail && event.detail.elt;
    if (form && form.classList) form.classList.remove("is-loading");
  }
  document.addEventListener("input", function (event) {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.name !== "q") return;
    const field = input.closest(".search-field");
    const clear = field && field.querySelector(".search-clear");
    if (clear) clear.hidden = !input.value;
  });

  document.addEventListener("change", function (event) {
    const form = event.target.closest("form.pref-form");
    if (!form) return;
    form.requestSubmit();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Enter") return;
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.name !== "q") return;
    const form = input.closest("form.filters");
    if (!form) return;
    event.preventDefault();
    form.requestSubmit();
  });

  document.addEventListener("change", function (event) {
    const select = event.target;
    if (!(select instanceof HTMLSelectElement) || !select.classList.contains("baby-food-select")) return;
    const slot = select.closest(".baby-slot");
    const tag = slot && slot.querySelector(".tag");
    if (!tag) return;
    const option = select.selectedOptions[0];
    const texture = option && option.dataset.texture;
    if (!texture) {
      tag.textContent = "";
      tag.hidden = true;
      return;
    }
    tag.textContent = option.dataset.new ? texture + " · nuevo" : texture;
    tag.hidden = false;
  });

  document.addEventListener("change", function (event) {
    const select = event.target;
    if (!(select instanceof HTMLSelectElement) || !select.classList.contains("dish-select")) return;
    const pick = select.closest(".day-rail-pick");
    const tag = pick && pick.querySelector(".tag");
    if (!tag) return;
    const option = select.selectedOptions[0];
    const category = option && option.dataset.category;
    if (!category) {
      tag.textContent = "";
      tag.hidden = true;
      return;
    }
    const same = select.dataset.current && select.value === select.dataset.current;
    const source = same ? select.dataset.source || "propuesto" : "elegido a mano";
    tag.textContent = category + " · " + source;
    tag.hidden = false;
  });

  document.addEventListener("htmx:afterRequest", releaseForm);
  document.addEventListener("htmx:sendError", releaseForm);
  document.addEventListener("htmx:responseError", releaseForm);
  document.addEventListener("htmx:timeout", releaseForm);

  let shopBusy = false;
  let shopEpoch = 0;
  let shopChain = Promise.resolve();
  let shopBoot = null;
  let flushing = null;
  let shopReachable = navigator.onLine;
  let shopAuthBlocked = false;
  let memoryQueue = [];

  const SHOP_ICONS = {
    none: "fa-tag",
    frutas: "fa-apple-whole",
    verduras: "fa-carrot",
    lacteos: "fa-bottle-droplet",
    carnes: "fa-drumstick-bite",
    pescados: "fa-fish",
    fridge: "fa-snowflake",
    pantry: "fa-jar",
    cleaning: "fa-pump-soap",
    other: "fa-ellipsis",
    cart: "fa-cart-shopping",
  };

  function shopClient() {
    const key = "nuestro-menu-shop";
    let id = "";
    try {
      id = window.sessionStorage.getItem(key) || "";
      if (!id) {
        id = Math.random().toString(36).slice(2) + Date.now().toString(36);
        window.sessionStorage.setItem(key, id);
      }
    } catch (err) {
      id = "este";
    }
    return id;
  }

  function updateShopStatus(data) {
    const pending = document.getElementById("shop-pending");
    const viewers = document.getElementById("shop-viewers");
    if (pending) {
      pending.textContent = data.pending || "";
      pending.hidden = !data.pending;
    }
    if (viewers) {
      viewers.textContent = data.viewers || "";
      viewers.hidden = !data.viewers;
    }
  }

  let latestBoard = null;
  let shopDbPromise = null;

  function shopHome() {
    const live = document.getElementById("shop-live");
    if (live && live.dataset.home) return live.dataset.home;
    return document.body.dataset.home || "";
  }

  function shopClean(name) {
    return String(name || "").trim().replace(/\s+/g, " ");
  }

  function shopKey(name) {
    return shopClean(name).toLocaleLowerCase("es");
  }

  function shopEscape(value) {
    return String(value || "").replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function shopDb() {
    if (!window.indexedDB) return Promise.reject(new Error("idb"));
    if (shopDbPromise) return shopDbPromise;
    shopDbPromise = new Promise(function (resolve, reject) {
      const request = window.indexedDB.open("nuestro-menu-shop", 1);
      request.onupgradeneeded = function () {
        const db = request.result;
        if (!db.objectStoreNames.contains("queue")) {
          db.createObjectStore("queue", { keyPath: "id", autoIncrement: true });
        }
        if (!db.objectStoreNames.contains("meta")) {
          db.createObjectStore("meta", { keyPath: "home" });
        }
      };
      request.onsuccess = function () { resolve(request.result); };
      request.onerror = function () {
        shopDbPromise = null;
        reject(request.error);
      };
    });
    return shopDbPromise;
  }

  function queueFor(home) {
    if (!home) return Promise.resolve([]);
    return shopDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        const request = db.transaction("queue", "readonly").objectStore("queue").getAll();
        request.onsuccess = function () {
          const rows = (request.result || []).filter(function (row) { return row.home === home; });
          rows.sort(function (a, b) { return a.id - b.id; });
          resolve(rows);
        };
        request.onerror = function () { reject(request.error); };
      });
    }).catch(function () { return []; });
  }

  function loadBoard(home) {
    if (!home) return Promise.resolve(null);
    return shopDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        const request = db.transaction("meta", "readonly").objectStore("meta").get(home);
        request.onsuccess = function () { resolve(request.result || null); };
        request.onerror = function () { reject(request.error); };
      });
    }).catch(function () { return null; });
  }

  function rememberBoard() {
    const live = document.getElementById("shop-live");
    if (!live) return null;
    const pending = document.getElementById("shop-pending");
    latestBoard = {
      home: shopHome(),
      html: live.innerHTML,
      pending: pending && !pending.hidden ? pending.textContent : "",
      revision: live.dataset.revision || "",
    };
    return latestBoard;
  }

  function saveBoard() {
    const record = rememberBoard();
    if (!record || !record.home) return Promise.resolve();
    return shopDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        const tx = db.transaction("meta", "readwrite");
        tx.objectStore("meta").put(record);
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    }).catch(function () {});
  }

  function persistNew(record) {
    return shopDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        const request = db.transaction("queue", "readwrite").objectStore("queue").add(record);
        request.onsuccess = function () {
          record.id = request.result;
          resolve(record);
        };
        request.onerror = function () { reject(request.error); };
      });
    });
  }

  function deleteQueue(id) {
    if (typeof id !== "number") return Promise.resolve();
    return shopDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        const tx = db.transaction("queue", "readwrite");
        tx.objectStore("queue").delete(id);
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    }).catch(function () {});
  }

  function dropMemory(id) {
    memoryQueue = memoryQueue.filter(function (row) { return row.id !== id; });
  }

  function remapQueue(from, to) {
    const home = shopHome();
    memoryQueue.forEach(function (row) {
      if (row.itemId === from) row.itemId = to;
    });
    return shopDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        const tx = db.transaction("queue", "readwrite");
        const request = tx.objectStore("queue").openCursor();
        request.onsuccess = function () {
          const cursor = request.result;
          if (!cursor) return;
          if (cursor.value.home === home && cursor.value.itemId === from) {
            const value = cursor.value;
            value.itemId = to;
            cursor.update(value);
          }
          cursor.continue();
        };
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    }).catch(function () {});
  }

  function shopAisles() {
    const node = document.getElementById("shop-aisles");
    if (node) {
      try {
        const parsed = JSON.parse(node.textContent);
        if (parsed && parsed.length) return parsed;
      } catch (err) {
        /* usa la lista fija */
      }
    }
    return [
      ["none", "Sin pasillo"],
      ["frutas", "Frutas"],
      ["verduras", "Verduras"],
      ["lacteos", "Lácteos"],
      ["carnes", "Carnes"],
      ["pescados", "Pescados"],
      ["fridge", "Nevera"],
      ["pantry", "Despensa"],
      ["cleaning", "Limpieza"],
      ["other", "Otros"],
    ];
  }

  function shopAisleAllowed(value) {
    return shopAisles().some(function (pair) { return pair[0] === value; });
  }

  function shopPendingLabel(items) {
    if (!items.length) return "";
    const count = items.filter(function (item) { return !item.done; }).length;
    if (count === 0) return "No queda nada";
    if (count === 1) return "Queda 1";
    return "Quedan " + count;
  }

  function shopCsrfInput() {
    return '<input type="hidden" name="csrfmiddlewaretoken" value="' + shopEscape(csrfToken()) + '">';
  }

  function shopAisleOptions(current) {
    return shopAisles().map(function (pair) {
      const selected = pair[0] === current ? " selected" : "";
      return '<option value="' + shopEscape(pair[0]) + '"' + selected + ">" + shopEscape(pair[1]) + "</option>";
    }).join("");
  }

  function shopItemHtml(item) {
    const name = shopEscape(item.name);
    const id = encodeURIComponent(item.id);
    const rawId = shopEscape(item.id);
    const checked = item.done ? " checked" : "";
    const doneClass = item.done ? " is-done" : "";
    const action = item.done ? "Devolver " + name + " a la lista" : "Marcar " + name + " como comprado";
    const fresh = item.fresh
      ? '<span class="shop-who">' + shopEscape(item.fresh) + " lo añadió ahora</span>"
      : "";
    const aisle = item.done ? "" : (
      '<form method="post" action="/lista/' + id + '/pasillo/">' +
      shopCsrfInput() +
      '<label class="sr-only" for="aisle-' + rawId + '">Pasillo de ' + name + "</label>" +
      '<select id="aisle-' + rawId + '" class="field-input shop-aisle-select" name="aisle" onchange="this.form.requestSubmit()">' +
      shopAisleOptions(item.aisle) +
      "</select></form>"
    );
    return '<li class="shop-item' + doneClass + '" data-id="' + rawId + '" data-aisle="' + shopEscape(item.aisle || "none") + '" data-fresh="' + shopEscape(item.fresh || "") + '">' +
      '<form method="post" action="/lista/' + id + '/hecho/">' +
      shopCsrfInput() +
      '<label class="check"><input type="hidden" name="done" value="0">' +
      '<input type="checkbox" name="done" value="1"' + checked + ' aria-label="' + action + '" onchange="this.form.requestSubmit()">' +
      '<span class="shop-copy"><span class="shop-name">' + name + "</span>" + fresh + "</span></label></form>" +
      aisle + "</li>";
  }

  function shopAisleHtml(key, label, group) {
    const icon = SHOP_ICONS[key] || "fa-tag";
    return '<section class="shop-aisle" aria-labelledby="pasillo-' + shopEscape(key) + '">' +
      '<h2 id="pasillo-' + shopEscape(key) + '"><i class="icon fa-solid ' + icon + '" aria-hidden="true"></i><span>' +
      shopEscape(label) + "</span></h2><ul class=\"shop-list\">" + group.map(shopItemHtml).join("") + "</ul></section>";
  }

  function shopBoardHtml(items) {
    if (!items.length) return '<p class="lede">La lista está al día. Escribe lo que falte.</p>';
    const aisles = shopAisles();
    const pending = items.filter(function (item) { return !item.done; }).sort(function (a, b) {
      if (a.name < b.name) return -1;
      if (a.name > b.name) return 1;
      return 0;
    });
    const cart = items.filter(function (item) { return item.done; }).sort(function (a, b) {
      if (a.name < b.name) return -1;
      if (a.name > b.name) return 1;
      return 0;
    });
    const known = {};
    aisles.forEach(function (pair) { known[pair[0]] = true; });
    let html = '<div class="shop-board">';
    aisles.forEach(function (pair) {
      const group = pending.filter(function (item) { return item.aisle === pair[0]; });
      if (group.length) html += shopAisleHtml(pair[0], pair[1], group);
    });
    const stray = pending.filter(function (item) { return !known[item.aisle]; });
    if (stray.length) html += shopAisleHtml("other", "Otros", stray);
    if (cart.length) {
      html += '<section class="shop-aisle shop-cart" aria-labelledby="en-el-carro">' +
        '<h2 id="en-el-carro"><i class="icon fa-solid fa-cart-shopping" aria-hidden="true"></i><span>En el carro</span></h2>' +
        '<ul class="shop-list">' + cart.map(shopItemHtml).join("") + "</ul>" +
        '<form method="post" action="/lista/vaciar/">' + shopCsrfInput() +
        '<button class="button button-ghost" type="submit">Vaciar lo comprado</button></form></section>';
    }
    return html + "</div>";
  }

  function readShopItems(root) {
    const items = [];
    root.querySelectorAll(".shop-item").forEach(function (row) {
      const nameEl = row.querySelector(".shop-name");
      if (!nameEl) return;
      let id = row.dataset.id || "";
      if (!id) {
        const form = row.querySelector("form[action]");
        const match = form && (form.getAttribute("action") || "").match(/\/lista\/([^/]+)\/(?:hecho|pasillo)\/?$/);
        id = match ? decodeURIComponent(match[1]) : "";
      }
      if (!id) return;
      const box = row.querySelector('input[type="checkbox"]');
      const select = row.querySelector('select[name="aisle"]');
      items.push({
        id: id,
        name: nameEl.textContent,
        done: box ? box.checked : row.classList.contains("is-done"),
        aisle: (select && select.value) || row.dataset.aisle || "none",
        fresh: row.dataset.fresh || "",
      });
    });
    return items;
  }

  function writeShopBoard(live, items) {
    live.innerHTML = shopBoardHtml(items);
    live.dataset.revision = "local";
    const label = document.getElementById("shop-pending");
    const text = shopPendingLabel(items);
    if (label) {
      label.textContent = text;
      label.hidden = !text;
    }
    return saveBoard();
  }

  function showAddError(message) {
    const slot = document.getElementById("shop-add-error");
    if (!slot) return;
    if (!message) {
      slot.textContent = "";
      slot.hidden = true;
      return;
    }
    slot.hidden = false;
    slot.innerHTML = '<ul class="errorlist"><li>' + shopEscape(message) + "</li></ul>";
  }

  function refreshShopStatus() {
    const node = document.getElementById("shop-offline");
    if (!node) return;
    const waiting = memoryQueue.length > 0;
    let message = "";
    if (shopAuthBlocked && waiting) message = "Entra de nuevo para enviar los cambios.";
    else if (waiting && (!navigator.onLine || !shopReachable)) {
      message = "Sin conexión. Los cambios se enviarán al volver la red.";
    } else if (waiting) message = "Enviando los cambios guardados…";
    else if (!navigator.onLine) message = "Sin conexión. Estás viendo la última lista guardada.";
    node.textContent = message;
    node.hidden = !message;
  }

  function applyShopOp(op) {
    const live = document.getElementById("shop-live");
    if (!live) return { ok: false };
    const items = readShopItems(live);
    if (op.kind === "add") {
      const name = shopClean(op.name);
      if (!name) return { ok: false, error: "Escribe lo que falta." };
      if (items.some(function (item) { return shopKey(item.name) === shopKey(name); })) {
        return { ok: false, error: "Ya está en la lista." };
      }
      items.push({ id: op.localId, name: name, aisle: "none", done: false, fresh: "" });
    } else if (op.kind === "toggle") {
      const item = items.find(function (entry) { return entry.id === op.itemId; });
      if (!item) return { ok: false };
      item.done = op.done === "1";
    } else if (op.kind === "aisle") {
      const item = items.find(function (entry) { return entry.id === op.itemId; });
      if (!item || item.done || !shopAisleAllowed(op.aisle)) return { ok: false };
      item.aisle = op.aisle;
    } else if (op.kind === "clear") {
      for (let index = items.length - 1; index >= 0; index -= 1) {
        if (items[index].done) items.splice(index, 1);
      }
    } else return { ok: false };
    shopEpoch += 1;
    writeShopBoard(live, items);
    return { ok: true };
  }

  function removeLocal(localId) {
    const live = document.getElementById("shop-live");
    if (!live || !localId) return Promise.resolve();
    const items = readShopItems(live).filter(function (item) { return item.id !== localId; });
    return writeShopBoard(live, items);
  }

  function remapLocal(from, to) {
    const live = document.getElementById("shop-live");
    if (live) {
      const items = readShopItems(live);
      let changed = false;
      items.forEach(function (item) {
        if (item.id === from) {
          item.id = to;
          changed = true;
        }
      });
      if (changed) writeShopBoard(live, items);
    }
    return remapQueue(from, to);
  }

  function restoreBoard(live, board) {
    live.innerHTML = board.html;
    if (board.revision) live.dataset.revision = board.revision;
    const label = document.getElementById("shop-pending");
    if (label) {
      label.textContent = board.pending || "";
      label.hidden = !board.pending;
    }
  }

  function cacheListDocument() {
    if (!window.caches || !navigator.onLine || location.pathname !== "/lista/") return;
    window.caches.open("nuestro-menu-lista").then(function (cache) {
      return cache.add(new Request("/lista/", { credentials: "same-origin" }));
    }).catch(function () {});
  }

  function bootShop(live) {
    const home = live.dataset.home || shopHome();
    return Promise.all([loadBoard(home), queueFor(home)]).then(function (result) {
      const saved = result[0];
      const pendingLocal = memoryQueue.filter(function (row) { return !row.id; });
      memoryQueue = result[1].concat(pendingLocal);
      const board = latestBoard && latestBoard.home === home ? latestBoard : saved;
      if ((memoryQueue.length || !navigator.onLine) && board && board.html) {
        restoreBoard(live, board);
        return;
      }
      return saveBoard();
    }).then(function () {
      refreshShopStatus();
      cacheListDocument();
    });
  }

  function submitShopAdd(input) {
    const name = shopClean(input.value);
    if (!name) {
      showAddError("Escribe lo que falta.");
      return;
    }
    if (name.length > 120) {
      showAddError("Asegúrate de que este valor tenga como máximo 120 caracteres (tiene " + name.length + ").");
      return;
    }
    enqueueAndFlush({
      kind: "add",
      name: name,
      localId: "local-" + Math.random().toString(36).slice(2) + Date.now().toString(36),
    });
  }

  function queueShopForm(form) {
    const action = form.getAttribute("action") || form.action || "";
    if (/\/vaciar\/?$/.test(action)) {
      enqueueAndFlush({ kind: "clear" });
      return;
    }
    const toggle = action.match(/\/lista\/([^/]+)\/hecho\/?$/);
    if (toggle) {
      const box = form.querySelector('input[type="checkbox"]');
      enqueueAndFlush({
        kind: "toggle",
        itemId: decodeURIComponent(toggle[1]),
        done: box && box.checked ? "1" : "0",
      });
      return;
    }
    const aisle = action.match(/\/lista\/([^/]+)\/pasillo\/?$/);
    if (!aisle) return;
    const select = form.querySelector('select[name="aisle"]');
    enqueueAndFlush({
      kind: "aisle",
      itemId: decodeURIComponent(aisle[1]),
      aisle: select ? select.value : "",
    });
  }

  function enqueueAndFlush(op) {
    const applied = applyShopOp(op);
    if (!applied.ok) {
      if (applied.error) showAddError(applied.error);
      return;
    }
    if (op.kind === "add") {
      const input = document.querySelector('.shop-add input[name="name"]');
      if (input) input.value = "";
      showAddError("");
    }
    const record = {
      home: shopHome(),
      kind: op.kind,
      localId: op.localId || "",
      itemId: op.itemId || "",
      name: op.name || "",
      done: op.done || "",
      aisle: op.aisle || "",
    };
    if (!record.home) return;
    memoryQueue.push(record);
    shopBusy = true;
    refreshShopStatus();
    shopChain = shopChain.then(function () {
      return persistNew(record).catch(function () {
        record.id = "mem-" + Date.now() + "-" + memoryQueue.length;
        return record;
      }).then(function () { return flushQueue(); });
    }).catch(function () {
      refreshShopStatus();
    }).finally(function () {
      if (!memoryQueue.length) shopBusy = false;
    });
  }

  function sendShopOp(op) {
    const body = new FormData();
    body.append("csrfmiddlewaretoken", csrfToken());
    let url = "";
    if (op.kind === "add") {
      url = "/lista/anadir/";
      body.append("name", op.name);
      body.append("client_key", shopClient());
    } else if (op.kind === "toggle") {
      url = "/lista/" + encodeURIComponent(op.itemId) + "/hecho/";
      body.append("done", op.done === "1" ? "1" : "0");
    } else if (op.kind === "aisle") {
      url = "/lista/" + encodeURIComponent(op.itemId) + "/pasillo/";
      body.append("aisle", op.aisle || "");
    } else if (op.kind === "clear") {
      url = "/lista/vaciar/";
    } else return Promise.resolve({ skip: true });
    return fetch(url, {
      method: "POST",
      body: body,
      credentials: "same-origin",
      headers: {
        "X-Shop": "1",
        "X-Shop-Client": shopClient(),
        "X-CSRFToken": csrfToken(),
      },
    }).then(readShopResponse).catch(function () { return { offline: true }; });
  }

  function readShopResponse(response) {
    if ((response.redirected && response.url.indexOf("/cuentas/") !== -1) || response.status === 403) {
      return { auth: true };
    }
    if (response.status === 404) return { skip: true };
    const type = response.headers.get("content-type") || "";
    if (type.indexOf("application/json") === -1) return { retry: true };
    return response.json().then(function (data) {
      return {
        html: data.html || "",
        revision: data.revision || "",
        pending: data.pending || "",
        viewers: data.viewers || "",
        created: data.created_id || "",
        matched: data.matched_id || "",
        error: data.error || "",
      };
    }).catch(function () { return { retry: true }; });
  }

  function applyServerShop(data) {
    const live = document.getElementById("shop-live");
    if (!live || !data) return Promise.resolve();
    updateShopStatus(data);
    if (data.html) {
      live.innerHTML = data.html;
      if (data.revision) live.dataset.revision = data.revision;
    }
    shopReachable = true;
    return saveBoard();
  }

  function drainQueue() {
    const epoch = shopEpoch;
    const home = shopHome();
    function finish(result) {
      if (memoryQueue.length) return step();
      if (shopEpoch !== epoch) return null;
      if (result && result.html) return applyServerShop(result);
      return refreshFromServer();
    }
    function step() {
      const op = memoryQueue[0];
      if (!op || op.home !== home || !op.id) return Promise.resolve();
      return sendShopOp(op).then(function (result) {
        if (result.offline || result.retry) {
          shopReachable = false;
          return null;
        }
        if (result.auth) {
          shopAuthBlocked = true;
          shopReachable = true;
          return null;
        }
        shopAuthBlocked = false;
        shopReachable = true;
        if (result.skip) {
          return deleteQueue(op.id).then(function () {
            dropMemory(op.id);
            return finish(null);
          });
        }
        const mapped = result.created || result.matched;
        return deleteQueue(op.id).then(function () {
          dropMemory(op.id);
          if (op.localId && mapped) return remapLocal(op.localId, mapped);
          if (result.error && op.localId && memoryQueue.length) return removeLocal(op.localId);
        }).then(function () {
          if (result.error) showAddError(result.error);
          else if (op.kind === "add") showAddError("");
          return finish(result);
        });
      });
    }
    return step();
  }

  function flushQueue() {
    if (!shopHome()) return Promise.resolve();
    if (!navigator.onLine) {
      shopReachable = false;
      refreshShopStatus();
      return Promise.resolve();
    }
    if (!memoryQueue.length) {
      refreshShopStatus();
      return Promise.resolve();
    }
    if (flushing) return flushing;
    shopBusy = true;
    flushing = drainQueue().finally(function () {
      flushing = null;
      shopBusy = false;
      refreshShopStatus();
    });
    return flushing;
  }

  function replaceShop(url) {
    const live = document.getElementById("shop-live");
    if (!live) return Promise.resolve();
    const epoch = shopEpoch;
    const focused = document.activeElement;
    const holdBoard = focused && live.contains(focused) && focused.tagName === "SELECT";
    return fetch(url, {
      credentials: "same-origin",
      headers: { "X-Shop": "1", "X-Shop-Client": shopClient() },
    }).then(function (response) {
      if (response.redirected && response.url.indexOf("/cuentas/") !== -1) {
        shopAuthBlocked = true;
        return null;
      }
      const type = response.headers.get("content-type") || "";
      if (type.indexOf("application/json") === -1) throw new Error("shop");
      return response.json();
    }).then(function (data) {
      if (!data || shopEpoch !== epoch || memoryQueue.length) return;
      shopReachable = true;
      shopAuthBlocked = false;
      updateShopStatus(data);
      if (!holdBoard && data.html && data.revision !== live.dataset.revision) {
        live.innerHTML = data.html;
        if (data.revision) live.dataset.revision = data.revision;
      }
      if (!holdBoard) return saveBoard();
    }).catch(function () {
      shopReachable = false;
      refreshShopStatus();
    });
  }

  function refreshFromServer() {
    const live = document.getElementById("shop-live");
    if (!live || !live.dataset.fragment) return Promise.resolve();
    return replaceShop(live.dataset.fragment);
  }

  function pollShop() {
    const live = document.getElementById("shop-live");
    if (!live || !live.dataset.fragment || flushing) return;
    if (!navigator.onLine) {
      shopReachable = false;
      refreshShopStatus();
      return;
    }
    if (memoryQueue.length) {
      flushQueue();
      return;
    }
    if (shopBusy) return;
    replaceShop(live.dataset.fragment);
  }

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    if (match) return decodeURIComponent(match[1]);
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input && input.value ? input.value : "";
  }

  function urlBase64ToUint8Array(value) {
    const padded = value + "=".repeat((4 - (value.length % 4)) % 4);
    const base64 = padded.replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    const bytes = new Uint8Array(raw.length);
    for (let index = 0; index < raw.length; index += 1) bytes[index] = raw.charCodeAt(index);
    return bytes;
  }

  function enablePush(button) {
    if (!button || button.dataset.pushing === "1") return;
    button.dataset.pushing = "1";
    navigator.serviceWorker.ready
      .then(function (registration) {
        return registration.pushManager.getSubscription().then(function (existing) {
          if (existing) return existing;
          return registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(button.dataset.key),
          });
        });
      })
      .then(function (subscription) {
        const data = subscription.toJSON();
        return fetch(button.dataset.subscribe, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken(),
          },
          body: JSON.stringify({
            endpoint: data.endpoint,
            keys: data.keys,
            client_key: shopClient(),
          }),
        });
      })
      .then(function (response) {
        if (!response.ok) throw new Error("aviso");
        button.hidden = true;
      })
      .catch(function () {
        button.hidden = false;
        const iphone = /iPhone|iPad/.test(navigator.userAgent);
        const installed = window.matchMedia("(display-mode: standalone)").matches;
        button.textContent = iphone && !installed ? "Añádela a inicio para avisarte" : "Avisarme";
      })
      .finally(function () {
        button.dataset.pushing = "";
      });
  }

  function watchPush() {
    const button = document.getElementById("shop-push");
    if (!button) return;
    const iphone = /iPhone|iPad/.test(navigator.userAgent);
    const installed = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
    if (!("Notification" in window) || !("PushManager" in window) || !("serviceWorker" in navigator)) {
      button.hidden = false;
      if (iphone && !installed) button.textContent = "Añádela a inicio para avisarte";
      return;
    }
    if (!button.dataset.bound) {
      button.dataset.bound = "1";
      button.addEventListener("click", function () {
        Notification.requestPermission().then(function (permission) {
          if (permission === "granted") enablePush(button);
          else button.hidden = true;
        });
      });
    }
    if (Notification.permission === "granted") {
      button.hidden = true;
      enablePush(button);
      return;
    }
    button.hidden = Notification.permission !== "default";
  }

  let tabMark = null;
  let tabCommitted = false;
  let tabPrefetch = null;
  let tabPrefetchSeq = 0;

  function tabPrefetchKey(link) {
    const url = new URL(link.href, location.origin);
    return url.pathname + url.search;
  }

  function dropTabPrefetch() {
    if (!tabPrefetch || tabPrefetch.committed) return;
    const dropped = tabPrefetch;
    tabPrefetch = null;
    dropped.controller.abort();
    const worker = navigator.serviceWorker && navigator.serviceWorker.controller;
    if (worker) {
      worker.postMessage({ type: "drop-prefetch", key: dropped.key, seq: dropped.seq });
    }
  }

  function startTabPrefetch(link) {
    const key = tabPrefetchKey(link);
    if (tabPrefetch && !tabPrefetch.committed && tabPrefetch.key === key) return;
    dropTabPrefetch();
    const controller = new AbortController();
    const seq = ++tabPrefetchSeq;
    tabPrefetch = { key: key, seq: seq, controller: controller, committed: false };
    fetch(key, {
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
      headers: {
        "X-Tab-Prefetch": "1",
        "X-Tab-Prefetch-Seq": String(seq)
      }
    }).catch(function () {});
  }

  function tabLink(event) {
    if (event.button && event.button !== 0) return null;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return null;
    const link = event.target.closest(".tabbar a[href]");
    if (!link || link.getAttribute("href").charAt(0) === "#") return null;
    return link;
  }

  function rememberTab() {
    const current = document.querySelector(".tabbar [aria-current='page']");
    const header = document.querySelector(".brand-section");
    return {
      current: current,
      header: header,
      headerText: header ? header.textContent : ""
    };
  }

  function showTab(link) {
    const bar = link.closest(".tabbar");
    if (!bar) return;
    const chosen = link.closest(".tabbar-more-panel")
      ? bar.querySelector(".tabbar-more-toggle")
      : link;
    bar.querySelectorAll("[aria-current='page']").forEach(function (item) {
      item.removeAttribute("aria-current");
    });
    if (chosen) chosen.setAttribute("aria-current", "page");
    const title = link.getAttribute("data-title");
    const header = document.querySelector(".brand-section");
    if (title && header) header.textContent = title;
    const panel = document.getElementById("menu-tab-mas");
    if (panel && link.closest(".tabbar-more-panel")) {
      panel.hidden = true;
      const toggle = bar.querySelector(".tabbar-more-toggle");
      if (toggle) toggle.setAttribute("aria-expanded", "false");
    }
  }

  function restoreTab() {
    if (!tabMark) return;
    const bar = document.querySelector(".tabbar");
    if (bar) {
      bar.querySelectorAll("[aria-current='page']").forEach(function (item) {
        item.removeAttribute("aria-current");
      });
      if (tabMark.current && bar.contains(tabMark.current)) {
        tabMark.current.setAttribute("aria-current", "page");
      }
    }
    if (tabMark.header) tabMark.header.textContent = tabMark.headerText;
    tabMark = null;
  }

  document.addEventListener("pointerdown", function (event) {
    const link = tabLink(event);
    if (!link) return;
    tabCommitted = false;
    tabMark = rememberTab();
    showTab(link);
    startTabPrefetch(link);
  }, true);

  document.addEventListener("pointercancel", function () {
    if (tabCommitted) return;
    restoreTab();
    dropTabPrefetch();
  }, true);

  document.addEventListener("click", function (event) {
    const link = tabLink(event);
    if (!link) return;
    tabCommitted = true;
    if (tabPrefetch && tabPrefetch.key === tabPrefetchKey(link)) tabPrefetch.committed = true;
    else dropTabPrefetch();
    if (!tabMark) tabMark = rememberTab();
    showTab(link);
  }, true);

  document.addEventListener("htmx:afterSettle", function () {
    tabMark = null;
    tabCommitted = false;
    tabPrefetch = null;
  });
  document.addEventListener("htmx:sendError", restoreTab);
  document.addEventListener("htmx:responseError", restoreTab);

  let shopTimer = 0;
  function watchShop() {
    const live = document.getElementById("shop-live");
    if (!live) {
      const home = shopHome();
      if (!home) return;
      queueFor(home).then(function (rows) {
        const pendingLocal = memoryQueue.filter(function (row) { return !row.id; });
        if (!memoryQueue.some(function (row) { return row.id; })) memoryQueue = rows.concat(pendingLocal);
        if (navigator.onLine) return flushQueue();
      }).catch(function () {});
      return;
    }
    if (live.dataset.offlineReady !== "1") {
      live.dataset.offlineReady = "1";
      shopBusy = true;
      shopBoot = bootShop(live).finally(function () {
        shopBusy = false;
        refreshShopStatus();
      });
    }
    Promise.resolve(shopBoot).then(function () {
      if (!document.getElementById("shop-live")) return;
      if (navigator.onLine) return flushQueue();
    }).then(function () {
      if (shopTimer || !document.getElementById("shop-live")) return;
      pollShop();
      shopTimer = window.setInterval(pollShop, 4000);
    });
  }
  window.addEventListener("online", function () {
    shopReachable = true;
    shopAuthBlocked = false;
    flushQueue();
  });
  window.addEventListener("offline", function () {
    shopReachable = false;
    refreshShopStatus();
  });
  watchShop();
  watchPush();
  document.addEventListener("htmx:afterSettle", function () {
    watchShop();
    watchPush();
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {
        /* sin service worker si el navegador lo rechaza */
      });
    });
  }
})();
