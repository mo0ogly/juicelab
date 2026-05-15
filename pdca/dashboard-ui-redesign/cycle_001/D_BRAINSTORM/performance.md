# Domain: performance

**Score agent : 62/100**

## Findings RETENUS

| # | Severite | Fichier:Ligne | Description |
|---|----------|---------------|-------------|
| 1 | HAUTE | dashboard.css:1-2 | `@import url('https://fonts.googleapis.com/...')` puis `@import url('./dashboard-widgets.css')` au top du CSS = cascade render-blocking. dashboard-widgets attend la resolution Google Fonts avant download. Fix : remplacer par 2 `<link rel="stylesheet">` dans `<head>` de chaque template (ou ajouter preconnect + link Google Fonts en head et garder widgets @import). |
| 2 | HAUTE | templates/*.html `<head>` | Aucun `<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>` ni `<link rel="dns-prefetch" href="https://fonts.googleapis.com">`. ~100-150ms latency tax DNS+TCP. Ajout 2 lignes par template (ou 1 si on cree un partial `_head.html` inclus partout). |
| 3 | MOYENNE | dashboard.css:1 | Fraunces variable opsz 9..144 italic + wght 400..700 = ~50KB woff2. Subset agressif : `family=Fraunces:ital,wght@1,500` (italic 500 seul) couvrirait 95% des usages (h1, section-title, modal-head, student-display, diploma-title, login h1). Gain ~30 KB. |
| 4 | MOYENNE | dashboard.css:101-108 | `body::before` position fixed + 2 radial-gradients = repaint au scroll. Pas critique sur desktop (compositor handle), mais sur mobile low-end ~12ms/scroll. Ajouter `will-change: transform` ou simplifier a 1 radial. |
| 5 | BASSE | dashboard.css:228-233 | Stagger KPI x4 + pulseDot infinite simultanes au load = ~8-12ms paint window. Acceptable. |
| 6 | BASSE | dashboard.css:447 | `backdrop-filter: blur(6px)` modal-backdrop. Display:none par defaut = no initial cost. PASS. |

## CSS bytes
- core 22833 + widgets 6943 = 29.7 KB non-compresse
- gzip ~8.5 KB = acceptable
- Bytes fonts woff2 dominent (~50-60 KB net, ~18 KB gzip)
