# Domain: markup_consistency

**Score agent : 94/100**

## Findings RETENUS

| # | Severite | Fichier:Ligne | Description |
|---|----------|---------------|-------------|
| 1 | INFO | diploma.html:149 | Selecteur CSS print `header.app-header { display: none }` dans `@media print` cible une classe morte (diploma.html n'a pas de header.app-header). Inoffensif. Cleaner pour cycle 2. |
| 2 | BASSE | dashboard-widgets.css:22 (`.hidden`) | Utilisee dans dashboard.html ligne 119 : `<div class="scroll {% if not summary.students %}hidden{% endif %}">`. **N'EST PAS orpheline.** Agent FAUX. |
| 3 | BASSE | dashboard-widgets.css:19 (`.text-mono`) | Verifier usage : `grep -r 'text-mono' templates/ static/` → si 0 = orphan, supprimer. |
| 4 | BASSE | dashboard-widgets.css:13 (`.w-30p`) | Verifier usage. Si 0 = supprimer ou documenter pour usage futur. |

## Findings REJETES (faux positifs)

- `.hidden` declaree orpheline par agent : utilisee dashboard.html line 119. PASS.

## Migration app-header → topbar : 100% complete

Verification independante :

```bash
grep -rn 'app-header\|brand-icon' templates/ static/ 2>/dev/null
# templates/diploma.html:149: header.app-header { display: none } (dead selector @media print)
# Aucun autre usage.
```

Tous templates HTML touchent maintenant `class="topbar"` + `class="brand-mark"`. Migration markup propre.

## Inline `style="..."` audit

L'agent a identifie 14 inline styles. Triage :
- 4 dynamiques (width/height calcules en JS) → garder
- 10 statiques (margin, font-size, cursor) → migrables vers classes, mais CSP `'unsafe-inline'` autorise. Non bloquant.

## Strengths

- API classes preserve : kpi, pill, sticky-col, score-col, name-edit, lang-pill, btn, logout, scroll, modal-backdrop, etc. — 100% coverage entre CSS et templates utilises
- Aucune classe silently broken (utilisee sans CSS)
