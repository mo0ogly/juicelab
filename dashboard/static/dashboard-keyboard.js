// Phase 3 Task 3 - keyboard shortcuts + help overlay.
// Loaded by dashboard.html as <script src nonce>. Same-origin, CSP-locked.

(function () {
  let focusedRowIdx = -1;

  function visibleRows() {
    return Array.from(document.querySelectorAll('#body-rows tr:not(.row-filtered-out)'));
  }

  function setFocusedRow(idx) {
    const rows = visibleRows();
    if (!rows.length) { focusedRowIdx = -1; return; }
    idx = Math.max(0, Math.min(rows.length - 1, idx));
    rows.forEach(r => r.classList.remove('row-focused'));
    rows[idx].classList.add('row-focused');
    rows[idx].scrollIntoView({ block: 'nearest' });
    focusedRowIdx = idx;
  }

  function focusedToken() {
    const rows = visibleRows();
    if (focusedRowIdx < 0 || focusedRowIdx >= rows.length) return null;
    return rows[focusedRowIdx].getAttribute('data-student');
  }

  function cycleTagOnFocusedRow() {
    const rows = visibleRows();
    if (focusedRowIdx < 0) return;
    const sel = rows[focusedRowIdx].querySelector('.tag-select');
    if (!sel) return;
    const order = ['none', 'a_voir', 'ok', 'absent', 'a_interroger'];
    const idx = order.indexOf(sel.value);
    sel.value = order[(idx + 1) % order.length];
    sel.dispatchEvent(new Event('change'));
  }

  function openDetail() {
    const rows = visibleRows();
    if (focusedRowIdx < 0) return;
    const link = rows[focusedRowIdx].querySelector('a[data-drilldown="1"]') || rows[focusedRowIdx].querySelector('.row-actions a');
    if (link) link.click();
  }

  function toggleHelp(open) {
    const h = document.getElementById('kbd-help');
    if (!h) return;
    if (open === undefined) h.classList.toggle('open');
    else h.classList.toggle('open', open);
  }

  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, textarea, select, [contenteditable="true"]')) return;
    if (e.key === 'j') { setFocusedRow(focusedRowIdx < 0 ? 0 : focusedRowIdx + 1); e.preventDefault(); }
    else if (e.key === 'k') { setFocusedRow(focusedRowIdx < 0 ? 0 : focusedRowIdx - 1); e.preventDefault(); }
    else if (e.key === 'Enter' && focusedRowIdx >= 0) { openDetail(); e.preventDefault(); }
    else if (e.key === 't' && focusedRowIdx >= 0) { cycleTagOnFocusedRow(); e.preventDefault(); }
    else if (e.key === '?' || (e.shiftKey && e.key === '/')) { toggleHelp(); e.preventDefault(); }
    else if (e.key === '/') { document.getElementById('filter-challenge')?.focus(); e.preventDefault(); }
    else if (e.key === 'Escape') { toggleHelp(false); }
  });

  const closeBtn = document.getElementById('kbd-help-close');
  if (closeBtn) closeBtn.addEventListener('click', () => toggleHelp(false));
  const helpBackdrop = document.getElementById('kbd-help');
  if (helpBackdrop) helpBackdrop.addEventListener('click', (e) => {
    if (e.target.id === 'kbd-help') toggleHelp(false);
  });
})();
