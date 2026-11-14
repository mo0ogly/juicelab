# JuiceLab pedagogy

JuiceLab adds a teaching layer around OWASP Juice Shop for a twelve-hour M2
course. The 14 November improvements affect this layer, without changing
challenge mechanisms. Existing integration uses a wiring patch; an overlay does
not mean the upstream files have never been patched.

French version: [PEDAGOGY-FR.md](PEDAGOGY-FR.md).

## Before during and after a challenge

Each public course briefing provides a learning mission, two objectives,
prerequisites and expected work, without a solution procedure. Work stays within
the authorised local lab.

Existing pedagogical endpoints reveal private hints in N1–N5 order. Students
see each level’s role before revealing it: reflective question, research
direction, technical clue, guided steps, complete solution. Technical hint and
walkthrough contents are unchanged by this revision.

The post-challenge journal asks for an observation, evidence and a limit, an
explanation, a justified protection and defensive transfer to a different
fictional application. A multiple-choice quiz gives an automatic score, but does
not establish analysis or creation skills. Teachers assess reasoning with the
[separate rubric](TEACHER-GUIDE.md).

The existing interface requires five words to save. The fifty-word advice helps
writing; badges retain their own length rule. None of these counts measures
response quality. Journal synchronisation depends on configuration and receipt
by the dashboard. A local save does not prove receipt.

## Active course

Delivery base: 20.4.0-SNAPSHOT, commit documented in [DOCKER.md](DOCKER.md).
The [public catalogue](../overlay/frontend/src/assets/juicelab/selected_challenges.yml)
and badge course contain these thirteen challenges. The extended historical
catalogue is [retained separately](reference/selected-challenges-legacy-20260511.yml)
and is not a validated list for this version.

| Half-day | Order | Challenge | Key |
| --- | --- | --- | --- |
| 1 | 1 | Score Board | `scoreBoardChallenge` |
| 1 | 2 | Privacy Policy | `privacyPolicyChallenge` |
| 1 | 3 | Confidential Document | `directoryListingChallenge` |
| 1 | 4 | Exposed credentials | `exposedCredentialsChallenge` |
| 1 | 5 | Password Hash Leak | `passwordHashLeakChallenge` |
| 2 | 1 | Login Admin | `loginAdminChallenge` |
| 2 | 2 | Admin Section | `adminSectionChallenge` |
| 2 | 3 | View Basket | `basketAccessChallenge` |
| 2 | 4 | Five-Star Feedback | `feedbackChallenge` |
| 3 | 1 | DOM XSS | `localXssChallenge` |
| 3 | 2 | Reflected XSS | `reflectedXssChallenge` |
| 3 | 3 | Bonus Payload | `xssBonusChallenge` |
| 3 | 4 | Forged Feedback | `forgedFeedbackChallenge` |

## Scoring explained

Hint costs 5, 10, 20, 35 and 50 accumulate; they do not replace earlier costs.
Challenge score = max(0, 100 − sum of costs). After quiz submission, per-challenge
final score = min(100, round((challenge score + quiz score)/2) + flag bonus).
Proof and dashboard use Python rounding to the nearest integer, with ties to
even. The existing flag bonus is ten after verification, zero otherwise.
Without a submitted quiz, only a partial score is available.

| Hints used | Cumulative cost | Challenge score | Quiz | Bonus | Final score |
| --- | --- | --- | --- | --- | --- |
| None | 0 | 100 | 100 | 0 | 100 |
| N1 | 5 | 95 | 100 | 0 | 98 |
| N1–N3 | 35 | 65 | 100 | 0 | 82 |
| N1–N5 | 120 | 0 | 100 | 0 | 50 |
| N1–N5 | 120 | 0 | 100 | 10 | 60 |

The overlay floor now matches the teacher proof at zero. Old persisted score_net
values are not an authoritative mark: the hint panel recomputes its display
from consumed levels. Cohort-wide certificates remain distinct from per-challenge
proofs.

## Assessment and measurement

The [before/after exercise](ASSESSMENT.md) uses two fresh defensive situations,
without paid services or new exploitation. The [teacher guide](TEACHER-GUIDE.md)
provides answers, partial credit and a comparison protocol. Its manual eight-point
rubric is separate from automatic scoring and does not alter historical marks.

Hint-level effects, completion time and learning gains remain to be measured.
Earlier claims about two cohorts, approximately sixty students and a Poisson
distribution have not been reconciled with a measurement dataset; they are not
retained as results. Lower reluctance to request hints remains a hypothesis.

## Evidence limits

An HMAC signature checks proof integrity under key-management assumptions. It
does not establish the truth of submitted events, their author’s identity or
understanding. A green card alone does not prove a business effect. Challenge13
acceptance remains open under its complete criterion; see
[RECETTE-20261114.md](RECETTE-20261114.md).

Corrected quiz13 reference: [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html),
permissions on every request, object-level checks and server-side enforcement.
Common middleware does not remove necessary business rules.
