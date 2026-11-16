/* JuiceLab dashboard - student x challenge matrix.
   Becomes the ONLY renderer of the matrix: the server stops emitting the
   <thead>/<tbody> rows and only embeds the summary JSON, and every refresh
   (first load, SSE snapshot, refetch) goes through render(summary) below.
   render() rebuilds the KPIs, the header row, the per-challenge stats row
   and one row per student, mirroring the previous server-side Jinja markup
   (same elements, classes and texts), plus these additions: students with
   no recorded event get "row-inactive", cells with a duration get a time
   pill, and the stats row shows the per-challenge progress. It binds no
   event handler and runs no filter: the caller does both right after.
   Every label comes from the i18n catalog through window.T, and every
   dynamic value is escaped with opts.escapeHtml.
   Loaded by dashboard.html, which owns the cohort id, the boot snapshot and
   the EventSource, and drives this module through create(). */
(function () {
  "use strict";

  /* Fixed tag option list, same values and order as the server template. */
  var TAG_VALUES = ["none", "a_voir", "ok", "absent", "a_interroger"];

  function T(key, params) { return window.T(key, params); }

  /* True only for real finite numbers: every "new" summary field may be
     absent or null on an older server and must then be skipped. */
  function isNum(v) { return typeof v === "number" && isFinite(v); }

  /* Missing counters render as 0 so the stats row never shows "undefined". */
  function numOr0(v) { return isNum(v) ? v : 0; }

  /* Human duration: "" unless sec is a number > 0; under a minute the
     "less than a minute" label, "N min" below an hour (at least 1 minute),
     then hours with the minutes zero-padded to 2 digits. */
  function formatDuration(sec) {
    if (!isNum(sec) || sec <= 0) return "";
    if (sec < 60) return T("DURATION_LT_MIN");
    if (sec < 3600) return T("DURATION_MIN", { n: Math.max(1, Math.round(sec / 60)) });
    var h = Math.floor(sec / 3600);
    var m = Math.floor((sec % 3600) / 60);
    return T("DURATION_H", { h: h, m: (m < 10 ? "0" : "") + m });
  }

  /* create(opts) -> { render }
     opts.cohort      cohort id, put in the student/diploma links (required).
     opts.escapeHtml  HTML-escapes a value (required).
     Returns null when the matrix markup (#head-row or #body-rows) is absent
     from the page. */
  function create(opts) {
    var headRow = document.getElementById("head-row");
    var bodyRows = document.getElementById("body-rows");
    if (!headRow || !bodyRows) return null;
    var esc = opts.escapeHtml;
    var cohortQs = "?cohort=" + encodeURIComponent(opts.cohort || "");

    /* Write a KPI by id. Absent elements (#students-total may not exist on
       older templates) and absent values are silently skipped. */
    function setText(id, value) {
      var el = document.getElementById(id);
      if (el && value !== null && value !== undefined) el.textContent = value;
    }

    /* Sticky first cell of a body row: display name (or token prefix),
       inline name editor, tag selector, token hint and the detail / diploma
       / note actions. Same markup as the server template, with the token
       escaped in text and attributes, URL-encoded in the link paths. */
    function stickyCellHtml(student, sEsc, sUrl, name, tag) {
      var tagOpts = TAG_VALUES.map(function (v) {
        return '<option value="' + v + '"' + (v === tag ? ' selected' : '') + '>'
          + esc(T("TAG_" + v.toUpperCase())) + '</option>';
      }).join("");
      return '<td class="sticky-col" title="' + sEsc + '">'
        + '<strong class="student-display' + (name ? '' : ' student-display-missing') + '">'
        + esc(name || (T("STUDENT_UNNAMED_PREFIX") + ' ' + student.substring(0, 6))) + '</strong>'
        + '<input class="name-edit' + (name ? '' : ' name-missing') + '" type="text" value="' + esc(name)
        + '" placeholder="' + esc(T("STUDENT_NAME_MISSING_PLACEHOLDER"))
        + '" maxlength="100" aria-label="' + esc(T("ARIA_STUDENT_NAME")) + '">'
        + '<select class="tag-select" data-student="' + sEsc + '" aria-label="'
        + esc(T("ARIA_STUDENT_TAG")) + '">' + tagOpts + '</select>'
        + '<small class="token-hint">' + esc(student.substring(0, 8)) + '&hellip;</small>'
        + '<span class="row-actions">'
        + '<a href="/admin/student/' + sUrl + cohortQs + '" target="_blank" rel="noopener" title="'
        + esc(T("ACTION_DETAIL")) + '" aria-label="' + esc(T("ACTION_DETAIL")) + '" data-drilldown="1">D</a> '
        + '<a href="/admin/diploma/' + sUrl + cohortQs + '" target="_blank" rel="noopener" title="'
        + esc(T("ACTION_DIPLOMA")) + '">' + esc(T("ROW_ACTION_DIPLOMA_SHORT")) + '</a> '
        + '<button type="button" class="note-btn" data-student="' + sEsc + '" title="'
        + esc(T("ACTION_NOTE")) + '" aria-label="' + esc(T("ACTION_NOTE")) + '">N</button>'
        + '</span></td>';
    }

    /* One challenge cell: the pills in server order (solved, hints, journal,
       quiz, flag), then the time pill when the slot recorded a duration.
       Without slot: the empty "-" pill, like the server template. */
    function cellHtml(slot, challenge, student) {
      if (!slot) return '<span class="pill empty">-</span>';
      var parts = ['<div class="cell">'];
      if (slot.solved) parts.push('<span class="pill solved">solved</span>');
      parts.push('<span class="pill hints">hints ' + esc(slot.hints || 0) + '/5</span>');
      if (slot.journal) {
        parts.push('<span class="pill journal" data-key="' + esc(challenge)
          + '" data-student="' + esc(student) + '" tabindex="0" role="button">journal</span>');
      }
      if (slot.quiz_score !== null && slot.quiz_score !== undefined) {
        parts.push('<span class="pill quiz">quiz ' + esc(slot.quiz_score) + '/100</span>');
      }
      if (slot.flag_verified) parts.push('<span class="pill flag">flag +10</span>');
      if (isNum(slot.duration_sec) && slot.duration_sec > 0) {
        parts.push('<span class="pill time" title="' + esc(T("PILL_TIME_TITLE")) + '">'
          + esc(formatDuration(slot.duration_sec)) + '</span>');
      }
      parts.push('</div>');
      return parts.join('');
    }

    /* Score cell, mirror of the server-rendered <td class="score-col">:
       final average, else partial score (starred), else "not available". */
    function totalCellHtml(total) {
      var has = function (v) { return v !== null && v !== undefined; };
      if (total && has(total.avg_score)) {
        return '<span class="score-total">' + esc(total.avg_score) + '/100</span>';
      }
      if (total && has(total.partial_score)) {
        return '<span class="score-total score-partial" title="' + esc(T("SCORE_PARTIAL_TITLE")) + '">'
          + esc(total.partial_score) + '/100 *</span>';
      }
      return '<span class="score-na" title="' + esc(T("SCORE_NA_TITLE")) + '">&mdash;</span>';
    }

    /* One stats-row cell for a challenge: solved / in progress / not started
       counters in the title and as spans, then the average hints and the
       average duration when the server provides them. No entry: empty cell. */
    function statsCellHtml(challenge, statsMap) {
      var cs = statsMap ? statsMap[challenge] : null;
      if (!cs) return '<th class="challenge-col stats-cell"></th>';
      var html = '<th class="challenge-col stats-cell" title="'
        + esc(T("STATS_CELL_TITLE", {
          solved: numOr0(cs.solved),
          in_progress: numOr0(cs.in_progress),
          not_started: numOr0(cs.not_started)
        })) + '">'
        + '<span class="stat stat-solved">' + esc(numOr0(cs.solved)) + '</span>'
        + '<span class="stat stat-progress">' + esc(numOr0(cs.in_progress)) + '</span>'
        + '<span class="stat stat-todo">' + esc(numOr0(cs.not_started)) + '</span>';
      var avg = isNum(cs.avg_hints) ? esc(T("STATS_AVG_HINTS", { n: cs.avg_hints })) : '';
      var dur = formatDuration(cs.avg_duration_sec);
      if (dur) avg += (avg ? ' &middot; ' : '') + esc(dur);
      if (avg) html += '<small class="stat-avg">' + avg + '</small>';
      return html + '</th>';
    }

    /* The stats row filled under the header: label, empty activity cell, one
       cell per challenge, empty score cell (same column count as #head-row). */
    function statsRowHtml(challenges, statsMap) {
      var html = '<th class="sticky-col">' + esc(T("STATS_ROW_LABEL")) + '</th>'
        + '<th class="activity-col"></th>';
      for (var i = 0; i < challenges.length; i++) {
        html += statsCellHtml(challenges[i], statsMap);
      }
      return html + '<th class="score-col"></th>';
    }

    /* One body row: sticky student cell, event counter, one cell per
       challenge, total score. A student whose event counter is 0 or missing
       gets the "row-inactive" class on the <tr>. */
    function rowHtml(student, summary, challenges) {
      var sEsc = esc(student);
      var sUrl = encodeURIComponent(student);
      var name = (summary.names || {})[student] || '';
      var tag = (summary.tags || {})[student] || 'none';
      var evCount = (summary.event_counts || {})[student] || 0;
      var matrix = summary.matrix || {};
      var html = '<tr data-student="' + sEsc + '"' + (evCount > 0 ? '' : ' class="row-inactive"') + '>';
      html += stickyCellHtml(student, sEsc, sUrl, name, tag);
      html += '<td class="activity-col"><span class="pill '
        + (evCount > 0 ? 'hints' : 'empty') + '">' + esc(evCount) + '</span></td>';
      for (var i = 0; i < challenges.length; i++) {
        html += '<td data-cell="' + esc(challenges[i]) + '">'
          + cellHtml((matrix[student] || {})[challenges[i]], challenges[i], student) + '</td>';
      }
      html += '<td class="score-col">' + totalCellHtml((summary.totals || {})[student]) + '</td>';
      return html + '</tr>';
    }

    /* Replace the whole matrix from a server summary snapshot: KPIs first,
       then the empty-state switch, the header row, the stats row and the
       body rows. Never throws on missing or null summary fields. */
    function render(summary) {
      summary = summary || {};
      var students = summary.students || [];
      var challenges = summary.challenges || [];

      setText("students-count",
        isNum(summary.active_students) ? summary.active_students : students.length);
      setText("students-total", students.length);
      setText("challenges-count", challenges.length);
      setText("events-count", summary.events_total);

      var wrap = document.getElementById("matrix-wrap");
      var emptyMsg = document.getElementById("empty-msg");
      if (!students.length) {
        if (wrap) wrap.style.display = 'none';
        if (emptyMsg) emptyMsg.style.display = '';
        return;
      }
      if (emptyMsg) emptyMsg.style.display = 'none';
      if (wrap) wrap.style.display = '';

      // Header row: must stay the mirror of the server <thead> (same columns
      // and classes), otherwise the page changes shape after first refresh.
      var headHtml = '<th class="sticky-col">' + esc(T("TABLE_STUDENT")) + '</th>'
        + '<th class="activity-col">' + esc(T("KPI_EVENTS")) + '</th>';
      for (var i = 0; i < challenges.length; i++) {
        headHtml += '<th class="challenge-col">' + esc(challenges[i]) + '</th>';
      }
      headHtml += '<th class="score-col">' + esc(T("TABLE_SCORE_TOTAL")) + '</th>';
      headRow.innerHTML = headHtml;

      var statsRow = document.getElementById("stats-row");
      if (statsRow) statsRow.innerHTML = statsRowHtml(challenges, summary.challenge_stats || {});

      var html = '';
      for (var j = 0; j < students.length; j++) {
        html += rowHtml(students[j], summary, challenges);
      }
      bodyRows.innerHTML = html;
    }

    return {
      /* Rebuild the matrix (KPIs, header, stats row, body) from a summary. */
      render: render
    };
  }

  window.JuicelabMatrix = { create: create };
})();
