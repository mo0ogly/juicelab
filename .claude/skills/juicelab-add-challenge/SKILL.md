---
name: juicelab-add-challenge
description: Manage the JuiceLab pedagogical parcours for the M2 TD on top of OWASP Juice Shop. CRITICAL RULE - NEVER CREATE A NEW CHALLENGE. The TD reuses the 13 existing Juice Shop challenges listed in juice-shop/frontend/src/assets/juicelab/selected_challenges.yml. Use this skill whenever the user asks to "ajoute un challenge", "cree un challenge", "modifie un challenge", "edite le pack", "fix le quiz du challenge X", "change les indices", "add a JuiceLab challenge", "edit a JuiceLab pack", or any work that touches the JuiceLab parcours - even if the user does not say the word "skill". The skill MUST refuse to create a new Juice Shop challenge entry, a new Angular route, a new component, or extend selected_challenges.yml without an explicit, informed authorization from the user. Modifications scope is limited to existing pedagogical packs (hints, quiz, journal), the overlay UI, the dashboard, and the i18n keys.
---

# juicelab-add-challenge

Skill that gates every action on the **JuiceLab pedagogical parcours** so that an
agent never silently creates a new challenge, a parallel Angular route, or a
duplicate UI when the user only asked to fix the existing 13 challenges.

## Why this skill exists

A previous session expanded scope without asking: when the user said "add the 13
packs to /#/score-board", the agent started designing fresh challenges and packs
beyond what the user wanted. The user's correction was explicit:

> "j'ai pas demande de refaire des challenges, j'ai demande de reprendre l'existant"
> *(2026-05-09 conversation log)*

The fix is structural: any agent touching the JuiceLab parcours has to read this
skill first and apply the gates below.

## When to trigger

Trigger on any of:

- "ajoute un challenge", "cree un challenge", "add a challenge"
- "modifie un challenge", "fix challenge X"
- "edit le pack quiz", "ajoute un indice", "change le journal"
- "extends selected_challenges.yml"
- Any tool call that reads or writes inside :
  - `juice-shop/data/juicelab-private/{hints,quiz,walkthroughs}/`
  - `juice-shop/frontend/src/assets/juicelab/`
  - `juice-shop/frontend/src/app/juicelab-overlay/`
  - `juice-shop/routes/juicelab.ts`
  - `dashboard/`
  - `juice-shop/data/static/challenges.yml` (FORBIDDEN, see below)

## Hard rules (BLOCKING)

| # | Rule | Enforcement |
|---|---|---|
| 1 | **No new Juice Shop challenge.** Never add a new entry to `juice-shop/data/static/challenges.yml`. That file is OWASP upstream, off-limits. | Refuse the action, propose the closest existing key from `selected_challenges.yml`. |
| 2 | **No new Angular route.** No new `path: 'something'` in `app.routing.ts` for a per-challenge component. The score-board challenge-card + coach-dialog cover all 13 challenges. **Documented exceptions** : `path: 'juicelab'` (TD parcours panel, the bootstrap entry) and `path: 'cabinet'` (hidden trophy room — gamification of captured CTF flags, deliberately unlisted). Adding any new route requires explicit user authorization captured in this table. | Refuse the action unless the user explicitly approves and the route is added here. |
| 3 | **No new entry in `selected_challenges.yml`** without the user explicitly typing OK to a question of the form: *"Le challenge `<key>` n'est pas dans les 13 du parcours. Tu veux qu'on l'ajoute pour de bon ? (oui/non)"*. | Block until explicit yes. |
| 4 | **No new component file** under `juicelab-overlay/` for a single challenge. The 4 generic components (panel, hints-panel, journal-form, quiz-form, coach-dialog) already cover everything via the `challengeKey` input. | Refuse, reuse the existing components. |
| 5 | **No fork of OWASP Juice Shop UI files** beyond the documented patches (the score-board `challenge-card` got the Coach button). All other Juice Shop sources are read-only. | Refuse, propose the overlay path instead. |

## Allowed scope

