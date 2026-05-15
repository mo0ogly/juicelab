# PDCA Cycle 001 — Dashboard UI Redesign

**Perimetre :** dashboard/ (Flask + Jinja, JuiceLab cohort dashboard)
**Date :** 2026-05-15
**Objectif :** baseline audit du redesign cyber-pedagogique sombre raffine livre ce tour.

## Pre-flight (P.0) — GREEN

- Flask `create_app()` boot OK (35 routes registered)
- `/static/dashboard.css` HTTP 200 (22833 bytes)
- `/static/dashboard-widgets.css` HTTP 200 (6943 bytes)
- `/login` HTTP 200
- CSP header contient `fonts.googleapis.com` + `fonts.gstatic.com`
- `pytest tests/` : 199/199 passed

Aucun blocker. On lance l'audit.

## Scoring domains (cycle 1 baseline)

| Domaine | Poids | Checks principaux |
|---------|-------|-------------------|
| design_quality | 20 | typographie distinctive, palette coherente, atmosphere, motion intentionnel, hero rail, KPI bento |
| accessibility | 18 | contraste WCAG AA, focus-visible, aria-labels, prefers-reduced-motion, keyboard nav |
| performance | 12 | weight CSS, font-display swap, blocking @import, CLS, animation perf |
| security_csp | 15 | CSP relax minimal, SRI integrity, font-src whitelist, no XSS surface, integrity recompute boot |
| i18n_coherence | 10 | aucune string hardcodee ajoutee, brand mark exception OK |
| file_size_hygiene | 5 | 800 lignes max, decomposition modules |
| test_coverage | 10 | pytest survit, smoke routes, regression markup |
| markup_consistency | 10 | dead classes purgees (app-header/brand-icon), classes API preserved |

Total : 100

## Prompts d'audit (par domaine)

### Prompt 1 — design_quality
Audit le redesign visuel de dashboard.css (516 lignes), dashboard-widgets.css (242), et templates login/diploma. Verifie :
- Coherence typographique (Fraunces italic display + Geist body + JBM mono)
- Palette : charbon `#0a100d`, menthe `#7df9b8`, rose `#ff6b9d`, ambre `#f7c560`, cobalt `#82a8ff` — assignation semantique coherente ?
- Atmosphere : radial gradients fixed, hero rail 2px multicolore, KPI gradients
- Motion : stagger fade-up KPI 40-280ms, pulse auto-tag, hover row inset 3px, btn translateY(-1px). Intentionnel ou disperse ?
- Bento layout pour KPI ?
- Generic-AI-slop check : pas de purple-on-white, pas de Inter, pas de generic system stack
- Score /100 + 3-5 findings concrets avec ligne CSS

### Prompt 2 — accessibility
Audit a11y du dashboard restyle. Verifie :
- Contraste WCAG AA : text/text-soft/text-mute sur bg-elev. JBM body 13px lisible ?
- focus-visible sur tous interactifs (btn, logout, .pill.journal, lang-pill, modal-close)
- prefers-reduced-motion : guard autour staggers, pulses, transitions ?
- aria-labels preserves dans templates (topbar, nav-actions, kpis) ?
- Color independence : reposer uniquement sur couleur pour solved/hints/quiz/flag/journal ?
- Score /100 + risques bloquants

### Prompt 3 — performance
Audit perf CSS + fonts :
- `@import` Google Fonts en top de CSS = render-blocking. Impact ?
- font-display: swap present
- 4 weights Fraunces italic 9..144 + 4 Geist + 3 JBM = combien KB downloaded ?
- Animation cost : 4x stagger fade-up keyframes simultanes, body::before fixed radial, transitions ubiquite
- Backdrop-filter blur(6px) sur modal-backdrop — perf hit on low-end ?
- 22833 bytes core CSS sans compression brotli — acceptable ?
- Score /100

### Prompt 4 — security_csp
Audit CSP relax + SRI. Verifie :
- `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com` — risque ?
- SRI hash dashboard.css recompute au boot (`_compute_css_sri`) — couvre-t-il dashboard-widgets.css ? NON. Risque cross-origin tampering ?
- `'unsafe-inline'` style-src deja present avant le patch — pas une regression
- XSS surface introduit ? Google Fonts CDN sert CSS+woff2 only, pas de JS
- font-src vide pour dashboard-widgets.css (woff2 chargees via @import dans CSS importee = OK)
- Score /100 + recommandations

### Prompt 5 — i18n_coherence
Audit i18n. Verifie :
- Aucune string UI visible hardcodee dans templates modifies (login.html, diploma.html, dashboard_404.html, student_detail.html, cohorts.html)
- `<p class="login-mark">JuiceLab dashboard</p>` = brand, deja hardcode dans dashboard.html ligne 20 = consistant
- Hint cost cohorte 5/10/20/35/50 non touche (data, pas UI)
- t('KEY') preserves partout
- Score /100

### Prompt 6 — markup_consistency
Audit markup + dead classes :
- Anciennes classes `app-header` + `brand-icon` (dashboard_404 + student_detail) → migrees vers `topbar` + `brand-mark`
- Reste-t-il du dead CSS (selecteurs vises sur classes plus utilisees) ?
- diploma.html print rule `header.app-header { display: none }` = dead selecteur, inoffensif. Cleaner ?
- Classes API preserve : kpi, kpi-value, pill.solved, pill.hints, sticky-col, score-col, name-edit, etc. — verifier 100% coverage entre CSS et templates
- Score /100
