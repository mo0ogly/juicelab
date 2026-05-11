# Cohort workflow — operational guide

This document describes the **trilateral cohort workflow**, the
**login flow**, the **multilingual support**, the **help popups**, and
the **operational concerns** (Google OAuth, teacher token rotation,
troubleshooting). It complements [`PEDAGOGY.md`](PEDAGOGY.md) (which
covers the *why*) and [`CLASSROOM-DEPLOYMENT.md`](CLASSROOM-DEPLOYMENT.md)
(which covers deployment topologies).

## Audience

- **Teachers (instructors)** : sections 1, 2, 4, 5, 7
- **Students** : sections 1, 3
- **Operators (sysadmins)** : sections 6, 7

---

## 1. Trilateral workflow at a glance

Three actors interact in a linear sequence :

```mermaid
sequenceDiagram
    autonumber
    participant T as Teacher
    participant D as Dashboard (Flask :5050)
    participant S as Student
    participant J as Juice Shop overlay (:3000)

    T->>D: Create cohort (UX /admin/cohorts)
    T-->>S: Share cohort code + dashboard URL
    S->>J: Open Juice Shop, JuiceLab panel
    S->>J: Login (admin@juice-sh.op or self-register)
    Note over S,J: Step 1 banner "Connecte-toi" disappears
    S->>J: Submit cohort-join modal (URL + code + email)
    J->>D: POST /api/cohort/join (status=pending)
    Note over S,J: Step 2 banner "Request sent" appears
    T->>D: /admin/cohorts -> Approve student
    D-->>J: Next status poll (60s) returns "validated"
    Note over S,J: Banner disappears; events stream
    J->>D: POST /api/sync (event_type=...)
    D-->>T: Live matrix on /dashboard updates
```

### Required pre-requisites (in order)

1. **Juice Shop authentication** — student must log in to Juice Shop
   itself (gives the JWT used by hints, quiz, journal). Without it
   the auth banner stays visible and the join modal is gated.
2. **Cohort join request** — student fills the JuiceLab modal with
   dashboard URL + cohort code + email.
3. **Teacher approval** — teacher clicks Approve on
   `/admin/cohorts`. The student's events are blocked on `/api/sync`
   with HTTP 403 until this step.

The two banners (`auth-banner` and `join-banner`) **never appear at
the same time** : the join-banner is hidden until the student is
authenticated. This is by design to keep the flow linear.

---

## 2. Teacher side

### 2.1 Create a cohort

- URL : `http://127.0.0.1:5050/admin/cohorts`
- Form : identifier (alnum + `-`, `_`, `.`, max 64) + optional label.
- Side effects : cohort row appears in the table immediately ; the
  cohort becomes available for students to join.

### 2.2 Approve / reject join requests

- Same page `/admin/cohorts` → section **Demandes d'inscription en attente**.
- Buttons **Approuver** or **Rejeter** per request.
- Approve → student status flips to `validated` → `/api/sync` accepts
  their events.
- Reject → status `rejected` → `/api/sync` returns 403 with a
  message ; the student sees a "Access denied" banner.

### 2.3 Live dashboard

- URL : `http://127.0.0.1:5050/dashboard?cohort=<id>`
- Auto-refresh every 5 s. KPI cards : students, challenges, events,
  live status.
- Per-student matrix : per-challenge pills (solved, hints N/5,
  journal, quiz X/100, flag +10). Click `journal` pill → opens the
  student's free-text journal in a modal.

### 2.4 Roster management

- URL : `http://127.0.0.1:5050/admin/students?cohort=<id>`
- Inline rename, delete, status badges (pending / validated /
  rejected).

---

## 3. Student side

### 3.1 Login to Juice Shop

The overlay is gated on the Juice Shop JWT. Two paths :

**Seeded accounts** (fastest for labs) :

| Email | Password | Role |
|---|---|---|
| `admin@juice-sh.op` | `admin123` | admin |
| `jim@juice-sh.op` | `ncc-1701` | customer |
| `bender@juice-sh.op` | `OhG0dPlease1nsertLiquor!` | customer |
| `support@juice-sh.op` | `J6aVjTgOpRs@?5l!Zkq2AYnCE@RF$P` | admin |
| `morty@juice-sh.op` | `focusOnScienceMorty!focusOnScience` | customer |

**Self-register** : `http://127.0.0.1:3000/#/register`. Picks any
email + password, then login via `http://127.0.0.1:3000/#/login`.

**Login helper** (selector with the seeded accounts pre-filled) :
`http://127.0.0.1:3000/assets/juicelab/login-helper.html`.

### 3.2 Join a cohort