| Action | Where |
|---|---|
| Edit hints text or cost for an existing key | `juice-shop/data/juicelab-private/hints/<existingKey>.yaml` |
| Edit quiz options/correct/explanation for an existing key | `juice-shop/data/juicelab-private/quiz/<existingKey>.yaml` |
| Edit journal prompts for an existing key | `juice-shop/frontend/src/assets/juicelab/journal/<existingKey>.yaml` |
| Edit briefing pack (mission + concepts) | `juice-shop/frontend/src/assets/juicelab/briefing/<existingKey>.yaml` |
| Edit walkthroughs | `juice-shop/data/juicelab-private/walkthroughs/<existingKey>.md` |
| Edit overlay UI components | `juice-shop/frontend/src/app/juicelab-overlay/` |
| Edit dashboard | `dashboard/` |
| Add or edit i18n keys | `juice-shop/frontend/src/assets/i18n/{en,fr_FR}.json` (prefix `JUICELAB_*`) |

## Coach dialog : 4 onglets et leur role

The coach dialog (modal opened from the score-board "TD" button) has exactly four tabs, in this order. Edits must respect this contract or the student's mental model breaks.

| # | Tab | Role | Component | Data source | Allowed to edit |
|---|---|---|---|---|---|
| 1 | **Briefing** | READ-only briefing for the student before they attack. Mission statement (what to find/do) + 2-4 key security concepts to internalize. No textarea, no input. | `briefing-panel.component.ts` | `assets/juicelab/briefing/<key>.yaml` (PUBLIC, no solution) | Yes — content + layout |
| 2 | **Indices** (Hints) | 5 graduated hints N1..N5 with cost_pct 5/10/20/35/50. Server-side gating : level N+1 refused until N is consumed. Sequential warm-up on mount re-populates the in-memory map after a server restart. | `hints-panel.component.ts` | `data/juicelab-private/hints/<key>.yaml` (PRIVATE, served via `/api/juicelab/hint`, auth required) | Yes — text + cost |
| 3 | **Apres - journal** (After) | Free-text reflection AFTER the student has solved the challenge. Min 5 words to enable Save. Save persists in localStorage AND syncs to dashboard with full text. Download button generates a tamper-evident `.md` proof signed HMAC-SHA256 by the dashboard. **Includes the CTF flag input** (paste the hash from the Juice Shop solve notification → POST `/api/verify-flag` → +10 bonus on match). | `journal-form.component.ts` (phase=after) | `state.challenges[key].journal.after_solve` in localStorage + `/api/sync` events + `/api/proof` + `/api/verify-flag` server | Yes — UI only, schema fixed |
| 4 | **Quiz** | 3 multiple-choice questions to anchor the concept. Each Q is rendered as `mat-radio-group` if `q.type === 'multiple_choice'` (default), or as textarea fallback if `q.type === 'free_text'`. Score binary 0/100 per question, average = quiz score. | `quiz-form.component.ts` | `data/juicelab-private/quiz/<key>.yaml` (PRIVATE, served stripped via `/api/juicelab/quiz/questions`) | Yes — questions + options + `correct` index |

**Removed tab** : the legacy "Avant - journal" tab was replaced by **Briefing** in 2026-05-09 because students did not understand what they had to do — the open prompt "what is your hypothesis?" was useless without context. The mission + concepts structure is the canonical pre-challenge view.

**Score badge in dialog header** : a live total `(score_challenge + score_quiz) / 2 + bonus_flag` (capped at 100, with `*` suffix when the quiz is missing) is shown in the dialog title bar. Hover for the formula tooltip. Reads from `state.challenges[key]` via signals — no extra HTTP roundtrip.

## Hidden trophy room — `/#/cabinet`

A standalone Angular route deliberately omitted from any navbar / dropdown / link. Mounted at `/#/cabinet`, served by `juicelab-overlay/trophy-room/trophy-room.component.ts`. Renders the CTF flags the student has verified through `dashboard /api/verify-flag` as gold trophies in a responsive grid.

