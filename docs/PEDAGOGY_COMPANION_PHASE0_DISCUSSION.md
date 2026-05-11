# Phase 0 Discussion — text ready to post on the OWASP Juice Shop upstream

**Target** : https://github.com/juice-shop/juice-shop/discussions

**Category** : `Ideas` or `Show and tell` (pick whichever the maintainers
prefer for proposals).

**Title** : `Pedagogy Companion overlay — non-invasive academic lab on top of Juice Shop (interest in upstreaming?)`

**Body** (paste the block below verbatim) :

---

Hi OWASP Juice Shop team,

I have been maintaining a pedagogical fork of Juice Shop at
`mo0ogly/juice-shop` for academic security labs (currently used in an
M2 module). It adds a thin overlay on top of the unmodified upstream
codebase. I wanted to ask whether you would be open to upstreaming
parts of it as a plugin / opt-in extension, or whether you would
rather it stay external.

## Scope summary

| Area | What | Where |
|---|---|---|
| Briefing per challenge | OWASP-sourced mission + 3-4 concepts (CWE / Top 10 anchored) | `frontend/src/assets/juicelab/briefing/<key>.yaml` |
| Graduated hints | 5 levels, fixed cost cohort 5 / 10 / 20 / 35 / 50 | `data/juicelab-private/hints/<key>.yaml` |
| Reflective journal | before / after free text, HMAC-signed PDF proof | overlay + Flask dashboard |
| Quiz | 3 questions, 4 options, deterministic scoring | `data/juicelab-private/quiz/<key>.yaml` |
| Cohort workflow | teacher creates cohort, student joins, teacher approves | Flask companion dashboard (separate repo) |
| i18n | FR / EN / BR maintained in parallel | `frontend/src/assets/i18n/` |

## Non-invasive guarantees

- **Zero** native OWASP route, dataset, lib, or challenge file is
  modified. All overlay code lives in
  `frontend/src/app/juicelab-overlay/`.
- **Zero** vulnerability is removed. The CTF surface remains exactly
  as upstream delivers it.
- The companion dashboard is a separate Flask process. Juice Shop runs
  normally without it ; the overlay falls back to a local-only mode.

## Coverage

110 of 111 native challenges currently have full pack triplets
(briefing + hints + quiz). The remaining one is `csrfChallenge` which
is marked deprecated upstream and intentionally left out.

## Question to the maintainers

Two paths I can see :

1. **Plugin / opt-in extension upstream** : merge a documented YAML
   schema (`juicelab.briefing.v2`, `juicelab.hints.v2`,
   `juicelab.quiz.v2`) and a loader hook gated on a config flag. The
   actual pedagogical content stays in this fork or in a separate
   `owasp-juice-shop-pedagogy-companion` repo so it does not bloat
   the upstream binary.
2. **External companion repo** : I keep the fork standalone and
   publish a `juice-shop-pedagogy-companion` package that teachers
   install alongside Juice Shop. No code change upstream.

Path 1 would let other contributors build pedagogical packs (other
universities, training providers) without forking. Path 2 keeps the
maintenance burden out of the OWASP repo entirely.

I am happy to take whichever direction you prefer. If there is
interest, I will open a small first PR introducing only the YAML
schema documentation and the opt-in loader hook (no UI, no content),
so the change set is reviewable.

## Provenance and DCO

All commits will be signed off, on a branch off `develop`. I will
clearly disclose AI assistance (Claude was used for the overlay and
pedagogical content drafts ; everything is reviewed and validated by
me before commit).

## Repo links

- Fork : https://github.com/mo0ogly/juice-shop
- Fork landing notes : `PEDAGOGY_COMPANION.md` on the fork root
- Companion dashboard : (link to dashboard repo)

Thank you for the work behind Juice Shop. Even the answer "please keep
it external" is useful to me — it lets me document the integration
path cleanly on the fork side.

---

## Notes for me before posting

- [ ] Cross-check the URL of the companion dashboard repo before
      pasting.
- [ ] Make sure `mo0ogly/juice-shop` is public.
- [ ] Make sure `PEDAGOGY_COMPANION.md` is on `master` of the fork.
- [ ] Use a personal account (not anonymous) so maintainers can
      identify me.
- [ ] Do NOT open a PR yet. This is a sondage / temperature check
      only. Wait for a maintainer reply before any code PR.
