(function () {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector("#menu-principal");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Cerrar menú" : "Abrir menú");
    });
  }

  document.addEventListener("submit", function (event) {
    const button = event.target.querySelector("[data-confirm]");
    if (button && !window.confirm(button.getAttribute("data-confirm"))) {
      event.preventDefault();
      return;
    }
    event.target.classList.add("is-loading");
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {
        /* sin service worker si el navegador lo rechaza */
      });
    });
  }
})();