| Aspect | Detail |
|---|---|
| **Discovery** | URL guessing only. No briefing mentions it, no link points to it. The pedagogical reward is the discovery itself. |
| **Source of truth** | `state.challenges[key].flag_captured` boolean + `flag_captured_at` ISO timestamp. Both fields live in localStorage `juicelab.state` and are set by `journal-form.verifyFlag()` on a `{valid: true}` response. |
| **Counter** | `<captured> / <total>` where total is `selected_challenges.yml` length (currently 13). |
| **Empty state** | A "shield" icon + instructions on how to capture flags via the Coach. |
| **Allowed to edit** | Component template + styles (UI only). The data contract (state fields) MUST stay backwards compatible — any rename breaks existing students' localStorage. |

**Sync with existing state** : when a flag is verified, BOTH the dashboard (server-side `flag_verified` event for the proof + cohort matrix) AND the local state (client-side `flag_captured` for the trophy room) are updated. The two sources are independent — a student who clears localStorage loses their trophy display but keeps the dashboard record.

## Bridge service : Juice Shop core integration

`JuicelabBridgeService` (singleton, `providedIn: 'root'`) listens to the Juice Shop core socket.io stream and forwards relevant events into our pedagogical pipeline. Mounted via `bridgeSvc.start()` from BOTH `juicelab-panel.ngOnInit` and `coach-dialog.constructor` — the call is idempotent thanks to a `subscribed` guard, so the listener registers exactly once per page load.

**Currently relayed event** : `challenge solved`. When Juice Shop core flips a challenge to solved=true, the bridge :

1. Filters by `selected_challenges.yml` keys (TD scope only).
2. Calls `stateSvc.markSolved(key)` — adds `solved_at` timestamp to local state.
3. Emits a `challenge_solved` SyncEvent to the dashboard, including any flag value present in the socket payload (Juice Shop CTF mode).

This is the ONLY documented patch where the overlay reaches into Juice Shop core APIs. Adding more socket listeners is allowed but must follow the same pattern (idempotent start, TD key filter, sync forward).

## Schema reference for editable packs

### `assets/juicelab/briefing/<key>.yaml` — PUBLIC, no solutions

```yaml
challenge_key: "<key>"               # MUST match selected_challenges.yml
schema_version: "juicelab.briefing.v1"
mission_fr: |                        # 3-6 lines, imperative voice
  ...
mission_en: |
  ...
concepts:
  - title_fr: "<concept name FR>"
    title_en: "<concept name EN>"
    body_fr: |                       # 3-5 lines explanation
      ...
    body_en: |
      ...
  # 2 to 4 concepts total — more than 4 dilutes attention
```

### `data/juicelab-private/hints/<key>.yaml` — PRIVATE

```yaml
challenge_key: "<key>"
schema_version: "juicelab.hints.v1"
hints:
  N1: { cost_pct: 5,  text_fr: "...", text_en: "...", pedagogical_intent: "socratic question" }
  N2: { cost_pct: 10, ... pedagogical_intent: "research direction" }
  N3: { cost_pct: 20, ... pedagogical_intent: "technical clue" }
  N4: { cost_pct: 35, ... pedagogical_intent: "guided steps" }
  N5: { cost_pct: 50, ... pedagogical_intent: "complete solution" }
```

Cost cohort fixed (5/10/20/35/50) because `JuicelabScoringService` and `HINT_COST_BY_LEVEL` constants assume it. Changing requires updating both.

### `data/juicelab-private/quiz/<key>.yaml` — PRIVATE

```yaml
challenge_key: "<key>"
schema_version: "juicelab.quiz.v1"
quiz:
  Q1:
    type: multiple_choice              # required — frontend renders dynamically
    question_fr: "..."
    question_en: "..."
    options_fr: [ "...", "...", "...", "..." ]   # 4 items typical, min 2
    options_en: [ "...", "...", "...", "..." ]   # SAME length as options_fr
    correct: 1                                    # 0-based index
    explanation_fr: |
      ...
  Q2: ...
  Q3: ...
```

The server scoring `routes/juicelab.ts:scoreQuiz` does `ans === q.correct` (strict equality) for `multiple_choice`. For `free_text` it does substring keyword matching with `expected_keywords_*`.

### `assets/juicelab/journal/<key>.yaml` — PUBLIC, prompts only

