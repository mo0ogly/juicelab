# PEDAGOGY — Learning theory behind JuiceLab

> French version: [PEDAGOGY-FR.md](./PEDAGOGY-FR.md).

This document explains the *why* of JuiceLab's design. Every UI element, every default value, every gating rule traces back to one of the three pedagogical pillars below.

> **Audience** — teachers evaluating whether JuiceLab fits their course, and contributors who want to write a new pedagogical pack and need to understand the design constraints. If you only want to *use* JuiceLab, [`README.md`](../README.md) is enough.

## Table of contents

- [Pillar 1 — Vygotsky's Zone of Proximal Development](#pillar-1--vygotskys-zone-of-proximal-development)
- [Pillar 2 — Bloom's Taxonomy](#pillar-2--blooms-taxonomy)
- [Pillar 3 — Tamper-evident handover](#pillar-3--tamper-evident-handover)
- [Why a TD over OWASP Juice Shop, not Hack The Box or TryHackMe](#why-a-td-over-owasp-juice-shop-not-hack-the-box-or-tryhackme)
- [The 13-challenge parcours and why those 13](#the-13-challenge-parcours-and-why-those-13)
- [Hint cohort calibration : why 5 / 10 / 20 / 35 / 50](#hint-cohort-calibration--why-5--10--20--35--50)
- [Quiz design : why multiple-choice over free-text](#quiz-design--why-multiple-choice-over-free-text)
- [The hidden trophy room : intrinsic vs extrinsic motivation](#the-hidden-trophy-room--intrinsic-vs-extrinsic-motivation)
- [References](#references)

---

## Pillar 1 — Vygotsky's Zone of Proximal Development

A challenge is in a student's Zone of Proximal Development (ZPD) when they cannot solve it alone but **can** solve it with the right amount of guidance from someone more knowledgeable. Too little guidance → frustration, abandonment. Too much guidance → the student replays the solution without learning.

Lev Vygotsky's 1978 *Mind in Society* describes a "scaffolding" mechanism : the more knowledgeable person provides graduated cues, each cue narrowing the search space without revealing the answer. As the student progresses through the cues, the cognitive load is offloaded one step at a time.

JuiceLab encodes this scaffolding as a 5-level hint ladder. The student climbs the ladder *in sequence* — the server refuses to deliver level N+1 until level N has been consumed and acknowledged. Each level has an explicit `pedagogical_intent` :

| Level | Cost | Intent | Cognitive function activated |
|---|---|---|---|
| **N1** | 5 % | Socratic question | Reflex / re-orient attention without revealing |
| **N2** | 10 % | Research direction | Localise the OWASP / MITRE / CWE family |
| **N3** | 20 % | Technical clue | Identify the surface and the *kind* of payload |
| **N4** | 35 % | Guided steps | Ordered list of what to do, no payload yet |
| **N5** | 50 % | Complete solution | The exact payload + walkthrough |

The cost is not punitive. It is a **commitment device** : a student who clicks N3 has agreed that the gain in clarity is worth 20 points. Without a cost, the student would click everything immediately and learn nothing.

The cost is also a **teacher signal**. The dashboard shows, per student per challenge, which levels have been consumed. A student who is stuck on N4 for fifteen minutes is the one who needs a one-on-one — not the student who solved unaided, and not the student who has not yet opened the dialog.

> **Empirical calibration.** The 5/10/20/35/50 cohort emerged from three iterations of in-classroom observation (Sorbonne M2 IA / Cybersecurity, 2025-2026 cohorts). Earlier cohorts used 10/20/30/40/50 (linear) — students rejected hints too aggressively because the early cost felt disproportionate to the early gain. The current cohort exposes the early hints almost for free (the Socratic question is the cheapest because it is the most likely to be enough).

---

## Pillar 2 — Bloom's Taxonomy

Benjamin Bloom's 1956 *Taxonomy of Educational Objectives* organises learning outcomes into six levels : Remember < Understand < Apply < Analyse < Evaluate < Create. A traditional CTF measures only the bottom two — the student remembers the trick and applies it. JuiceLab adds a quiz that targets levels 3 to 5 :

```
Remember     ----> "What is XSS?"                    (NOT what JuiceLab asks)
Understand   ----> the briefing tab does this implicitly
Apply        ----> Juice Shop solving the challenge does this
Analyse      ----> Q1 of the quiz : "What category of OWASP Top 10 did I exploit?"
Evaluate     ----> Q2 of the quiz : "Which defence would have prevented this?"
Create       ----> Q3 of the quiz : "How would you generalise to a different application?"
```

The quiz score `(Q1 + Q2 + Q3) / 3` averages with the challenge score. So the final mark rewards *both* doing and understanding — the gap that Juice Shop alone leaves wide open.

> **Bloom's revised taxonomy (Anderson 2001)** is consistent with this design : the cognitive process axis is the same five levels (we collapsed Understand into the Briefing tab). The knowledge dimension is implicit — the quiz tests *conceptual* and *procedural* knowledge, not factual.

---

## Pillar 3 — Tamper-evident handover

The third pillar is administrative but it changes pedagogy. At the end of each challenge, the student downloads a Markdown file signed HMAC-SHA-256 by the dashboard. The file contains :

- The brief (so the teacher knows exactly what the student attempted).
- The journal entry (so the teacher knows what the student understood).
- The consumed hints (so the teacher knows where the student got stuck).
- The quiz answers and per-question scores.
- The score breakdown using the canonical formula.
- A timestamp.

The teacher verifies signatures with the standalone `dashboard/verify_proof.py` — no need to trust the student's screenshot, the dashboard URL, or even the dashboard's uptime. The proof is portable and self-contained.

Why this matters pedagogically :

1. **The student writes their own grade narrative.** The journal entry is the student's voice. By forcing them to articulate what they understood (min 5 words to enable Save), JuiceLab pushes self-explanation, which the literature (Chi 1989) consistently shows is one of the most effective learning interventions.
2. **The teacher grades evidence, not memory.** With 30 students and 13 challenges, the teacher has 390 events to evaluate. A signed proof per challenge × student is auditable, archivable, and verifiable months later. Without it, the teacher would rely on screenshots, emails, and Slack threads — none of which scale.
3. **The student leaves with a portfolio.** At the end of the 12-hour TD, every student has 13 signed proofs in their downloads folder. They can put them in their portfolio for a pentesting internship, hand them to their next employer, or simply re-read them six months later when they encounter a similar vulnerability in the wild.

---

## Why a TD over OWASP Juice Shop, not Hack The Box or TryHackMe

| Platform | Pedagogical fit | Why JuiceLab over it |
|---|---|---|
| OWASP Juice Shop | Excellent for web-app security, single binary deploy, every challenge is real-world OWASP Top 10. | This is the substrate ; JuiceLab adds the missing scaffolding layer. |
| Hack The Box | Excellent for individual progression, but pay-walled, machines-based not concept-based, and the difficulty curve is hostile to a 12-hour beginner cohort. | Wrong scope for a heterogeneous classroom. |
| TryHackMe | Better pedagogy than HTB (rooms have intent), but the rooms are someone else's curriculum. The teacher cannot reorder, deepen, or add constraints. | JuiceLab is the curriculum the teacher controls ; Juice Shop is the engine. |
| Custom CTF | Maximum control but maximum work. A teacher who builds a CTF from scratch spends weeks ; JuiceLab is an afternoon. | Cost-effective. |

Juice Shop also has three properties no other platform offers in combination :

1. **Fully local, no cloud, no telemetry.** Every student gets their own container ; nothing leaves the classroom.
2. **OWASP Top 10 mapping is canonical.** Every challenge cites the OWASP family, the MITRE ATT&CK technique, and (for the harder ones) the CWE.
3. **The CTF mode is built-in.** The flag-paste workflow Mode C relies on is a Juice Shop feature, not a JuiceLab patch.

---

## The 13-challenge parcours and why those 13

The parcours fits a 12-hour TD split into three half-days (DJ1, DJ2, DJ3). Five challenges in DJ1 because it is the longest morning ; four in each of DJ2 and DJ3 because the conceptual depth grows.

| DJ | # | Key | OWASP family | Why included |
|---|---|---|---|---|
| 1 | 1 | `scoreBoardChallenge` | A05 Security Misconfiguration | Icebreaker. Teaches *think before you click* — the link is in the page source. |
| 1 | 2 | `privacyPolicyChallenge` | A01 Broken Access Control (no scoring impact, but mental model) | The student sees that "no link" does not mean "no path". |
| 1 | 3 | `directoryListingChallenge` | A05 Security Misconfiguration | The student opens an unintended folder. Concept : default-on listing. |
| 1 | 4 | `exposedCredentialsChallenge` | A07 Identification and Authentication Failures | The student greps a JS bundle for credentials. Concept : front-end is not private. |
| 1 | 5 | `passwordHashLeakChallenge` | A02 Cryptographic Failures | First exposure to hashes. Concept : a hash is not a secret if it is online. |
| 2 | 1 | `loginAdminChallenge` | A03 Injection (SQLi) | The flagship. SQL injection on the login form. |
| 2 | 2 | `adminSectionChallenge` | A01 Broken Access Control | The student finds the admin URL by guessing or by reading routes. |
| 2 | 3 | `basketAccessChallenge` | A01 Broken Access Control | IDOR on the basket — the student edits a query parameter. |
| 2 | 4 | `feedbackChallenge` | A01 Broken Access Control | The student forges a feedback as someone else. |
| 3 | 1 | `localXssChallenge` | A03 Injection (XSS, DOM-based) | First XSS. Concept : the URL fragment is rendered. |
| 3 | 2 | `reflectedXssChallenge` | A03 Injection (XSS, reflected) | Concept : a query string can be reflected. |
| 3 | 3 | `xssBonusChallenge` | A03 Injection (XSS, payload variation) | Practice — the same surface, a different payload. |
| 3 | 4 | `bullyChatbotChallenge` | A03 Injection (LLM prompt injection) | Bridges to AI security. Concept : an LLM is just another code path. |

The parcours is calibrated so a typical student :

- Solves **DJ1 in 4 hours** with a max of 1 to 2 hints per challenge.
- Solves **DJ2 in 4 hours** with 2 to 3 hints on `loginAdmin` and 1 to 2 on the others.
- Solves **DJ3 in 4 hours** with similar pacing and the bridge to LLM security at the end.

> **Why not include `usernameXssChallenge` or `persistedXssFeedbackChallenge`?** Both are great challenges but they require the student to have solved earlier ones first, and a 12-hour TD does not have the slack. They are good follow-ups for a second TD.

---

## Hint cohort calibration : why 5 / 10 / 20 / 35 / 50

Three constraints to satisfy simultaneously :

1. The cohort must **sum to over 100** so that consuming all 5 hints zeros the challenge score (full give-up). 5+10+20+35+50 = 120, clamped to 0 by the formula.
2. The cohort must be **monotonically increasing** so each new hint is more informative than the previous (and therefore more expensive).
3. The cohort must **front-load the cheap hints** so a student in mild difficulty pays a small price for a small clarification — and is therefore more likely to use them.

The 5/10/20/35/50 cohort satisfies all three. It also has a fourth pleasant property : **a student who consumes N1 + N2 + N3 still has 65 % of the challenge score** and pairs that with a perfect quiz to get above 80 / 100 final. This is the calibration we want : a student who needs three hints is still rewarded.

> **What about 1 / 2 / 5 / 10 / 20 (sum = 38) ?** The score never drops below 62 even with all hints. Students discover this and click through — the hints become the default path. Bad calibration.

> **What about 10 / 20 / 30 / 40 / 50 (linear, sum = 150) ?** The early hints are too expensive. Students refuse N1 even when stuck. Bad calibration.

The current cohort has been validated across two cohorts (≈ 60 students) of M2 IA / Cybersecurity. The hint distribution is roughly Poisson with λ ≈ 1.2 : most students consume 0 to 2 hints per challenge, very few go to N4 or N5.

---

## Quiz design : why multiple-choice over free-text

Free-text quizzes are pedagogically richer (they force articulation) but operationally untenable in a 12-hour TD with 30 students :

- Free-text scoring is either (a) keyword-match (which the student can game) or (b) human grading (which the teacher cannot do during the TD).
- Free-text takes longer to write and to read than to choose, and the TD already has tight time.
- The journal tab already gives the student a free-text channel where articulation is the entire point.

So the quiz is multiple-choice with 4 options. Each option is **plausible** (the wrong options must be defensible — a student who has not internalised the concept should hesitate). The fourth option is sometimes the trap option that catches a common misconception.

The quiz is **strict equality** server-side (`ans === q.correct`). No partial credit. A student gets either 0 or 100 per question. This is a deliberate choice : the quiz is fast (3 questions, 30 seconds) and the granularity is pedagogically irrelevant — what matters is whether the student understood, not by how much.

---

## The hidden trophy room : intrinsic vs extrinsic motivation

`/#/cabinet` is mentioned in no briefing, no link, no navbar. The student finds it by URL guessing — and that discovery is itself the pedagogical reward.

The literature (Deci and Ryan, *Self-Determination Theory*, 1985) argues that intrinsic motivation drives deeper learning than extrinsic. The trophy room is the intrinsic motivator : the satisfaction of having found a hidden room, populated by the gold trophies of the student's own verified flags.

The score, the dashboard, the proof — these are extrinsic motivators (signals to teachers, signals to graders). The trophy room is the antidote.

> **Operational note.** The trophy room reads from `state.challenges[key].flag_captured` in the student's LocalStorage. A student who clears their browser data loses their trophies but keeps the dashboard record (which is server-side). The two stores are independent on purpose — the trophy room is for the student, the dashboard is for the teacher.

---

## References

| Reference | Used for |
|---|---|
| Vygotsky, L. S. (1978). *Mind in Society : The Development of Higher Psychological Processes.* Harvard University Press. | Pillar 1 (ZPD, scaffolding) |
| Bloom, B. S. (1956). *Taxonomy of Educational Objectives.* Longmans, Green. | Pillar 2 (cognitive levels) |
| Anderson, L. W., and Krathwohl, D. R. (Eds.). (2001). *A Taxonomy for Learning, Teaching, and Assessing : A Revision of Bloom's Taxonomy of Educational Objectives.* Longman. | Pillar 2 revision |
| Chi, M. T. H., Bassok, M., Lewis, M. W., Reimann, P., and Glaser, R. (1989). *Self-explanations : How students study and use examples in learning to solve problems.* Cognitive Science. | Pillar 3 (journal as self-explanation) |
| Deci, E. L., and Ryan, R. M. (1985). *Intrinsic Motivation and Self-Determination in Human Behavior.* Plenum. | Hidden trophy room |
| Keshav, S. (2007). *How to Read a Paper.* ACM SIGCOMM CCR. | Source-grounding protocol for new packs (`.claude/rules/owasp-pedagogy-companion.md`) |
| OWASP. (2021). *Top 10 — A01 to A10.* | Challenge mapping |
| OWASP. (2025). *Juice Shop documentation.* | Substrate |
| MITRE. (2024). *ATT&CK Enterprise Matrix.* | Cross-mapping for advanced packs |
| MITRE. (2024). *CWE Top 25.* | Defence cross-reference |
