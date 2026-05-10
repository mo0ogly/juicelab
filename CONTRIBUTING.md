# Contributing to JuiceLab

Thanks for considering a contribution. JuiceLab is an OWASP Juice Shop pedagogical companion ; the most useful contributions are :

1. **New pedagogical packs** for Juice Shop challenges not yet covered by the parcours (98 of the 111 native challenges still lack a JuiceLab pack — see [`.claude/rules/owasp-pedagogy-companion.md`](./.claude/rules/owasp-pedagogy-companion.md)).
2. **Translations** of the overlay UI, briefings, hints, and quizzes into more languages (current : FR, EN ; next : BR).
3. **Bug fixes** in the overlay, dashboard, or docker scripts.
4. **Documentation** improvements, especially in [`INSTALL.md`](./INSTALL.md) and [`docs/`](./docs/).

This document covers what we expect from contributors, how to set up a dev environment, and the pedagogical content rules that gate every PR.

## Table of contents

- [Code of conduct](#code-of-conduct)
- [Two hard rules](#two-hard-rules)
- [Dev environment](#dev-environment)
- [Adding a new pedagogical pack](#adding-a-new-pedagogical-pack)
- [Editing the overlay UI](#editing-the-overlay-ui)
- [Editing the dashboard](#editing-the-dashboard)
- [Pull request checklist](#pull-request-checklist)
- [Reporting a security issue](#reporting-a-security-issue)

---

## Code of conduct

Read [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md). It is the Contributor Covenant 2.1. The classroom audience is heterogeneous beginner students ; the project keeps the same bar for its contributors.

---

## Two hard rules

### Rule 1 — No new Juice Shop challenge

We never add a new entry to `juice-shop/data/static/challenges.yml`. That file is upstream OWASP Juice Shop territory. If you want a new challenge, contribute it to the [Juice Shop project](https://github.com/juice-shop/juice-shop) directly. JuiceLab only builds *on top of* what Juice Shop already ships.

If your contribution requires a new challenge that does not exist in upstream, the PR is rejected. The reviewer will suggest the closest existing key from `selected_challenges.yml` instead.

### Rule 2 — Sources before content

For any new pack (briefing, hints, quiz, journal, walkthrough), you must :

1. **Read** the upstream description in `juice-shop/data/static/challenges.yml`.
2. **Read** the `hacking-instructor` walkthrough in `juice-shop/frontend/src/hacking-instructor/challenges/<key>.ts` if it exists.
3. **Read** the defence in `juice-shop/data/static/codefixes/<key>/` if it exists.
4. **Read** the route source in `juice-shop/routes/<key>.ts` or `juice-shop/lib/` if relevant.
5. **Cite** at least one of these sources in the briefing concepts. No invention. No paraphrasing of an LLM hallucination.

The full source-grounding protocol — including how to handle "source-thin" challenges with only an OWASP description and a mitigation URL — is in [`.claude/rules/owasp-pedagogy-companion.md`](./.claude/rules/owasp-pedagogy-companion.md). Read it before writing your first pack.

> **Why this is enforced.** Pedagogical packs are graded by students against their classroom experience and by teachers against their professional knowledge. A pack with a fabricated payload, a wrong OWASP family, or a broken kill chain wastes everyone's time. Better five impeccable packs than thirty weak ones.

---

## Dev environment

### Quickest path — Docker

```bash
git clone https://github.com/mo0ogly/juicelab.git
cd juicelab/docker
cp .env.example .env
# edit .env, set DASHBOARD_TEACHER_TOKEN and DASHBOARD_PROOF_SECRET
docker compose --env-file .env up -d --build
```

Boot times : 8 min first build, 10 s subsequent.

### Native dev (faster iteration on the overlay)

```powershell
# clone juice-shop next to juicelab
git clone https://github.com/juice-shop/juice-shop.git ../juice-shop
# manually merge the JuiceLab overlay (apply-overlay.sh forthcoming)

# launch the stack
.\juice.ps1 start
.\juice.ps1 logs shop
.\juice.ps1 health
```

See [`INSTALL.md`](./INSTALL.md) section 4 for the full native dev procedure.

### Tests

```powershell
# Dashboard tests (10 hermetic pytest cases)
cd dashboard
python -m pytest tests/ -v

# Frontend overlay (Karma + Angular)
cd ../juice-shop/frontend
npm run test
npm run build
```

The build must be green before any PR.

---

## Adding a new pedagogical pack

A pack is a set of 4 YAML files under `juice-shop/`. The keys must match `selected_challenges.yml`.

### Files

```
juice-shop/
├── frontend/src/assets/juicelab/
│   ├── briefing/<key>.yaml         PUBLIC : mission + 2-4 concepts (no payload)
│   └── journal/<key>.yaml          PUBLIC : after_solve_fr / after_solve_en prompts
└── data/juicelab-private/
    ├── hints/<key>.yaml            PRIVATE : 5 levels N1..N5
    ├── quiz/<key>.yaml             PRIVATE : 3 multiple-choice questions
    └── walkthroughs/<key>.md       PRIVATE : full solution
```

### Schemas

All schemas are in [`.claude/skills/juicelab-add-challenge/SKILL.md`](./.claude/skills/juicelab-add-challenge/SKILL.md). Summary :

**`briefing/<key>.yaml`** :

```yaml
challenge_key: "<key>"
schema_version: "juicelab.briefing.v2"
mission_fr: |
  3-6 lines, imperative voice. What to find, what to exploit, what to avoid.
mission_en: |
  Same in English.
concepts:
  - title_fr: "<concept name FR>"
    title_en: "<concept name EN>"
    body_fr: |
      3-5 lines explanation, with citations to OWASP / MITRE / CWE / RFC.
    body_en: |
      Same in English.
  # 2 to 4 concepts total
```

**`hints/<key>.yaml`** :

```yaml
challenge_key: "<key>"
schema_version: "juicelab.hints.v2"
hints:
  N1: { cost_pct: 5,  text_fr: "...", text_en: "...", pedagogical_intent: "socratic question" }
  N2: { cost_pct: 10, ... pedagogical_intent: "research direction" }
  N3: { cost_pct: 20, ... pedagogical_intent: "technical clue" }
  N4: { cost_pct: 35, ... pedagogical_intent: "guided steps" }
  N5: { cost_pct: 50, ... pedagogical_intent: "complete solution" }
```

The cost cohort `5/10/20/35/50` is **fixed** by `HINT_COST_BY_LEVEL` in `models/juicelab.types.ts`. Do not change those values without coordinating both files and updating [`docs/PEDAGOGY.md`](./docs/PEDAGOGY.md) hint cohort calibration section.

**`quiz/<key>.yaml`** :

```yaml
challenge_key: "<key>"
schema_version: "juicelab.quiz.v2"
quiz:
  Q1:
    type: multiple_choice            # required (or free_text for fallback)
    question_fr: "..."
    question_en: "..."
    options_fr: [ "...", "...", "...", "..." ]   # 4 plausible options
    options_en: [ "...", "...", "...", "..." ]   # SAME length as options_fr
    correct: 1                                    # 0-based index
    explanation_fr: |
      ...
    explanation_en: |
      ...
  Q2: ...
  Q3: ...
```

The wrong options must be **plausible**. A quiz with three absurd distractors and one obvious answer is dead pedagogy.

### Procedure

1. **Pre-flight** — read the four upstream sources (rule 2 above). Note the exact OWASP / MITRE / CWE references you will cite.
2. **Write the briefing** — mission + 2-4 concepts. Cite sources inline. No payload.
3. **Write the 5-level hints** — pedagogical_intent on each, monotonically more revealing. N5 must be a complete solution.
4. **Write the 3-question quiz** — strict equality scoring, 4 options, all plausible.
5. **Write the after-solve journal prompt** — open-ended, encourages self-explanation.
6. **Write the walkthrough** — full solution in Markdown, including the exploited surface, the payload, the validation, and the canonical defence.
7. **Lint** — run `python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py` (validates schemas, bilingual pairing, hint cohort).
8. **Build the frontend** — `cd juice-shop/frontend && npm run build` must be green.
9. **Test in browser** — open `http://127.0.0.1:3000/#/score-board`, click the **TD** button on the new challenge's card, walk through all four tabs, verify gating works.

### Pull request

Open a PR with the title : `pack(<key>): briefing + hints + quiz + journal + walkthrough`.

The PR description must include :

- The 4 sources you read (file paths in the Juice Shop tree).
- The OWASP family, MITRE technique, and CWE you targeted.
- A note on the pedagogical_intent of N5 (the complete solution).
- A screenshot of the four tabs in the browser.

---

## Editing the overlay UI

The overlay is Angular 20 standalone components, signals, RxJS. The 4 generic components (`briefing-panel`, `hints-panel`, `journal-form`, `quiz-form`) cover all 13 challenges via the `challengeKey` input. Do **not** create per-challenge components.

### Constraints

| Constraint | Source | Why |
|---|---|---|
| No new Angular route | [`.claude/skills/juicelab-add-challenge/SKILL.md`](./.claude/skills/juicelab-add-challenge/SKILL.md) | The dialog is opened from the score-board card. Per-challenge routes leak the parcours structure. Documented exceptions : `/#/juicelab` and `/#/cabinet`. |
| No hardcoded UI text | [`.claude/rules/programming.md`](./.claude/rules/programming.md) | Every visible string passes through `juicelab-overlay/models/juicelab-i18n.ts`. |
| No hardcoded URL or port | same | Every URL goes through `assets/juicelab/config.json` or env vars. |
| 800-line file size limit | same | Decompose into sub-components and shared services beyond 800 lines. |
| Signal binding for ngModel | [`.claude/skills/juicelab-add-challenge/SKILL.md` § Technical traps](./.claude/skills/juicelab-add-challenge/SKILL.md) | `text = ''` plain property does not trigger `computed()` re-evaluation. Use `readonly text = signal('')` + `[ngModel]="text()"` + `(ngModelChange)="text.set($event)"`. |

### Adding an i18n string

1. Add the key to `juicelab-overlay/models/juicelab-i18n.ts` with FR / EN entries.
2. Use `i18nSvc.t('JUICELAB_NEW_KEY')` in the template — never inline.
3. Update `juice-shop/frontend/src/assets/i18n/{en,fr_FR}.json` if the string is also used by Juice Shop core (shouldn't be, normally).

---

## Editing the dashboard

The dashboard is Flask 3 + SQLite. Single file (`app.py`) intentionally — the project values readability for teachers who may want to audit it.

### Constraints

| Constraint | Why |
|---|---|
| Token length >= 16 chars | Refused at boot — these tokens grant teacher-level access |
| Cohort id from query param OR env var, no project-specific fallback | One source of truth for the cohort string |
| Allowed event types fixed in `ALLOWED_EVENT_TYPES` | The schema validation must be tight |
| HMAC-SHA-256 of the proof markdown body, not just the meta | A modified proof must fail verification, even a typo |
| 10 hermetic tests minimum | Every route covered, every auth path covered |

### Tests

```powershell
cd dashboard
python -m pytest tests/ -v
```

If you add a route, add a test. If you change a response shape, update `dashboard.html` and the matching JS that consumes it.

---

## Pull request checklist

Before opening a PR :

- [ ] I have read [`CONTRIBUTING.md`](./CONTRIBUTING.md) (this file) and [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).
- [ ] My PR addresses one of : new pack, translation, bug fix, or doc improvement.
- [ ] If new pack : I cited 4 upstream sources in the briefing.
- [ ] If overlay edit : `npm run build` is green.
- [ ] If dashboard edit : `pytest tests/ -v` shows 10+ green tests.
- [ ] If schema change : I updated [`.claude/skills/juicelab-add-challenge/SKILL.md`](./.claude/skills/juicelab-add-challenge/SKILL.md).
- [ ] If user-facing text : it goes through `juicelab-i18n.ts` (FR + EN minimum).
- [ ] No emoticons in code, comments, or YAML — unless the design explicitly requires them.
- [ ] No hardcoded URL, port, email, or credential.
- [ ] No file > 800 lines (decompose if needed).

---

## Reporting a security issue

Read [`SECURITY.md`](./SECURITY.md). Do not file vulnerability reports as public issues — email the maintainer first.