```yaml
challenge_key: "<key>"
journal_prompts:
  before_solve_fr: "..."     # legacy — now displayed only as fallback
  before_solve_en: "..."     # if briefing pack is missing
  after_solve_fr: "..."
  after_solve_en: "..."
```

The "before" prompts are kept for backward compatibility but the Briefing tab supersedes them. New work should populate `briefing/<key>.yaml` and leave `journal_prompts.after_solve_*` only.

## Procedure to follow on every invocation

1. **Read** `juice-shop/frontend/src/assets/juicelab/selected_challenges.yml` and extract the 13 keys (single source of truth).
2. **Match** the requested challenge key against this list.
   - In the list -> proceed to step 3.
   - Not in the list -> ask the user the explicit question above and **block until reply**.
3. **Confirm** with the user the exact nature of the change (correct a typo, add a quiz option, rephrase a hint, etc.) before any Edit/Write.
4. **Apply** edits ONLY to the allowed paths in the table above.
5. **Verify** the YAML still validates against its schema:
   - `juicelab.quiz.v1` : Q1, Q2, Q3 each `multiple_choice` with `options_fr`, `options_en`, `correct: <int>` (0-3).
   - `juicelab.hints.v1` : 5 levels N1..N5 with `cost_pct` cohort 5/10/20/35/50.
   - `juicelab.journal.v1` : `before_solve_*` and `after_solve_*` prompts only, no answers.
6. **Confirm** that paired bilingual fields are present : every `*_fr` has its `*_en`, every option list has `options_fr` and `options_en` of equal length.
7. **Build gate** : if a frontend file was touched, run `npm.cmd run build` from `juice-shop/frontend/` and fail loudly if the build breaks. The hook `file_size_check.cjs` and TypeScript compiler are the only allowed gatekeepers.
8. **Honor** the project rules : `.claude/rules/programming.md` (zero hardcoding, zero placeholder, zero emoticon).

## Anti-patterns documented from past failures

- Creating `juice-shop/data/juicelab-private/quiz/myCustomChallenge.yaml` with a keyword that does not exist in `selected_challenges.yml`. The frontend will reach the route, get a 404, and the student sees nothing.
- Generating "improved" pedagogical content (new hints, new quiz questions) when the user asked for a UI fix only.
- Adding a new Angular route `/#/myCustomChallenge` and porting its UI by hand. Done once -> blocked at step 2 of this skill from now on.
- Touching `data/static/challenges.yml` to "register" a new challenge. Forbidden.

## Technical traps (regression-prone — read before touching the overlay)

- **Signal binding for ngModel.** `text = ''` as a plain property does NOT trigger `computed()` re-evaluation — wordCount/dirty stay frozen and the Save button never enables. Pattern : `readonly text = signal('')` + `[ngModel]="text()"` + `(ngModelChange)="text.set($event)"`. Same for `lastLoadedText` if any computed reads it.
- **Effect dependency leak.** An `effect()` that reads `state()` re-fires after every save (since save mutates state). If the effect resets UI fields like `lastSavedAt`, the badge disappears immediately. Pattern : take only `challengeKey()` / `phase()` as tracked deps and read state via `untracked(() => stateSvc.state())`.
- **Bootstrap missing on /#/score-board.** `syncSvc.configure(dashboard_url, instance_label)` and `stateSvc.ensureStudent(cohort_id, lang)` historically lived in `juicelab-panel.ngOnInit`. The coach dialog opened from the score-board never mounts that panel. The dialog must call `packSvc.getConfig()` itself in its constructor and configure both services. Otherwise the download-proof button reports `Dashboard URL non configuree` and the sync events are dropped silently.
- **Hint gating race.** The server tracks consumed hints in an in-memory map per (studentToken, challengeKey). Re-populating after a Juice Shop restart MUST be sequential : `getHint(N1)` -> wait -> `getHint(N2)` -> wait -> ... If you fire them in parallel, the network can deliver N3 before N1 and the server returns 403. Helper : a recursive `warmUpHints(key, levels, index)` that chains via `subscribe.next`.
- **Quiz answer types.** `answerQ1/Q2/Q3` are now `string | number | null` because `multiple_choice` writes a number into the radio model. The `scoreQuiz` service signature must accept `string | number | null` for all three. Server side, `ans === q.correct` does strict equality — pass numbers as numbers, not stringified.
- **Juice Shop global error toast.** Every uncaught HTTP error reaches the Juice Shop core interceptor, which shows "An unexpected error occurred undefined". Rule : every overlay HTTP call MUST consume the error in its `subscribe({ error })` handler AND re-route 401 via `authSvc.markUnauthenticated()`, NEVER rethrow. RxJS `catchError(() => of(null))` is the safe wrapper.

