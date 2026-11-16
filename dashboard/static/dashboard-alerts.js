/* JuiceLab dashboard - live alerts panel.
   Renders the <ul id="alerts-list"> of templates/_alerts_panel.html.
   One row per group of identical alerts (same student, kind and challenge):
   the server groups unacknowledged alerts (GET /api/alerts?...&group=true),
   live SSE alerts are merged into their group here. Acknowledging a row
   clears the whole group in one request (POST /api/alerts/<id>/ack-group).
   The panel also drives the matrix (<tbody id="body-rows">): rows of students
   with an alert are marked and moved to the top, most urgent first, and a
   click on a student name scrolls to that row.
   Every label comes from the i18n catalog through window.T.
   Loaded by dashboard.html before its inline script, which owns the cohort
   id, the boot fetch and the EventSource and drives this module through
   window.JuicelabAlerts.create(). */
(function () {
  "use strict";

  var TOKEN_PREFIX_LEN = 8;
  /* Urgency order of the matrix rows, most urgent first. A kind missing from
     this list (unknown future kind) sorts after the known ones. */
  var KIND_ORDER = ["blocked", "stuck", "scripting", "idle", "absent"];
  var FOCUS_MS = 2600;  // how long a focused row stays highlighted

  function kindRank(kind) {
    var i = KIND_ORDER.indexOf(kind);
    return i === -1 ? KIND_ORDER.length : i;
  }

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

  /* create(opts) -> { render, add, remove, syncMatrix, loadFailed }
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
        + '<button type="button" class="alert-student" title="' + esc(g.token) + '" aria-label="'
        + esc(T("ALERT_FOCUS_ARIA", { name: g.name || g.token.substring(0, TOKEN_PREFIX_LEN) })) + '">' + who + '</button>'
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
      syncMatrix();
    }

    /* Most urgent alert kind per student token, from the groups on screen. */
    function worstKinds() {
      var worst = {};
      groups.forEach(function (g) {
        if (!(g.token in worst) || kindRank(g.kind) < kindRank(worst[g.token])) worst[g.token] = g.kind;
      });
      return worst;
    }

    function matrixRows() {
      var body = document.getElementById("body-rows");
      return body ? Array.prototype.slice.call(body.querySelectorAll("tr[data-student]")) : [];
    }

    /* Mark matrix rows that have an alert and order rows by urgency. Rows
       without alert keep their relative order (the sort is made stable with
       the original position, stored once in data-pos). Safe to call after
       every matrix re-render and every panel change. */
    function syncMatrix() {
      var rows = matrixRows();
      if (!rows.length) return;
      var worst = worstKinds();
      rows.forEach(function (tr, i) {
        if (!tr.hasAttribute("data-pos")) tr.setAttribute("data-pos", String(i));
        var kind = worst[tr.getAttribute("data-student")] || "";
        KIND_ORDER.forEach(function (k) { tr.classList.remove("row-alert-" + k); });
        tr.classList.toggle("row-alert", !!kind);
        if (kind && KIND_ORDER.indexOf(kind) !== -1) tr.classList.add("row-alert-" + kind);
        tr._alertRank = kind ? kindRank(kind) : KIND_ORDER.length + 1;
      });
      var sorted = rows.slice().sort(function (a, b) {
        return (a._alertRank - b._alertRank)
          || (Number(a.getAttribute("data-pos")) - Number(b.getAttribute("data-pos")));
      });
      var changed = sorted.some(function (tr, i) { return tr !== rows[i]; });
      if (changed) sorted.forEach(function (tr) { tr.parentNode.appendChild(tr); });
    }

    /* Scroll to the matrix row of `token` and highlight it briefly. Reports
       through opts.onError when the student has no visible row (no activity
       yet, or hidden by the filters). */
    function focusStudent(token) {
      var row = null;
      matrixRows().forEach(function (tr) { if (tr.getAttribute("data-student") === token) row = tr; });
      if (!row || row.classList.contains("row-filtered-out")) {
        opts.onError(T("ALERT_STUDENT_NOT_IN_MATRIX"));
        return;
      }
      row.scrollIntoView({ block: "center", behavior: "smooth" });
      row.classList.add("row-focus");
      setTimeout(function () { row.classList.remove("row-focus"); }, FOCUS_MS);
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
      var target = e.target.closest ? e.target.closest(".alert-ack-btn, .alert-student") : null;
      if (!target) return;
      var item = target.closest(".alert-item");
      if (!item) return;
      var id = item.getAttribute("data-alert-id");
      if (target.classList.contains("alert-ack-btn")) { ack(id, target); return; }
      var i = findIndex("id", id);
      if (i !== -1) focusStudent(groups[i].token);
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
      /* A situation ended (SSE `alert_resolved`): drop its group, if shown. */
      remove: function (a) {
        var i = findIndex("key", groupKey(a));
        if (i === -1) return;
        groups.splice(i, 1);
        draw();
      },
      /* Re-apply row marks and urgency order; call after a matrix re-render. */
      syncMatrix: syncMatrix,
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
