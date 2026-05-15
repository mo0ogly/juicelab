# Phase 3 — MOYENNE priorite

## M1 — `--text-mute` contraste AA fix

**Effort :** 15 min (1 token + tests visual)
**Impact :** WCAG AA body text compliance pour ~30 instances (kpi-foot, footer, lang-pill, brand subtitle, toolbar labels)

```css
/* dashboard.css ligne 21 */
--text-mute: #7a8a82;  /* etait #6b7d73, ratio 4.05 → ~4.7:1 */
```

Light mode override aussi (`#6b7569` ratio TBD) : tester independant.

## M2 — Subset Fraunces (KB gain ~30 KB)

**Effort :** 5 min
**Impact :** font payload -50%

Modifier `@import` (apres migration H1, dans le `<link>` head) :

```
family=Fraunces:ital,wght@1,500&family=Geist:wght@400;500;600&family=JetBrains+Mono:wght@500;700
```

Plus de variable opsz axis (lourd). Verifier rendering h1 brand + diploma-title + section-title encore satisfaisant (perte de subtilite italic optical-size, mais 95% des usages OK a 500).

## M3 — body::before repaint optim

**Effort :** 5 min
**Impact :** ~12ms/scroll mobile low-end

```css
body::before {
  /* ... */
  will-change: transform;
  transform: translateZ(0);  /* force GPU layer */
}
```

Ou simplifier a 1 radial-gradient si visual loss acceptable.

## M4 — Progress-bar q1/q4 semantique : trancher avec produit

**Effort :** 5 min (decision) + 3 min CSS (si inversion)
**Impact :** coherence semantique vs convention red=low

Options :
- (A) Garder rose=q1, menthe=q4 — convention "red bad, green good" intuitif
- (B) Inverser : cobalt=q1, menthe=q4 — eviter dissonance avec rose=live/flag partout ailleurs

Recommandation : (A) garder convention, MAIS documenter dans CLAUDE.md la semantique rose pour eviter confusion future.

## M5 — Suppression orphan CSS

**Effort :** 2 min
**Impact :** -3 lignes dead code

```bash
# dashboard-widgets.css :
# Supprimer .text-mono (line 19) et .w-30p (line 13)
# Garder .hidden (utilisee dashboard.html:119)
# Garder .w-10, .w-24p, .w-25p, .w-90, .w-120, .mt-8 (a verifier usage)
```