## Proof markdown contract — `dashboard/app.py /api/proof`

The signed `.md` lab proof is generated by `_build_proof_markdown()` and signed by `_sign_proof()`. The user-facing layout is fixed and any change must respect this contract (verify_proof.py only validates the signature, not the structure — but the teacher reads the file by hand).

### Sections in order

1. `# JuiceLab proof - <challenge name>`
2. **Meta table** : `Etudiant` (email from JWT), `Challenge key`, `Categorie`, `Difficulte`, `Cohorte`, `Token (UUID)`. The `Etudiant` line uses the email passed via `student_name` query param ; the dashboard does NOT verify the JWT — the email is informational, the cryptographic identity stays the `Token (UUID)`.
3. `## Brief` : the OWASP description from Juice Shop (`challenge_description` query param).
4. `## Journal de l'etudiant` : the latest `journal_filled` event with `phase=after`. The legacy `phase=before` was removed when the "Avant - journal" tab was replaced by the read-only Briefing tab in 2026-05-09 ; events with `phase=before` are now ignored by the proof builder.
5. `## Indices consommes` : table `Niveau | Cout (%) | Horodatage` from `hint_revealed` events, plus `Score apres indices : 100 - sum(cost_pct)`.
6. `## Quiz` : `Score quiz = (Q1+Q2+Q3)/3`, table `Question | Reponse | Score` (the `answers` and per-question scores come from the `quiz_completed` event payload that `quiz-form.submit()` now includes).
7. `## Score final` (REQUIRED, even if partial) : the canonical formula and result. See below.
8. `## Trace` : `Resolution Juice Shop | <ts | non resolu>`, `Export proof | <utc now>`.
9. **Signed footer** : `--- / PROOF: HMAC-SHA256 / SCHEME: v1 / TIMESTAMP / STUDENT / CHALLENGE / SIGNATURE: <hex>`.

### Scoring formula (canonical — change ONLY with explicit user approval)

```
score_challenge = max(0, 100 - sum(hints_costs))     # 100 if no hints, 0 if all 5 (5+10+20+35+50 = 120, clamped)
score_quiz      = (Q1_score + Q2_score + Q3_score) / 3   # each Q is 0 or 100 (multiple_choice strict equality)
bonus_flag      = 10 if a flag_verified event exists for the (student, challenge), else 0
score_final     = min(100, round((score_challenge + score_quiz) / 2) + bonus_flag)
```

Edge cases:
- Quiz not submitted yet -> `score_quiz` undefined -> proof shows `Score final partiel : <score_challenge + bonus>/100 (composante challenge seule [+10 flag CTF verifie])`. NEVER replace missing quiz with 0.
- `cost_pct` per level is fixed by `HINT_COST_BY_LEVEL` in `models/juicelab.types.ts` (5/10/20/35/50). Changing those numbers without updating both files breaks the score consistency.
- `bonus_flag` is awarded only via `/api/verify-flag` (server-side HMAC check). The Coach UI never sets it on its own.

### Sync event payload contract — what the proof builder reads

The dashboard pulls events from SQLite by `(student_token, challenge_key, cohort_id)`. Each event must carry the right `data` shape :

