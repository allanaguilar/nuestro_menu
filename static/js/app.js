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
    const more = event.target.closest(".nav-more-toggle");
    if (more) {
      const panel = document.getElementById(more.getAttribute("aria-controls"));
      if (!panel) return;
      const open = panel.hidden;
      panel.hidden = !open;
      more.setAttribute("aria-expanded", open ? "true" : "false");
      return;
    }
    if (!event.target.closest(".nav-more")) {
      const panel = document.querySelector(".nav-more-panel");
      const toggle = document.querySelector(".nav-more-toggle");
      if (panel && !panel.hidden) {
        panel.hidden = true;
        if (toggle) toggle.setAttribute("aria-expanded", "false");
      }
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
      replaceShop(form.action, new FormData(form));
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

  function replaceShop(url, body) {
    const live = document.getElementById("shop-live");
    if (!live) return;
    shopBusy = true;
    const options = { headers: { "X-Shop": "1" } };
    if (body) {
      options.method = "POST";
      options.body = body;
    }
    fetch(url, options)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        updateShopStatus(data);
        if (data.html && data.revision !== live.dataset.revision) {
          live.innerHTML = data.html;
          live.dataset.revision = data.revision;
        }
      })
      .catch(function () {})
      .finally(function () { shopBusy = false; });
  }

  function pollShop() {
    const live = document.getElementById("shop-live");
    if (!live || shopBusy || !live.dataset.fragment) return;
    if (document.activeElement && live.contains(document.activeElement)) return;
    replaceShop(live.dataset.fragment);
  }

  let shopTimer = 0;
  function watchShop() {
    if (shopTimer || !document.getElementById("shop-live")) return;
    shopTimer = window.setInterval(pollShop, 8000);
  }
  watchShop();
  document.addEventListener("htmx:afterSettle", watchShop);

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {
        /* sin service worker si el navegador lo rechaza */
      });
    });
  }
})();
