# Phase 0 outreach — channels and ready-to-post text

GitHub **Discussions is not enabled** on `juice-shop/juice-shop`. The
maintainers point external feedback to two channels (verified
2026-05-11) :

| Channel | URL | Use for |
|---|---|---|
| Issue tracker | https://github.com/juice-shop/juice-shop/issues/new/choose | Feature request via the official `[🚀]` template |
| Gitter chat | https://gitter.im/bkimminich/juice-shop | Conversational support / live ping a maintainer |

**Recommended primary** : open a Feature request Issue (traceable,
referenceable from a future PR). **Optional secondary** : ping
@bkimminich on Gitter pointing at the Issue.

---

## Pre-flight checklist before posting

- [ ] Search open AND closed Issues for "pedagogy", "overlay", "lab",
      "training", "academic" — make sure no prior request covers this.
- [ ] Verify `mo0ogly/juice-shop` is public on GitHub.
- [ ] Verify `PEDAGOGY_COMPANION.md` is on `master` of the fork.
- [ ] Replace `<DASHBOARD_REPO_URL>` below with the actual companion
      dashboard repo URL.
- [ ] Use your personal GitHub account (not anonymous).

---

## Feature request — ready-to-paste

Pick the **"🚀 Feature request"** template at
https://github.com/juice-shop/juice-shop/issues/new/choose .

### Title

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

## Optional Gitter follow-up (after the Issue is filed)

Once the Issue has an URL, you can ping the maintainer chat with :

```
Hi all, just opened a non-invasive Pedagogy Companion proposal as a
Feature request : <ISSUE_URL>. Would love a temperature check from
a maintainer before I prepare any code PR. Happy to discuss either
here or on the Issue.
```

Keep it short ; maintainers triage Gitter conversationally.

---

## Why we did NOT open a PR yet

This is a temperature check, NOT a PR. Per the deferred rebrand plan
in `docs/REBRAND_PLAN.md`, we wait for a maintainer signal before
investing the 2-3 days needed to strip the internal "JuiceLab" name
from 140+ i18n keys, 12 components, 7 services, 4 path roots, 3
localStorage keys, the dashboard, and the documentation. If the
maintainers prefer the external repo path, the rebrand stays
unnecessary.
