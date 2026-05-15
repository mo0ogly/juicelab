# Phase 4 — BASSE priorite

## L1 — Selecteur print mort diploma.html

```css
/* diploma.html ligne 149, dans @media print */
- .diploma-actions, header.app-header, footer.footer { display: none !important; }
+ .diploma-actions, .footer { display: none !important; }
```

## L2 — KPI hover glow softer

```css
/* dashboard.css ligne 208 */
- .kpi:hover::before { opacity: 1; box-shadow: 0 0 12px var(--accent); }
+ .kpi:hover::before { opacity: 1; box-shadow: 0 0 8px var(--accent-glow); }
```

## L3 — Mono small text line-height

```css
/* dashboard.css : kpi-foot, footer, lang-pill, toolbar label */
line-height: 1.65;  /* etait herite 1.55 */
```

## L4 — Browser visual recette (cycle 2 priority)

Lancer Flask en dev + playwright/puppeteer headless pour capturer screenshots :
- /login (Fraunces 34px italic + rail + grid backdrop)
- /dashboard?cohort=demo (KPI stagger anim, hero rail, table hover)
- /admin/cohorts (toolbar select, pending-block Fraunces)
- /admin/students?cohort=demo
- /admin/diploma/<token>?cohort=demo (print preview + screen render)
- light mode toggle via DevTools emulate
