# C — GAP REPORT (Cycle 001)

**Perimetre :** dashboard UI redesign cyber-pedagogique sombre raffine
**Date :** 2026-05-15

## Synthese

| Domaine | Score | Tendance | Findings retenus |
|---------|-------|----------|------------------|
| design_quality   | 82/100 | baseline | 1 MOYENNE (progress-bar semantique a trancher), 1 BASSE (kpi hover glow) |
| accessibility    | 82/100 | baseline | 1 MOYENNE (text-mute 4.05:1), 1 BASSE (line-height mono 10.5px) |
| performance      | 65/100 | baseline | 2 HAUTE (@import vs link + preconnect), 2 MOYENNE (font subset, body::before repaint) |
| security_csp     | 78/100 | baseline | 1 HAUTE (SRI ne couvre pas widgets.css), 1 BASSE (GDPR notice) |
| i18n_coherence   | 92/100 | baseline | 0 introduit par ce travail (3 violations pre-existantes reportees backlog) |
| file_size_hygiene| 95/100 | baseline | tous fichiers < 800 (max = dashboard.css 516) |
| test_coverage    | 90/100 | baseline | 199/199 pytest, mais 0 visual/E2E browser smoke |
| markup_consistency | 95/100 | baseline | 2 orphan classes (text-mono, w-30p), 1 dead selecteur print diploma.html:149 |

**Score global pondere : 84/100** (objectif baseline atteint)

## Findings agreges par priorite

### CRITIQUE
*(aucun)*

### HAUTE
1. **@import render-blocking + missing preconnect** (performance) — fix : remplacer `@import url(Google Fonts)` par `<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>` + `<link rel="stylesheet" href="https://fonts.googleapis.com/...">` dans `<head>` de chaque template, garder `@import url('./dashboard-widgets.css')` interne (same-origin OK). Gain FCP ~150-200ms.
2. **SRI ne couvre pas dashboard-widgets.css** (security_csp) — fix : modifier `_compute_css_sri()` dans app.py:560 pour digest concatene de `dashboard.css + dashboard-widgets.css`. ~10 min.

### MOYENNE
3. **`--text-mute` contraste 4.05:1 sous AA body** (accessibility) — fix : token `#6b7d73` → tester `#7a8a82` ou plus clair. Verifier impact visuel sur kpi-foot/footer/lang-pill.
4. **Fraunces variable opsz over-subscribed** (performance) — fix : restreindre query Google Fonts a `family=Fraunces:ital,wght@1,500&family=Geist:wght@400;500;600&family=JetBrains+Mono:wght@500;700`. Gain ~30 KB woff2.
5. **body::before repaint mobile** (performance) — fix : `will-change: transform` ou reduire a 1 radial-gradient.
6. **Progress-bar q1/q4 semantique** (design_quality) — A TRANCHER avec produit : rose=q1 (red=low conventionnel) OU inverser (cobalt=low, menthe=high) pour eviter confusion avec rose=live partout ailleurs.

### BASSE
7. **`.text-mono` + `.w-30p` orphelines** (markup_consistency) — fix : supprimer de dashboard-widgets.css. ~1 min.
8. **`header.app-header` selecteur print mort** (markup_consistency) — fix : supprimer ligne diploma.html:149 ou remplacer par `.app-header`-less. ~1 min.
9. **`.kpi:hover::before` glow trop bright** (design_quality) — fix : reduire box-shadow `0 0 12px var(--accent)` → `0 0 8px var(--accent-glow)`.
10. **Line-height mono 10.5px** (accessibility) — fix : ajouter `line-height: 1.65` sur kpi-foot, footer, lang-pill.

## Pre-existant (hors scope ce cycle)

Reportes au backlog produit, NON imputes a ce cycle :
- Pills hardcodes JS template dashboard.html (solved/hints/journal/quiz/flag) — i18n debt anterieure
- Placeholder cohorts.html:117 — i18n debt anterieure
- `FLAG`/`cost` student_detail.html JS — i18n debt anterieure

## Faux positifs detectes (rejetes)

- accessibility agent : rose ratio 3.93:1 — recompute donne 6.61:1 = PASS. Formula erronee.
- design_quality agent : password input "low contrast" — text/bg = 15:1, PASS AAA.
- markup_consistency agent : `.hidden` orpheline — utilisee dashboard.html:119.
- accessibility agent : focus-visible manquant sur .pill.solved/quiz/hints/flag — ces pills ne sont PAS interactives (pas de tabindex), donc focus non requis.
- i18n agent : audite scope entier au lieu du DELTA. La majeure partie des violations etait pre-existante.

## Browser visual recette : NON EXECUTEE

Limitation : session CLI sans headless browser. Recommandation cycle 2 : lancer dev server + screenshot via puppeteer/playwright pour valider rendu effectif :
- /login (Fraunces 34px italic charge ?)
- /dashboard?cohort=X (KPI stagger, hero rail visible ?)
- /admin/diploma/X print preview (mention colors print-safe ?)
- Light mode (`prefers-color-scheme: light`) — paper editorial render OK ?