| Event type | Required `data.*` keys | Used by proof builder | Source |
|---|---|---|---|
| `journal_filled` | `phase: 'after'`, `text: string`, `word_count: number` | `text` -> Journal section. `phase=before` is dropped. | `journal-form.save()` |
| `hint_revealed` | `level: 'N1'..'N5'`, `cost_pct: number`, `score_after: number` | `level` + `cost_pct` -> Indices table. `score_after` ignored, score is recomputed from costs. | `hints-panel.reveal()` |
| `quiz_completed` | `score: number`, `q1_score`, `q2_score`, `q3_score`, `answers: { Q1, Q2, Q3 }` | All keys consumed. `answers.Q*` may be `string \| number`. | `quiz-form.submit()` |
| `challenge_solved` | `flag` (optional, hex string), `source: 'juice-shop-socket'` | `client_ts` -> Trace table. `flag` is informational only — the +10 bonus is awarded by `flag_verified`, not this event. | `juicelab-bridge.service.ts` (auto, listens to `io.socket().on('challenge solved')`) |
| `flag_verified` | `bonus_pts: 10` | Sets the `flag_verified` flag in the proof + adds `+10` to the score. | `dashboard /api/verify-flag` (server-side after HMAC match — NEVER emitted by the client) |

If the frontend stops sending `text` in `journal_filled` or `answers` in `quiz_completed`, the proof becomes uninformative even though the signature stays valid. Always preserve these fields when editing `journal-form.save()` or `quiz-form.submit()`.

## Dashboard Flask : routes + auth

The dashboard (`dashboard/app.py`, port 5050) exposes the following routes. Auth model :

| Route | Method | Auth | Notes |
|---|---|---|---|
| `/login` | GET | none | Form template `login.html` |
| `/login` | POST | form `token` field vs `DASHBOARD_TEACHER_TOKEN` | Sets `teacher_token` cookie HttpOnly + redirect to `next` |
| `/logout` | GET | none | Clears the cookie |
| `/dashboard` | GET | cookie `teacher_token` OR header `X-Teacher-Token` (redirects to `/login` if missing) | Renders the matrix UI |
| `/api/health` | GET | none | Liveness probe |
| `/api/sync` | POST | none (open ingestion) | Validates `event_type` against `ALLOWED_EVENT_TYPES`, persists in SQLite |
| `/api/cohort` | GET | cookie OR header (JSON 401 if missing) | Returns the cohort_summary used by the auto-refresh JS |
| `/api/journal-text` | GET | cookie OR header | Returns the latest `journal_filled phase=after` text for `(student, challenge, cohort)`. Used by the journal modal. |
| `/api/proof` | GET | none (auth via knowledge of student_token) | Generates the signed `.md` lab proof. Requires `DASHBOARD_PROOF_SECRET`. |
| `/api/verify-flag` | POST | none (auth via knowledge of student_token) | Recomputes `HMAC-SHA1(challenge_name, JUICESHOP_CTF_SECRET)`. On match : persists a `flag_verified` event and returns `{valid: true}`. The +10 bonus then automatically appears in `/api/proof` and in `/api/cohort` totals. |

**Authentication trust model** : the dashboard does NOT verify the Juice Shop JWT — it trusts whatever `student_token` the client sends. The cryptographic anti-tampering is on the proof signature (HMAC of the markdown body) and on the flag (HMAC of the challenge.name with the shared CTF_KEY). A student who falsifies their own student_token still produces a valid proof for their fake identity ; cross-checking student_token <-> email is left to the teacher reading the proof.

## Required environment variables (launcher exports)

`juice.ps1` / `aegis.sh` set these at boot. Override by exporting before invoking the launcher.

