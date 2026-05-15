# Domain: i18n_coherence

**Score agent : 58/100**
**Score apres triage scope-correct : 92/100**

## Triage critique : pre-existant vs introduit par ce travail

L'agent a audite l'ETAT GLOBAL du dashboard, pas le DELTA introduit par le redesign. La plupart des violations existaient AVANT.

### Verification git diff

```bash
# pills hardcodes dans dashboard.html lignes 156-166 et JS 252-262 :
# → presents AVANT ce travail (non touche par le redesign)

# placeholder "m2-ia-2026" cohorts.html ligne 117 :
# → present AVANT (non touche)

# "FLAG"/"cost" student_detail.html lignes 89, 105 :
# → presents AVANT (non touche, seul header app-header→topbar change)
```

## Findings RETENUS (introduits par ce travail)

| # | Severite | Fichier:Ligne | Description | Status |
|---|----------|---------------|-------------|--------|
| 1 | INFO | login.html:111 | Ajout `<p class="login-mark">JuiceLab dashboard</p>` hardcode. Conforme exception CLAUDE.md (brand mark = dashboard.html line 20 deja). | PASS (exception explicite) |
| 2 | INFO | login.html:43 (CSS) | `.login-mark::before { content: "//" }` decoratif symbol. PASS. | PASS |

## Findings reportes au backlog produit (pre-existant)

Ces violations existaient AVANT le redesign. A traiter dans un cycle dedie i18n :

- dashboard.html pills `solved/hints/journal/quiz/flag` hardcodes (JS inline). Generer cles `PILL_*_INLINE`.
- cohorts.html ligne 117 placeholder `"m2-ia-2026 (alnum + - _ .)"`. Generer cle `COHORTS_FILTER_EXAMPLE`.
- student_detail.html `"FLAG"` / `"cost"` dans JS template. Generer cles.

## Strengths

- Tous `{{ t() }}` Jinja preserves dans les sections modifiees
- `{{ t('DIPLOMA_MENTION_' + mention.upper()) }}` intact (diploma.html)
- aria-labels via `{{ t('ARIA_*') }}` preserves partout
- Pas de nouvelle string UI hardcodee introduite par ce travail (sauf brand mark conforme exception)
