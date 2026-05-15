# Phase 2 — HAUTE priorite

## H1 — Migrate Google Fonts @import → preconnect + <link>

**Domaine :** performance
**Effort :** 20 min (5 templates × 3 lignes head, +revert @import dashboard.css)
**Impact :** FCP -150ms a -200ms

**Steps :**
1. Dans `dashboard.css` ligne 1 : supprimer `@import url('https://fonts.googleapis.com/...')`. Garder `@import url('./dashboard-widgets.css')`.
2. Pour chaque template (`dashboard.html`, `cohorts.html`, `students.html`, `student_detail.html`, `diploma.html`, `dashboard_404.html`, `login.html`) ajouter dans `<head>` AVANT le link dashboard.css :
   ```html
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,300..600&family=Geist:wght@300..700&family=JetBrains+Mono:wght@400;500;700&display=swap">
   ```
3. Considerer creer `templates/_head_partial.html` inclus dans chaque page pour eviter duplication
4. Smoke : `flask boot + curl /login + curl /dashboard` toujours 200

## H2 — Etendre SRI a dashboard-widgets.css

**Domaine :** security_csp
**Effort :** 10 min
**Impact :** ferme un vecteur reverse proxy tampering

**Steps :**
1. Modifier `dashboard/app.py:560-572` :
   ```python
   def _compute_css_sri() -> str:
       css_path = Path(__file__).parent / "static" / "dashboard.css"
       widgets_path = Path(__file__).parent / "static" / "dashboard-widgets.css"
       try:
           combined = css_path.read_bytes() + widgets_path.read_bytes()
           digest = hashlib.sha384(combined).digest()
       except OSError:
           return ""
       return "sha384-" + base64.b64encode(digest).decode("ascii")
   ```
2. ALTERNATIVE plus simple : ajouter un second SRI hash + `<link rel="stylesheet" href="...widgets.css" integrity="...">` dans templates `<head>` (mais necessite passer `widgets_sri` dans contexte Jinja → cf. `_CSS_SRI` et `_inject_globals`)
3. Re-boot Flask : SRI recompute auto
4. pytest tests/ pour assurer regression nulle
