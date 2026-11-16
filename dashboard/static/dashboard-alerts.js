/* JuiceLab dashboard - live alerts panel.
   Renders the <ul id="alerts-list"> of templates/_alerts_panel.html.
   One row per group of identical alerts (same student, kind and challenge):
   the server groups unacknowledged alerts (GET /api/alerts?...&group=true),
   live SSE alerts are merged into their group here. Acknowledging a row
   clears the whole group in one request (POST /api/alerts/<id>/ack-group).
   Every label comes from the i18n catalog through window.T.
   Loaded by dashboard.html before its inline script, which owns the cohort
   id, the boot fetch and the EventSource and drives this module through
   window.JuicelabAlerts.create(). */
(function () {
  "use strict";

  var TOKEN_PREFIX_LEN = 8;

  function T(key, params) { return window.T(key, params); }

  /* SSE payloads expose `alert_kind`; REST /api/alerts returns `kind`. */
  function kindOf(a) { return String(a.alert_kind || a.kind || ""); }

  /* Identity of a group, used in memory only. It never goes into the DOM:
     rows carry the numeric alert id instead (an HTML attribute cannot hold
     every character, e.g. U+0000 is rewritten by the parser). */
  function groupKey(a) {
    return JSON.stringify([a.student_token || "", kindOf(a), a.challenge_key || ""]);
  }

  function kindLabel(kind) {
    var key = "ALERT_KIND_" + kind.toUpperCase();
    var label = T(key);
    return (label && label !== key) ? label : kind;
  }

  /* Locale date for an ISO timestamp, or "" when it cannot be parsed. */
  function formatDate(iso) {
    var ms = Date.parse(iso || "");
    if (isNaN(ms)) return "";
    try {
      return new Date(ms).toLocaleString(document.documentElement.lang || undefined,
        { dateStyle: "short", timeStyle: "short" });
    } catch (e) {
      return new Date(ms).toLocaleString();
    }
  }

  /* create(opts) -> { render, add, loadFailed }
     opts.escapeHtml(str)   HTML-escapes a value (required).
     opts.csrfHeaders(base) returns request headers carrying the CSRF token (required).
     opts.onError(message)  reports a failure to the teacher (required).
     Returns null when the panel markup is absent from the page. */
  function create(opts) {
    var list = document.getElementById("alerts-list");
    var counter = document.getElementById("alerts-count");
    if (!list) return null;
    var esc = opts.escapeHtml;
    var groups = [];  // newest first

    function toGroup(a) {
      return {
        key: groupKey(a),
        id: a.id,
        kind: kindOf(a),
        token: String(a.student_token || ""),
        name: a.display_name || "",
        challenge: a.challenge_key || "",
        count: a.count || 1,
        since: a.first_at || a.created_at || ""
      };
    }

    function rowHtml(g) {
      var who = g.name
        ? esc(g.name)
        : esc(g.token.substring(0, TOKEN_PREFIX_LEN)) + "&hellip;";
      var since = formatDate(g.since);
      return '<li class="alert-item alert-kind-' + esc(g.kind) + '" data-alert-id="' + esc(g.id) + '">'
        + '<span class="alert-kind">' + esc(kindLabel(g.kind)) + '</span>'
        + '<span class="alert-student" title="' + esc(g.token) + '">' + who + '</span>'
        + (g.challenge ? '<span class="alert-challenge">' + esc(g.challenge) + '</span>' : '')
        + (g.count > 1
            ? '<span class="alert-repeat" title="' + esc(T("ALERT_REPEAT_TITLE", { n: g.count })) + '">&times;' + g.count + '</span>'
            : '')
        + (since ? '<span class="alert-since">' + esc(T("ALERT_SINCE", { date: since })) + '</span>' : '')
        + '<button class="alert-ack-btn" type="button" aria-label="' + esc(T("ALERT_ACK_ARIA")) + '">'
        + esc(T("ALERT_ACK_BUTTON")) + '</button>'
        + '</li>';
    }

    function emptyHtml(key) {
      return '<li class="alerts-empty" id="alerts-empty">' + esc(T(key)) + '</li>';
    }

    function draw() {
      if (counter) counter.textContent = groups.length ? String(groups.length) : "";
      list.innerHTML = groups.length ? groups.map(rowHtml).join("") : emptyHtml("ALERT_EMPTY");
    }

    /* Index of the group matching `value` on field `field` ("key" or "id"), or -1. */
    function findIndex(field, value) {
      for (var i = 0; i < groups.length; i++) { if (String(groups[i][field]) === String(value)) return i; }
      return -1;
    }

    /* Acknowledge a whole group. The row is removed only once the server
       confirmed; on failure it stays so the teacher can retry. */
    function ack(id, btn) {
      var i = findIndex("id", id);
      if (i === -1) return;
      var key = groups[i].key;
      btn.disabled = true;
      fetch("/api/alerts/" + encodeURIComponent(id) + "/ack-group", {
        method: "POST", credentials: "include", headers: opts.csrfHeaders()
      }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        var j = findIndex("key", key);
        if (j !== -1) groups.splice(j, 1);
        draw();
      }).catch(function () {
        btn.disabled = false;
        opts.onError(T("ALERT_ACK_FAILED"));
      });
    }

    list.addEventListener("click", function (e) {
      var btn = e.target.closest ? e.target.closest(".alert-ack-btn") : null;
      if (!btn) return;
      var item = btn.closest(".alert-item");
      if (item) ack(item.getAttribute("data-alert-id"), btn);
    });

    return {
      /* Replace the panel content with server groups (newest first). */
      render: function (alerts) {
        groups = (alerts || []).map(toGroup);
        draw();
      },
      /* Merge one live alert: bump its group to the top, or open a new one. */
      add: function (a) {
        var g = toGroup(a);
        var i = findIndex("key", g.key);
        if (i !== -1) {
          var old = groups.splice(i, 1)[0];
          g.count = old.count + 1;
          g.since = old.since || g.since;
          g.name = g.name || old.name;
        }
        groups.unshift(g);
        draw();
      },
      /* The boot fetch failed: say so instead of showing "no alert". */
      loadFailed: function () {
        groups = [];
        if (counter) counter.textContent = "";
        list.innerHTML = emptyHtml("ALERT_LOAD_FAILED");
      }
    };
  }

  window.JuicelabAlerts = { create: create };
})();
