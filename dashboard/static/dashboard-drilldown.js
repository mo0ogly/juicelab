// Phase 3 Task 4 — drill-down modal for student detail (iframe loaded).
(function () {
  function open(href) {
    const bd = document.getElementById('drilldown-backdrop');
    const iframe = document.getElementById('drilldown-iframe');
    if (!bd || !iframe) return;
    iframe.src = href;
    bd.classList.add('open');
  }
  function close() {
    const bd = document.getElementById('drilldown-backdrop');
    const iframe = document.getElementById('drilldown-iframe');
    if (!bd || !iframe) return;
    bd.classList.remove('open');
    iframe.src = '';
  }
  function bind() {
    document.querySelectorAll('a[data-drilldown="1"]').forEach(a => {
      if (a.dataset.boundDrill) return;
      a.dataset.boundDrill = '1';
      a.addEventListener('click', (e) => { e.preventDefault(); open(a.href); });
    });
  }
  // Initial + on subsequent DOM updates (matrix re-render via SSE)
  bind();
  const observer = new MutationObserver(bind);
  const tbody = document.getElementById('body-rows');
  if (tbody) observer.observe(tbody, { childList: true, subtree: false });

  const closeBtn = document.getElementById('drilldown-close-btn');
  if (closeBtn) closeBtn.addEventListener('click', close);
  const bd = document.getElementById('drilldown-backdrop');
  if (bd) bd.addEventListener('click', (e) => { if (e.target.id === 'drilldown-backdrop') close(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
})();
