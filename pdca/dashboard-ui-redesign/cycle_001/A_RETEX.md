# A — RETEX Cycle 001

## Ce qui a bien marche

1. **Decomposition CSS en 2 modules** (dashboard.css + dashboard-widgets.css via @import) a permis de tenir la regle 800 lignes/fichier sans sacrifice de couverture.
2. **Preservation 100% de l'API classes** : aucune classe utilisee dans les templates n'est silently broken. Migration markup (`app-header → topbar`, `brand-icon → brand-mark`) coherente.
3. **CSP delta minimal et defensible** : 2 hosts read-only ajoutes (fonts.googleapis.com + fonts.gstatic.com), zero impact sur connect/script.
4. **Pretest harness pytest** : 199/199 survit a tout le redesign — preuve que la couche CSS n'a pas casse de markup test-able.
5. **Triage critique des findings agent** : verification independante des contrastes WCAG a invalide 1 faux positif majeur (rose 3.93 → 6.61) et raccroche les vrais issues.

## Ce qui a moins bien marche

1. **Browser visual recette skipped** : pas de smoke screenshot pour valider rendering effectif. C'est un gap recurrent en session CLI. Cycle 2 doit l'aborder via playwright/puppeteer headless.
2. **Agents brainstorm scope drift** : 2 agents sur 6 ont audite l'etat global au lieu du delta (i18n_agent surtout). Le prompt doit etre plus explicite sur "DELTA introduit par ce cycle vs etat global pre-existant".
3. **Agents brainstorm faux positifs** : 4 findings rejected/false-positive sur ~25 total = 16% noise. Acceptable mais a surveiller. Causes :
   - Formule WCAG mal appliquee (luminance sans linearization gamma)
   - Confusion text contrast vs font-size
   - Classe `.hidden` declaree orpheline alors qu'elle est utilisee
   - Pills.solved/quiz focus-visible reclame sur element non-interactif
4. **Performance score 65/100** : @import render-blocking + missing preconnect = 2 quick wins evidents non identifies avant audit. A faire en remediation prioritaire.
5. **SRI ne couvre pas widgets.css** : oversight design dans la decomposition CSS. Aurait du etre prevu.

## Surprises

- Agent design_quality a trouve plus de strengths que de findings (cohorte motion + palette semantique) — confirmation que le redesign n'est pas "AI slop" generique.
- Le finding "progress-bar q1/q4 dissonance" est genuinement debattable et merite arbitrage produit, pas auto-fix.

## Cause profonde des findings HAUTE

- **@import render-blocking** : choix initial pour minimiser edits templates (1 file change vs 6). Tradeoff perf vs scope. Cycle 2 reverse cette decision.
- **SRI gap widgets** : oversight quand j'ai splitte le CSS pour respecter regle 800 lignes. Aurait du etendre `_compute_css_sri` en meme temps.

## Apprentissages pour cycle 2

- Toujours ajouter preconnect Google Fonts si on autorise leur CDN
- Si on splitte un CSS protege par SRI, etendre la fonction SRI en meme temps
- Verifier independamment les contrastes WCAG avant accepter findings agent
- Prompts agents doivent inclure scope explicite "delta vs pre-existant"
