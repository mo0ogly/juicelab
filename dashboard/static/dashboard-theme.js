/* JuiceLab dashboard - theme toggle.
   Loaded synchronously in <head> (no defer) so data-theme is set before the
   first paint: no flash of the wrong theme. Default theme is "light" so the
   dashboard is readable in a bright room / on a projector; the teacher's
   choice is persisted in localStorage under "juicelab-theme".
   The toggle buttons are rendered server-side in _lang_switch.html (labels via
   the i18n catalog); this script only wires their behaviour. */
(function () {
  "use strict";
  var KEY = "juicelab-theme";
  var root = document.documentElement;

  function read() {
    try {
      var v = localStorage.getItem(KEY);
      return (v === "dark" || v === "light") ? v : "light";
    } catch (e) {
      return "light";
    }
  }

  function syncButtons(theme) {
    var btns = document.querySelectorAll("[data-theme-set]");
    for (var i = 0; i < btns.length; i++) {
      var wanted = btns[i].getAttribute("data-theme-set");
      btns[i].setAttribute("aria-pressed", wanted === theme ? "true" : "false");
    }
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    try { localStorage.setItem(KEY, theme); } catch (e) {}
    syncButtons(theme);
  }

  // Run immediately (head, pre-paint).
  root.setAttribute("data-theme", read());

  document.addEventListener("DOMContentLoaded", function () {
    syncButtons(root.getAttribute("data-theme") || "light");
    var btns = document.querySelectorAll("[data-theme-set]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener("click", function () {
        apply(this.getAttribute("data-theme-set"));
      });
    }
  });
})();
