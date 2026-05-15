# Domain: accessibility

**Score agent original : 73/100 → Score recalcule : 82/100**

L'agent a applique formule WCAG luminance avec normalisation incorrecte (skip linearization gamma). Verification independante (script Python WCAG canonique) re-rapporte les ratios.

## Verification independante des contrastes

```
ratio  WCAG       paire
 4.05  AA-LARGE   text-mute #6b7d73 / bg-elev #131a16   ← FAIL body text (small mono 10.5px)
 4.40  AA-LARGE   text-mute / bg #0a100d                ← borderline
 6.61  PASS       rose #ff6b9d / bg-elev                ← agent claim 3.93 etait FAUX
 6.86  PASS       rose / bg-soft
11.04  PASS       amber / bg-elev
 7.58  PASS       cobalt / bg-elev
14.75  PASS       accent / bg
13.58  PASS       accent / bg-elev
 8.55  PASS       text-soft / bg-elev
15.23  PASS       text / bg-elev
```

## Findings RETENUS

| # | Severite | Fichier:Ligne | Description |
|---|----------|---------------|-------------|
| 1 | MOYENNE | dashboard.css:21 | `--text-mute: #6b7d73` ratio 4.05:1 sur bg-elev = sous WCAG AA body (4.5) pour text < 18px non-bold. Utilise sur kpi-label, kpi-foot, footer, lang-pill, brand subtitle, toolbar labels (~30 instances 10.5-11px). Fix : tester `#7a8a82` (devrait remonter a ~4.6:1). |
| 2 | BASSE | dashboard.css | `prefers-reduced-motion` GUARDS bien presents sur stagger, pulse, btn translateY, name-edit transitions. Verified by agent. PASS. |
| 3 | BASSE | dashboard.css:370-379 | Pills (solved/quiz/hints/flag) non-interactives (seul .pill.journal a tabindex+role). Pas de focus-visible necessaire pour les autres. Pas un bug. |
| 4 | BASSE | dashboard.css:147+ | Texte mono 10.5px (kpi-foot, footer, lang-pill) en limite lisibilite. Augmenter `line-height: 1.65` pour aerer sans casser layout. |

## Findings REJETES

- `--rose` contraste : recomputed 6.61:1 = PASS AA AAA. Agent FAUX.
- Pills.solved/quiz/hints/flag focus-visible manquant : ces pills n'ont pas tabindex, ne sont pas keyboard-focusable. Non-issue.

## Strengths

- aria-labels preserves dans tous templates (dashboard.html lines 24, 48, 139, 160, 190, 214)
- Enter/Escape sur input.name-edit
- Tous staggers/pulses guardes par `prefers-reduced-motion`
