# Phase 0 - diffusion — canaux et textes prêts à publier

> Version anglaise : [PEDAGOGY_COMPANION_PHASE0_OUTREACH.md](./PEDAGOGY_COMPANION_PHASE0_OUTREACH.md).

Les **Discussions GitHub ne sont pas activées** sur `juice-shop/juice-shop`. Les
mainteneurs redirigent les retours externes vers deux canaux (vérifié
le 2026-05-11) :

| Canal | URL | Utilisation |
|---|---|---|
| Gestionnaire d'issues | https://github.com/juice-shop/juice-shop/issues/new/choose | Demande de fonctionnalité via le modèle officiel `[🚀]` |
| Chat Gitter | https://gitter.im/bkimminich/juice-shop | Support conversationnel / ping direct à un mainteneur |

**Priorité recommandée** : ouvrir une issue de demande de fonctionnalité (traçable,
référençable depuis une future PR). **Option secondaire** : pinger
@bkimminich sur Gitter en pointant vers l'issue.

---

## Liste de vérification avant publication

- [ ] Rechercher dans les issues ouvertes ET fermées les termes « pedagogy », « overlay », « lab »,
      « training », « academic » — s'assurer qu'aucune demande antérieure ne couvre ce sujet.
- [ ] Vérifier que `mo0ogly/juice-shop` est public sur GitHub.
- [ ] Vérifier que `PEDAGOGY_COMPANION.md` est sur `master` du fork.
- [ ] Remplacer `<DASHBOARD_REPO_URL>` ci-dessous par l'URL réelle du dépôt du tableau de bord compagnon.
- [ ] Utiliser votre compte GitHub personnel (pas anonyme).

---

## Demande de fonctionnalité — texte prêt à coller

Choisir le modèle **"🚀 Feature request"** sur
https://github.com/juice-shop/juice-shop/issues/new/choose .

### Titre

```
[🚀] Pedagogy Companion overlay — non-invasive academic lab on top of Juice Shop
```

### Description

```
I have been maintaining a pedagogical fork of Juice Shop at
mo0ogly/juice-shop for academic security labs (currently used in an
M2 university module). It adds a thin overlay on top of the
unmodified upstream codebase. I would like to ask whether the
maintainers would consider upstreaming parts of it as an opt-in
plugin / extension, or whether it should stay external.

Scope summary :

- Briefing per challenge : OWASP-sourced mission + 3-4 concepts
  (CWE / Top 10 anchored), trilingual FR / EN / BR.
- Graduated hints : 5 levels with fixed cost cohort 5 / 10 / 20 / 35 / 50.
- Reflective journal : before / after free text + HMAC-signed PDF proof.
- Quiz : 3 questions per challenge, 4 options each, deterministic scoring.
- Cohort workflow : a teacher creates a cohort on the companion dashboard,
  a student joins from the overlay with a cohort code, the teacher
  approves the request, events stream live to the dashboard.

Coverage : 110 of the 111 native challenges have full pack triplets
today. The remaining one is csrfChallenge (deprecated upstream).

Non-invasive guarantees :

- Zero native route, dataset, lib, or challenge file modified.
- Zero vulnerability removed. The CTF surface is preserved exactly
  as upstream delivers it.
- All overlay code lives under frontend/src/app/juicelab-overlay/.
- The companion dashboard runs on a separate Flask process and is
  opt-in : Juice Shop functions normally without it.
```

### Solution ideas

```
Two paths I can see :

(1) Plugin / opt-in extension upstream. Merge a documented YAML
    schema (juicelab.briefing.v2, juicelab.hints.v2, juicelab.quiz.v2)
    and a loader hook gated on a config flag. The pedagogical content
    itself stays in this fork or in a separate
    `juice-shop-pedagogy-companion` repo so it does not bloat the
    upstream binary.

(2) External companion repo. I keep the fork standalone and publish
    a `juice-shop-pedagogy-companion` package that teachers install
    alongside Juice Shop. Zero upstream change required.

I am happy to take whichever direction the maintainers prefer.
If interest exists for (1), I will open a small first PR introducing
only the YAML schema documentation and the opt-in loader hook
(no UI, no content), so the change set is reviewable.

All commits will be DCO-signed (git commit -s) on a branch off
develop. AI assistance disclosed : Claude was used for the overlay
and pedagogical content drafts ; everything is human-reviewed and
validated before commit.
```

### Possible alternatives

```
- Keep the fork standalone forever (status quo) — works for our M2
  module but loses the discoverability benefit of being indexed by
  the upstream README.
- Publish only a documented YAML schema (no code change upstream) and
  invite other educators to fork. Lower friction, lower visibility.
- Wait for the OWASP plugin / extension ecosystem (if any) to mature.
```

### Links

```
- Fork : https://github.com/mo0ogly/juice-shop
- Fork landing notes : https://github.com/mo0ogly/juice-shop/blob/master/PEDAGOGY_COMPANION.md
- Companion dashboard repo : <DASHBOARD_REPO_URL>
```

---

## Suivi Gitter optionnel (après le dépôt de l'issue)

Une fois que l'issue dispose d'une URL, il est possible de pinger le chat des mainteneurs avec :

```
Hi all, just opened a non-invasive Pedagogy Companion proposal as a
Feature request : <ISSUE_URL>. Would love a temperature check from
a maintainer before I prepare any code PR. Happy to discuss either
here or on the Issue.
```

Rester concis ; les mainteneurs traitent Gitter de façon conversationnelle.

---

## Pourquoi nous n'avons pas encore ouvert de PR

Il s'agit d'une prise de température, PAS d'une PR. Conformément au plan de
rebranding différé dans `docs/REBRAND_PLAN.md`, nous attendons un signal des
mainteneurs avant d'investir les 2 à 3 jours nécessaires pour supprimer le nom
interne « JuiceLab » dans 140+ clés i18n, 12 composants, 7 services, 4 racines
de chemin, 3 clés localStorage, le tableau de bord et la documentation. Si les
mainteneurs préfèrent la voie du dépôt externe, le rebranding reste superflu.
