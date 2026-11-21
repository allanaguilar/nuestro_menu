(function () {
  if (window.__nuestroMenuReady) return;
  window.__nuestroMenuReady = true;

  document.addEventListener("change", function (event) {
    const input = event.target.closest && event.target.closest(".chore-photo-input");
    if (!input || !input.files || !input.files[0]) return;
    input.form.requestSubmit();
  });

  document.addEventListener("submit", function (event) {
    const form = event.target;
    if (!form.classList || !form.classList.contains("chore-photo-form")) return;
    const input = form.querySelector(".chore-photo-input");
    const files = input && input.files ? Array.prototype.slice.call(input.files) : [];
    if (!files.length || typeof createImageBitmap !== "function") return;
    event.preventDefault();
    const token = form.querySelector("[name=csrfmiddlewaretoken]").value;
    const shrink = function (file) {
      return createImageBitmap(file).then(function (bitmap) {
        const edge = Math.max(bitmap.width, bitmap.height);
        const scale = edge > 1280 ? 1280 / edge : 1;
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(bitmap.width * scale));
        canvas.height = Math.max(1, Math.round(bitmap.height * scale));
        canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
        bitmap.close();
        return new Promise(function (resolve) {
          canvas.toBlob(function (blob) { resolve(blob || file); }, "image/jpeg", 0.82);
        });
      }).catch(function () { return file; });
    };
    Promise.all(files.map(shrink)).then(function (blobs) {
      const body = new FormData();
      body.append("csrfmiddlewaretoken", token);
      blobs.forEach(function (blob) { body.append("foto", blob, "foto.jpg"); });
      input.value = "";
      return fetch(form.action, { method: "POST", body: body, credentials: "same-origin" });
    }).then(function () {
      window.location.assign("/por-hacer/");
    }).catch(function () {
      form.submit();
    });
  });

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
    const share = event.target.closest(".recipe-share");
    if (share) {
      const text = share.getAttribute("data-text") || "";
      if (!text) return;
      const title = share.getAttribute("data-title") || "Receta";
      const status = document.getElementById("recipe-share-status");
      const copied = function () {
        if (status) status.textContent = "Receta copiada. Pégala en WhatsApp u otra app.";
      };
      const openWhatsapp = function () {
        const url = "https://wa.me/?text=" + encodeURIComponent(text);
        const opened = window.open(url, "_blank", "noopener");
        if (!opened && status) status.textContent = "No se pudo abrir WhatsApp. Copia la receta a mano.";
      };
      const fallbackCopy = function () {
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
        if (ok) copied();
        else openWhatsapp();
      };
      const copyText = function () {
        if (navigator.clipboard && window.isSecureContext) {
          navigator.clipboard.writeText(text).then(copied).catch(fallbackCopy);
          return;
        }
        fallbackCopy();
      };
      if (navigator.share) {
        navigator.share({ title: title, text: text }).catch(function (err) {
          if (err && err.name === "AbortError") return;
          copyText();
        });
        return;
      }
      copyText();
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
    const accountBtn = event.target.closest(".account-toggle");
    if (accountBtn) {
      const panel = document.getElementById(accountBtn.getAttribute("aria-controls"));
      if (!panel) return;
      const open = panel.hidden;
      panel.hidden = !open;
      accountBtn.setAttribute("aria-expanded", open ? "true" : "false");
      return;
    }
    const photoOpen = event.target.closest(".chore-photo-open");
    if (photoOpen) {
      const dialog = document.getElementById("foto-modal");
      if (!dialog) return;
      const title = photoOpen.getAttribute("data-title") || "";
      dialog.querySelector("h2").textContent = title;
      const image = dialog.querySelector("img");
      image.src = photoOpen.getAttribute("data-src");
      image.alt = "Foto de " + title;
      const remove = document.getElementById("foto-modal-borrar");
      if (remove) remove.action = photoOpen.getAttribute("data-delete");
      dialog.showModal();
      return;
    }
    if (event.target.closest(".photo-modal-close") || event.target.id === "foto-modal") {
      const dialog = document.getElementById("foto-modal");
      if (dialog && dialog.open) dialog.close();
      return;
    }
    const editOpen = event.target.closest(".chore-edit-open");
    if (editOpen) {
      const dialog = document.getElementById("editar-modal");
      const form = document.getElementById("editar-tarea");
      if (!dialog || !form) return;
      form.action = editOpen.getAttribute("data-edit");
      const title = form.querySelector("#id_editar-title");
      const cadence = form.querySelector("#id_editar-cadence");
      const assignee = form.querySelector("#id_editar-assignee");
      if (title) title.value = editOpen.getAttribute("data-title") || "";
      if (cadence) cadence.value = editOpen.getAttribute("data-cadence") || "hoy";
      if (assignee) assignee.value = editOpen.getAttribute("data-assignee") || "";
      dialog.showModal();
      return;
    }
    if (event.target.closest(".edit-modal-close") || event.target.id === "editar-modal") {
      const dialog = document.getElementById("editar-modal");
      if (dialog && dialog.open) dialog.close();
      return;
    }
    const askOpen = event.target.closest(".chore-ask-open");
    if (askOpen) {
      const item = askOpen.closest(".chore-item, .recipe-item, .ask-wrap");
      const ask = item && item.querySelector(".chore-ask");
      if (!ask) return;
      const show = ask.hidden;
      document.querySelectorAll(".chore-ask").forEach(function (other) {
        other.hidden = true;
        const button = other.parentElement.querySelector(".chore-ask-open");
        if (button) button.setAttribute("aria-expanded", "false");
      });
      ask.hidden = !show;
      askOpen.setAttribute("aria-expanded", show ? "true" : "false");
      return;
    }
    const askCancel = event.target.closest(".chore-ask-cancel");
    if (askCancel) {
      const ask = askCancel.closest(".chore-ask");
      if (!ask) return;
      ask.hidden = true;
      const button = ask.parentElement.querySelector(".chore-ask-open");
      if (button) button.setAttribute("aria-expanded", "false");
      return;
    }
    const accountChoice = event.target.closest(".account-panel a, .account-panel button");
    if (accountChoice) {
      window.setTimeout(function () {
        const panel = accountChoice.closest(".account-panel");
        if (!panel) return;
        panel.hidden = true;
        const toggle = document.querySelector('[aria-controls="' + panel.id + '"]');
        if (toggle) toggle.setAttribute("aria-expanded", "false");
      }, 0);
    } else if (!event.target.closest(".account")) {
      document.querySelectorAll(".account-panel").forEach(function (panel) {
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
    if (form.id === "house-form") return;
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
    if (form.classList.contains("baby-day-form")) {
      document.querySelectorAll("form.baby-day-form").forEach(function (other) {
        if (other === form) return;
        other.querySelectorAll("select.baby-food-select").forEach(function (select) {
          const day = select.dataset.day;
          const slot = select.dataset.slot;
          if (!day || !slot) return;
          const current = select.dataset.current || "";
          const value = select.value || "";
          if (value === current) return;
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = "tambien";
          input.value = day + "|" + slot + "|" + value;
          form.appendChild(input);
        });
      });
    }
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
      showAiWait(form);
      return;
    }
    if (form.dataset.confirmed === "1") {
      delete form.dataset.confirmed;
      form.classList.add("is-loading");
      showAiWait(form);
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

  function showAiWait(form) {
    if (!form.classList.contains("recipe-ai-form")) return;
    const wait = document.getElementById("ai-wait");
    if (wait) wait.hidden = false;
  }
  function hideAiWait() {
    const wait = document.getElementById("ai-wait");
    if (wait) wait.hidden = true;
  }
  document.addEventListener("htmx:sendError", hideAiWait);
  document.addEventListener("htmx:responseError", hideAiWait);
  document.addEventListener("htmx:historyRestore", hideAiWait);

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
    if (!(select instanceof HTMLSelectElement)) return;
    if (!select.classList.contains("dish-select") && !select.classList.contains("baby-food-select")) return;
    const form = select.form;
    if (!form) return;
    if ((select.dataset.current || "") === select.value) return;
    const saver = form.querySelector('button[type="submit"]:not([formaction])');
    form.requestSubmit(saver || undefined);
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
    const title = item.done
      ? '<span class="shop-name">' + name + "</span>"
      : '<button type="button" class="shop-name" aria-label="Editar ' + name + '">' + name + "</button>";
    const handle = item.done ? "" : (
      '<button type="button" class="shop-handle" aria-label="Mover ' + name + '">' +
      '<i class="icon fa-solid fa-grip-vertical" aria-hidden="true"></i></button>'
    );
    return '<li class="shop-item' + doneClass + '" data-id="' + rawId + '" data-fresh="' + shopEscape(item.fresh || "") + '">' +
      '<form method="post" action="/lista/' + id + '/hecho/">' +
      shopCsrfInput() +
      '<label class="check"><input type="hidden" name="done" value="0">' +
      '<input type="checkbox" name="done" value="1"' + checked + ' aria-label="' + action + '" onchange="this.form.requestSubmit()"></label></form>' +
      '<div class="shop-copy">' + title + fresh + "</div>" +
      handle + "</li>";
  }

  function shopBoardHtml(items) {
    if (!items.length) return '<p class="lede">La lista está al día. Escribe lo que falte.</p>';
    const pending = items.filter(function (item) { return !item.done; });
    const cart = items.filter(function (item) { return item.done; });
    let html = '<div class="shop-board">';
    if (pending.length) {
      html += '<div class="shop-pending"><ul class="shop-list">' + pending.map(shopItemHtml).join("") + "</ul></div>";
    }
    if (cart.length) {
      html += '<section class="shop-cart" aria-labelledby="en-el-carro">' +
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
      let id = row.dataset.id || "";
      if (!id) {
        const form = row.querySelector("form[action]");
        const match = form && (form.getAttribute("action") || "").match(/\/lista\/([^/]+)\/hecho\/?$/);
        id = match ? decodeURIComponent(match[1]) : "";
      }
      if (!id) return;
      const box = row.querySelector('input[type="checkbox"]');
      const input = row.querySelector('input[name="name"]');
      const name = input ? input.value : (nameEl ? nameEl.textContent : row.dataset.name || "");
      if (!name) return;
      items.push({
        id: id,
        name: name,
        done: box ? box.checked : row.classList.contains("is-done"),
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
      items.push({ id: op.localId, name: name, done: false, fresh: "" });
    } else if (op.kind === "toggle") {
      const item = items.find(function (entry) { return entry.id === op.itemId; });
      if (!item) return { ok: false };
      item.done = op.done === "1";
    } else if (op.kind === "rename") {
      const name = shopClean(op.name);
      const item = items.find(function (entry) { return entry.id === op.itemId; });
      if (!item || !name) return { ok: false, error: "Escribe lo que falta." };
      if (name.length > 120) {
        return { ok: false, error: "El nombre es demasiado largo." };
      }
      if (items.some(function (entry) { return entry.id !== item.id && shopKey(entry.name) === shopKey(name); })) {
        return { ok: false, error: "Ya está en la lista." };
      }
      item.name = name;
    } else if (op.kind === "order") {
      const ids = String(op.order || "").split(",").filter(Boolean);
      const pending = items.filter(function (entry) { return !entry.done; });
      const byId = {};
      pending.forEach(function (entry) { byId[entry.id] = entry; });
      const next = [];
      ids.forEach(function (id) {
        if (byId[id]) {
          next.push(byId[id]);
          delete byId[id];
        }
      });
      pending.forEach(function (entry) {
        if (byId[entry.id]) next.push(entry);
      });
      const cart = items.filter(function (entry) { return entry.done; });
      items.splice(0, items.length);
      next.concat(cart).forEach(function (entry) { items.push(entry); });
    } else if (op.kind === "aisle") {
      return { ok: true };
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
    const rename = action.match(/\/lista\/([^/]+)\/nombre\/?$/);
    if (!rename) return;
    const input = form.querySelector('input[name="name"]');
    form.dataset.sent = "1";
    enqueueAndFlush({
      kind: "rename",
      itemId: decodeURIComponent(rename[1]),
      name: input ? input.value : "",
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
      order: op.order || "",
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
    } else if (op.kind === "rename") {
      url = "/lista/" + encodeURIComponent(op.itemId) + "/nombre/";
      body.append("name", op.name || "");
    } else if (op.kind === "order") {
      url = "/lista/orden/";
      body.append("order", op.order || "");
    } else if (op.kind === "aisle") {
      return Promise.resolve({ skip: true });
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
    const holdBoard = document.body.classList.contains("shop-dragging") || (
      focused && live.contains(focused) && (
        focused.tagName === "SELECT" || focused.tagName === "INPUT" || focused.tagName === "TEXTAREA"
      )
    );
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
    if (document.body.classList.contains("shop-dragging")) return;
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
    bar.querySelectorAll("[aria-current='page']").forEach(function (item) {
      item.removeAttribute("aria-current");
    });
    link.setAttribute("aria-current", "page");
    const title = link.getAttribute("data-title");
    const header = document.querySelector(".brand-section");
    if (title && header) header.textContent = title;
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

  function shopNameButton(name) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "shop-name";
    button.setAttribute("aria-label", "Editar " + name);
    button.textContent = name;
    return button;
  }

  function closeShopRename(form) {
    if (!form || form.dataset.sent === "1") return;
    form.dataset.sent = "1";
    form.replaceWith(shopNameButton(form.dataset.original || ""));
  }

  function openShopName(button) {
    const row = button.closest(".shop-item");
    if (!row || row.querySelector(".shop-rename")) return;
    const current = shopClean(button.textContent);
    const form = document.createElement("form");
    form.method = "post";
    form.action = "/lista/" + encodeURIComponent(row.dataset.id) + "/nombre/";
    form.className = "shop-rename";
    form.dataset.original = current;
    form.innerHTML = shopCsrfInput() +
      '<input class="field-input" name="name" maxlength="120" aria-label="Nombre">' +
      '<button type="button" class="shop-cancel">Cancelar</button>';
    const input = form.querySelector('input[name="name"]');
    input.value = current;
    button.replaceWith(form);
    input.focus();
    const end = input.value.length;
    if (input.setSelectionRange) input.setSelectionRange(end, end);
    input.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      closeShopRename(form);
    });
    input.addEventListener("blur", function () {
      window.setTimeout(function () {
        if (!form.isConnected || form.dataset.sent === "1") return;
        if (form.dataset.canceling === "1") {
          closeShopRename(form);
          return;
        }
        const next = shopClean(input.value);
        if (!next || next === current) {
          closeShopRename(form);
          return;
        }
        form.requestSubmit();
      }, 0);
    });
  }

  let shopDrag = null;

  function shopRows(list) {
    return Array.prototype.filter.call(list.children, function (node) {
      return node.classList && node.classList.contains("shop-item");
    });
  }

  function shopOrder(list) {
    return shopRows(list).map(function (row) { return row.dataset.id; }).join(",");
  }

  document.addEventListener("pointerdown", function (event) {
    const cancel = event.target.closest && event.target.closest(".shop-cancel");
    if (!cancel) return;
    const form = cancel.closest("form");
    if (form) form.dataset.canceling = "1";
  });

  document.addEventListener("click", function (event) {
    const cancel = event.target.closest && event.target.closest(".shop-cancel");
    if (cancel) {
      event.preventDefault();
      closeShopRename(cancel.closest("form"));
      return;
    }
    const button = event.target.closest && event.target.closest("button.shop-name");
    if (!button) return;
    event.preventDefault();
    openShopName(button);
  });

  document.addEventListener("pointerdown", function (event) {
    const handle = event.target.closest && event.target.closest(".shop-handle");
    if (!handle || !event.isPrimary || event.button) return;
    const row = handle.closest(".shop-item");
    const list = row && row.parentElement;
    if (!row || !list) return;
    event.preventDefault();
    shopDrag = { row: row, list: list, pointer: event.pointerId, start: shopOrder(list) };
    row.classList.add("is-dragging");
    document.body.classList.add("shop-dragging");
    if (handle.setPointerCapture) handle.setPointerCapture(event.pointerId);
  });

  document.addEventListener("pointermove", function (event) {
    if (!shopDrag || event.pointerId !== shopDrag.pointer) return;
    const rows = shopRows(shopDrag.list);
    let before = null;
    for (let index = 0; index < rows.length; index += 1) {
      const rect = rows[index].getBoundingClientRect();
      if (event.clientY < rect.top + rect.height / 2) {
        before = rows[index];
        break;
      }
    }
    if (before === shopDrag.row) return;
    shopDrag.list.insertBefore(shopDrag.row, before);
  });

  function endShopDrag(event) {
    if (!shopDrag || (event && event.pointerId !== shopDrag.pointer)) return;
    const drag = shopDrag;
    shopDrag = null;
    drag.row.classList.remove("is-dragging");
    document.body.classList.remove("shop-dragging");
    const order = shopOrder(drag.list);
    if (!order || order === drag.start) return;
    enqueueAndFlush({ kind: "order", order: order });
  }

  document.addEventListener("pointerup", endShopDrag);
  document.addEventListener("pointercancel", endShopDrag);

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
  bindHouseChat();

  function bindHouseChat() {
    document.addEventListener("click", function (event) {
      const open = event.target.closest && event.target.closest("#house-open");
      const close = event.target.closest && event.target.closest("#house-close");
      const dim = event.target.closest && event.target.closest("#house-dim");
      if (open) {
        event.preventDefault();
        setHouseOpen(true);
        return;
      }
      if (close || dim) {
        event.preventDefault();
        setHouseOpen(false);
      }
    });
    document.addEventListener("submit", function (event) {
      const form = event.target;
      if (!form || form.id !== "house-form") return;
      event.preventDefault();
      sendHouse(form);
    });
  }

  function setHouseOpen(next) {
    const sheet = document.getElementById("house-sheet");
    const dim = document.getElementById("house-dim");
    const open = document.getElementById("house-open");
    if (!sheet || !dim || !open) return;
    sheet.hidden = !next;
    dim.hidden = !next;
    open.hidden = next;
    open.setAttribute("aria-expanded", next ? "true" : "false");
    if (next) {
      const input = document.getElementById("house-msg");
      if (input) input.focus();
      if (sheet.dataset.loaded !== "1") loadHouse();
    } else {
      open.focus();
    }
  }

  function loadHouse() {
    const sheet = document.getElementById("house-sheet");
    if (!sheet) return;
    sheet.dataset.loaded = "1";
    fetch("/casa/", { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (data) {
        if (!data || !data.messages) return;
        data.messages.forEach(addHouseMessage);
      })
      .catch(function () {
        houseError("No hay conexión con la casa. Prueba otra vez.");
      });
  }

  function sendHouse(form) {
    const input = document.getElementById("house-msg");
    const text = input ? input.value.trim() : "";
    if (!text) {
      houseError("Escribe lo que quieres preguntar.");
      return;
    }
    houseError("");
    const button = form.querySelector("button[type=submit]");
    if (button) button.disabled = true;
    const body = new FormData();
    body.append("csrfmiddlewaretoken", csrfToken());
    body.append("text", text);
    fetch(form.action || "/casa/", {
      method: "POST",
      body: body,
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    }).then(function (response) {
      return response.json().then(function (data) {
        return { ok: response.ok, data: data };
      });
    }).then(function (result) {
      if (!result.ok) {
        houseError((result.data && result.data.error) || "La casa no ha podido contestar. Prueba otra vez.");
        return;
      }
      input.value = "";
      addHouseMessage(result.data.user);
      addHouseMessage(result.data.reply);
    }).catch(function () {
      houseError("No hay conexión con la casa. Prueba otra vez.");
    }).then(function () {
      form.classList.remove("is-loading");
      if (button) button.disabled = false;
      if (input) input.focus();
    });
  }

  function addHouseMessage(message) {
    const log = document.getElementById("house-log");
    const sheet = document.getElementById("house-sheet");
    const empty = document.getElementById("house-empty");
    if (!log || !message || !message.body) return;
    if (empty) empty.hidden = true;
    const turn = document.createElement("div");
    turn.className = "house-turn";
    const who = document.createElement("p");
    who.className = "house-who";
    who.textContent = message.role === "user" ? ((sheet && sheet.dataset.who) || "Tú") : "Casa";
    const bubble = document.createElement("p");
    bubble.className = "house-bubble" + (message.role === "user" ? " house-mine" : "");
    bubble.textContent = message.body;
    turn.appendChild(who);
    turn.appendChild(bubble);
    (message.receipts || []).forEach(function (line) {
      const pill = document.createElement("p");
      pill.className = "house-receipt";
      pill.textContent = line;
      turn.appendChild(pill);
    });
    log.appendChild(turn);
    log.scrollTop = log.scrollHeight;
  }

  function houseError(text) {
    const error = document.getElementById("house-error");
    if (!error) return;
    error.textContent = text || "";
    error.hidden = !text;
  }
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
