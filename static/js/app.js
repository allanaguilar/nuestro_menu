(function () {
  if (window.__nuestroMenuReady) return;
  window.__nuestroMenuReady = true;

  document.addEventListener("click", function (event) {
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
