(function () {
  if (window.__nuestroMenuReady) return;
  window.__nuestroMenuReady = true;

  document.addEventListener("click", function (event) {
    const day = event.target.closest(".day-open");
    if (day) {
      const panel = document.getElementById(day.getAttribute("aria-controls"));
      if (!panel) return;
      const open = panel.hidden;
      panel.hidden = !open;
      day.setAttribute("aria-expanded", open ? "true" : "false");
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

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {
        /* sin service worker si el navegador lo rechaza */
      });
    });
  }
})();