| Variable | Required ? | Used by | Default fallback |
|---|---|---|---|
| `DASHBOARD_TEACHER_TOKEN` | YES (>= 16 chars) | `/login`, `/dashboard`, `/api/cohort`, `/api/journal-text` | Hardcoded `change-me-please-...` (warned at boot) |
| `DASHBOARD_PROOF_SECRET` | YES (>= 16 chars) | HMAC of `/api/proof` markdown | Hardcoded `change-me-proof-secret-...` (warned at boot) |
| `DASHBOARD_DEFAULT_COHORT` | NO | Default cohort id when `/dashboard` is hit without `?cohort=` | Read from `frontend/src/assets/juicelab/config.json` `cohort_id` |
| `JUICESHOP_CTF_SECRET` | NO | HMAC of `/api/verify-flag` (must match Juice Shop's CTF_KEY) | Read from `juice-shop/ctf.key` |
| `CTF_KEY` | NO (Juice Shop side) | Replaces the `ctf.key` file lookup in `lib/utils.ts` | The `ctf.key` file at the project root |
| `DASHBOARD_PORT` | NO | Flask listening port | 5000 (launcher overrides to 5050) |
| `DASHBOARD_CORS_ORIGINS` | NO | Comma-separated allowlist for cross-origin POST `/api/sync` | `http://127.0.0.1:3000,http://localhost:3000` |

## CTF flag flow — end to end

1. Juice Shop config : `config/default.yml` `ctf.showFlagsInNotifications: true` (already set as part of the JuiceLab patch).
2. Student solves challenge -> Juice Shop emits notification with `Flag : <hex>` where `<hex> = HMAC-SHA1(challenge.name, CTF_KEY)`.
3. Student copies the hex, pastes in the **Apres - journal** tab flag input, clicks **Verify flag**.
4. `journal-form.verifyFlag()` POSTs `{student_token, cohort_id, challenge_key, challenge_name, flag}` to `dashboard /api/verify-flag`.
5. Dashboard recomputes `HMAC-SHA1(challenge_name, JUICESHOP_CTF_SECRET)` and `hmac.compare_digest`.
6. On match -> dashboard persists `flag_verified` event with `{bonus_pts: 10}` -> returns `{valid: true}`.
7. The next call to `/api/proof` (or auto-refresh of `/api/cohort`) reflects the +10 bonus in the score breakdown.

**Algorithm validation** : for `challenge.name = "Score Board"` with the default `ctf.key`, the expected flag is `2614339936e8282e2f820f023d4d998a1f95e02a` (HMAC-SHA1, hex digest). If the dashboard returns `{valid: false}` for a flag the student copied verbatim, check that `JUICESHOP_CTF_SECRET` env var on the dashboard matches the `ctf.key` content used by Juice Shop.

## Hardcoding — explicit policy on cohort id

The cohort id (`M2-IA-2026`, `M1-CYBER-2026`, etc.) MUST live in exactly two places :

1. **Frontend source of truth** : `juice-shop/frontend/src/assets/juicelab/config.json` `cohort_id` field. This is the value students sync to.
2. **Backend env var** : `DASHBOARD_DEFAULT_COHORT` (auto-derived by the launcher from the frontend config).

Do NOT hardcode it anywhere else :
- `dashboard/app.py` : reads from query param OR env var, NO project-specific fallback.
- `coach-dialog.component.ts`, `juicelab-panel.component.ts` : NO fallback in the `error:` branch. If `getConfig()` fails, the bootstrap is incomplete on purpose so the user fixes the config and reloads.
- `docker/docker-compose.yml`, `docker/provision.py` : `${JUICELAB_COHORT_ID:?must be set in .env}` — fail fast if env missing, no default value.
- `docker/.env.example` : placeholder `replace-me-with-cohort-id`.

Acceptable exceptions : tests fixtures (`dashboard/tests/test_app.py`), human-readable docs (`README.md`, `CONTEXTE-JuiceLab.md`) — they may use `M2-IA-2026` as an example as long as the wording is clearly an example.

## References

- Source of truth (the 13 keys) : `juice-shop/frontend/src/assets/juicelab/selected_challenges.yml`
- Project context (history of decisions) : `CONTEXTE-JuiceLab.md` at repo root
- Programming rules : `.claude/rules/programming.md`
- Anti-leak architecture : `juice-shop/routes/juicelab.ts` + `data/juicelab-private/`
- Tamper-evident proof : `dashboard/app.py` `/api/proof` + `dashboard/verify_proof.py`
- Coach dialog source : `juice-shop/frontend/src/app/juicelab-overlay/coach-dialog/coach-dialog.component.ts` (4 tabs : Briefing / Indices / Apres-journal / Quiz, bootstrap of stateSvc + syncSvc on open)