After Juice Shop login :

1. Open JuiceLab panel inside Juice Shop (top-right or
   `/#/juicelab`).
2. The cohort-join modal opens on first launch. Enter :
   - **URL du dashboard** : the dashboard URL the teacher gave you
     (e.g. `http://127.0.0.1:5050`).
   - **Code de cohorte** : the cohort identifier from the teacher
     (alnum, dashes).
   - **Email** : a readable identifier for the teacher.
3. Click **Demander l'acces**. The join-banner shows "Request sent.
   Waiting for teacher approval."
4. The overlay polls `/api/student/status` every 60 s. As soon as the
   teacher approves, the banner disappears and events stream.

### 3.3 Re-open the join modal

Gear icon (Reglages cohorte) at the top of the JuiceLab panel
reopens the modal — use it if you mistyped the URL, code or email,
or to switch cohorts.

### 3.4 Help popup

The "?" icon (Aide) at the top of the JuiceLab panel opens a popup
explaining : how to join, request statuses, language switching, and
how to reset your registration. Trilingual FR / EN / BR (follows the
Juice Shop language selector).

---

## 4. Multilingual support

| Surface | Supported | Switch |
|---|---|---|
| Juice Shop core (catalog, accounts, navigation) | ~50 languages via upstream Crowdin | Language selector top-right |
| JuiceLab overlay (briefing, hints, quiz, journal, modals) | FR / EN / BR | Inherits Juice Shop language |
| Teacher dashboard (`/dashboard`, `/admin/cohorts`, `/admin/students`, `/login`) | FR / EN | URL `?lang=fr\|en`, cookie `dash_lang`, Accept-Language, default FR |

The teacher dashboard exposes a `[FR | EN]` pill switcher in the top
nav-actions of every page. A 1-year persistent cookie remembers the
choice. The HTML `lang` attribute is set dynamically per request, so
screen readers pick up the correct phonetics.

---

## 5. Help popups (UX onboarding)

Two read-only popups document the workflow in-product :

| Side | Trigger | Content |
|---|---|---|
| Teacher (dashboard) | "?" icon in nav-actions of `/dashboard`, `/admin/cohorts`, `/admin/students` | Workflow 4 steps, multilingual, teacher-token rotation (CLI, never via UX), endpoints overview, troubleshooting |
| Student (overlay) | "?" icon next to the gear in the JuiceLab panel header | How to join, request statuses (pending / validated / rejected), language switching, resetting registration |

Both popups close on `Escape` or click outside.

---

## 6. Google OAuth on local labs

Upstream Juice Shop ships with a Google OAuth login button. It uses
the **OWASP demo clientId**, which only trusts a handful of public
hosts (`demo.owasp-juice.shop`, the Heroku stagings, etc.) plus a
list of local-loopback origins routed through proxy domains. On a
plain `http://127.0.0.1:3000` install **the click always fails** :
Google rejects the origin.

The JuiceLab overlay does NOT use Google OAuth — students log in
through the seeded accounts or self-register. To avoid the broken
button, this fork ships an overlay config :

- File : `juice-shop/config/juicelab.yml`
- Content : empties `application.googleOauth.authorizedRedirects` so
  the upstream login component sets `oauthUnavailable=true` and the
  `@if (!oauthUnavailable)` guard in the template keeps the button
  hidden.
- Activation : `juice.sh start shop` exports `NODE_ENV=juicelab` so
  node-config layers `juicelab.yml` on top of `default.yml`. Override
  with `JUICELAB_NODE_ENV=...` if you ever want to switch overlays.

To re-enable Google OAuth in a class that has a real Google Cloud
Console project + a non-localhost origin, add another overlay (e.g.
`config/juicelab-prod.yml`) that restores `clientId` and
`authorizedRedirects` and start with `JUICELAB_NODE_ENV=juicelab-prod`.

---

## 7. Teacher token rotation

The `DASHBOARD_TEACHER_TOKEN` environment variable is the **only**
access control on every gated dashboard endpoint and on the HTML
admin pages. Treat it as a config secret, not as application data.

### 7.1 Why not via the UX

This was deliberately not exposed as an admin form. Reasons :

- A compromised dashboard session would let the attacker change the
  token (self-service escalation).
- A typo locks every legitimate teacher out — recovery would require
  SSH or container console.
- All HMAC-signed proofs (`DASHBOARD_PROOF_SECRET`) and tokens
  emitted before a rotation become opaque to verifiers ; this would
  invalidate student awards already issued.
- HTTP request logs may capture the token in `POST` bodies.

### 7.2 Correct rotation procedure (CLI only)

