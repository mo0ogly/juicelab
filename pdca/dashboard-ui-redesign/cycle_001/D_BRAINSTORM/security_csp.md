# Domain: security_csp

**Score agent : 74/100 (78 apres fix SRI)**

## Findings RETENUS

| # | Severite | Fichier:Ligne | Description |
|---|----------|---------------|-------------|
| 1 | HAUTE | app.py:560-572 | `_compute_css_sri()` calcule SHA-384 sur `dashboard.css` SEULEMENT. `dashboard-widgets.css` est charge via `@import url('./dashboard-widgets.css')` depuis dashboard.css → AUCUNE protection SRI sur widgets. Si reverse proxy compromise widgets.css = tampering invisible. Fix : etendre `_compute_css_sri()` pour digest concatene des 2 fichiers, OU inliner widgets dans dashboard.css. Effort < 10 min. |
| 2 | BASSE | app.py:614-617 | CSP delta = `+style-src https://fonts.googleapis.com; +font-src https://fonts.gstatic.com`. Acceptable : Google Fonts CDN sert uniquement CSS+woff2, pas de JS. GDPR : IP leak vers Google a chaque page load — a documenter dans privacy notice institutionnelle. |
| 3 | INFO | app.py:615 | `'unsafe-inline'` style-src deja present AVANT redesign (login.html, diploma.html, cohorts.html inline `<style>` blocs preexistants). Pas une regression introduite par ce travail. |

## Findings REJETES

- "innerHTML sans echappement" sur token student dans dashboard.html : agent confond data-attribute (server-side trusted) avec content injection. Validation server-side existe (csrf token + auth). Le code utilise deja `escapeHtml()` pour le name (line 305). Non-issue.

## Strengths

- csp_nonce preserve sur tous `<script nonce="...">` dans templates modifies
- `connect-src 'self'` strict — aucun appel reseau outbound ajoute
- Pas de nouvelle surface XSS introduite

## Verification additionnelle

Le SRI gap est exploitable seulement si :
1. Attaquant a un MITM ou compromit le reverse proxy
2. Sert un dashboard-widgets.css altere

Pour un dashboard interne en VPS prof avec HTTPS, scenario faible. Mais le fix coute ~10 min et est BCP.