```bash
# 1) Generate a fresh 32-byte hex token (>= 16 chars required by the dashboard).
openssl rand -hex 32

# 2) Edit the environment file (.env, systemd unit, docker-compose, k8s secret).
#    Variable name : DASHBOARD_TEACHER_TOKEN

# 3) Restart the dashboard so the new value is read on boot.
bash juice.sh restart dash

# 4) Hand the new token to the teacher through an out-of-band channel
#    (1Password, Signal, in-person). Never email plaintext.
```

The help popup on the dashboard surfaces the exact procedure for the
teacher (translated FR / EN), in case they want to do it themselves.

---

## 8. Troubleshooting

### 8.1 "Aucun event recu pour cette cohorte"

Check in order :

1. The cohort actually exists : `/admin/cohorts` lists it.
2. The student is **validated**, not pending or rejected :
   `/admin/students?cohort=<id>` shows their status badge.
3. The student configured the **right dashboard URL** in their
   join modal (gear icon in the panel reopens it). If they entered
   the wrong URL, events go to `localhost` instead of your server
   and never reach the dashboard.
4. The Juice Shop instance the student is on is **reachable** from
   their browser (a NAT or firewall might block a classroom router).

### 8.2 Two banners visible at the same time

Should not happen anymore (the join-banner is gated on
`isAuthenticated()`). If it does, force-reload the Juice Shop tab
(Ctrl+Shift+R) to drop the cached bundle.

### 8.3 "Login with Google" still appears

Probably the dashboard was started without `NODE_ENV=juicelab`.
Check the shop log : the start line should read
`demarrage Juice Shop (npm start, port 3000, NODE_ENV=juicelab)`.
If not, ensure `juice.sh` is up-to-date with the fix in
`juice.sh:start_shop()` (commit `1677f09` on the `juicelab` parent
repo).

### 8.4 Sync gate returning 403 after a fresh approval

The overlay polls `/api/student/status` every 60 s. Either wait one
poll cycle, or click the gear icon → close → re-open (forces an
immediate fetch). The events queue locally during the wait and
flush on the next successful poll.

### 8.5 Dashboard returns 502 / connection refused

Restart : `bash juice.sh restart dash`. Health check :
`curl http://127.0.0.1:5050/api/health`. If the SQLite database is
locked, stop the dashboard, remove
`dashboard/data/dashboard.sqlite-shm` and `dashboard/data/dashboard.sqlite-wal`,
restart.

---

## 9. Reference endpoints

| Verb | Path | Gate | Bound UX |
|---|---|---|---|
| GET | `/dashboard` | HTML auth (cookie) | Live matrix page |
| GET | `/admin/cohorts` | HTML auth | Cohorts admin page |
| GET | `/admin/students?cohort=` | HTML auth | Roster admin page |
| GET | `/api/cohorts` | `X-Teacher-Token` | List cohorts (used by dashboard UI) |
| POST | `/api/cohorts` | `X-Teacher-Token` | Create / rename cohort |
| POST | `/api/cohorts/<cid>/reset` | `X-Teacher-Token` | Reset events + students |
| DELETE | `/api/cohorts/<cid>` | `X-Teacher-Token` | Drop cohort row |
| GET | `/api/cohort/exists?cohort_id=` | public | Live cohort code check |
| POST | `/api/cohort/join` | public | Student join request (overlay modal) |
| GET | `/api/student/status?student_token=` | public | Overlay polling (60 s) |
| GET | `/api/students/pending?cohort=` | `X-Teacher-Token` | Pending requests list |
| POST | `/api/students/<token>/approve` | `X-Teacher-Token` | Approve student |
| POST | `/api/students/<token>/reject` | `X-Teacher-Token` | Reject student |
| POST | `/api/sync` | server-side status gate | Student event ingestion |
| GET | `/api/health` | public | Health ping |
| GET | `/api/cohort?cohort=` | `X-Teacher-Token` | Live matrix data |
| GET | `/api/journal-text` | `X-Teacher-Token` | Journal modal content |
| GET | `/api/proof` | `DASHBOARD_PROOF_SECRET` | HMAC-signed PDF proof |
| GET | `/login` / `/logout` | HTML | Teacher session |

No orphan routes : every endpoint is bound to at least one visible
UX surface (page, button, banner, or polling loop).

---

## 10. Change history (selected)

- **2026-05-11** — Cohort workflow (trilateral) + FR/EN dashboard +
  help popups + Google OAuth disabled via NODE_ENV overlay. See
  parent commits `0c84f1f`, `935dacb`, `1677f09` and fork commits
  `17a35f9`, `1810d9c`, `fd5b18d`.
