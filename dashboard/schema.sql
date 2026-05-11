-- JuiceLab dashboard - SQLite schema
-- Stores pedagogical events emitted by the juicelab-overlay plugin running
-- inside one or more Juice Shop instances.

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_token   TEXT    NOT NULL,
    cohort_id       TEXT    NOT NULL,
    event_type      TEXT    NOT NULL,
    challenge_key   TEXT,
    data_json       TEXT    NOT NULL DEFAULT '{}',
    client_ts       TEXT    NOT NULL,
    server_ts       TEXT    NOT NULL,
    instance_label  TEXT,
    award_pushed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_cohort       ON events(cohort_id);
CREATE INDEX IF NOT EXISTS idx_events_student      ON events(student_token);
CREATE INDEX IF NOT EXISTS idx_events_type         ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_challenge    ON events(challenge_key);
CREATE INDEX IF NOT EXISTS idx_events_cohort_student ON events(cohort_id, student_token);
-- idx_events_award_pending is created by db._migrate() after the column is
-- ensured to exist (legacy DBs predate the award_pushed_at column).

-- Cache of CTFd team identity per JuiceLab student. Populated lazily on the
-- first hint_revealed event for an unknown student_token, by looking up
-- /api/v1/teams?affiliation=<cohort> on the CTFd server. Stays NULL on the
-- ctfd_team_id column if the student has not registered on CTFd yet (the
-- mapping resolution will retry on the next hint event).
CREATE TABLE IF NOT EXISTS student_team_mapping (
    student_token   TEXT    PRIMARY KEY,
    ctfd_team_id    INTEGER,
    ctfd_user_id    INTEGER,
    last_synced_at  TEXT    NOT NULL
);

-- Registry of cohorts. Auto-populated on first event via ensure_cohort().
-- Reset = wipe events+students for the cohort. Delete = drop everything.
CREATE TABLE IF NOT EXISTS cohorts (
    cohort_id   TEXT    PRIMARY KEY,
    label       TEXT,
    created_at  TEXT    NOT NULL
);

-- Roster managed via /admin/students. Auto-populated on first sync event
-- (display_name = NULL) so prof can rename inline.
-- status = 'pending' on join request, 'validated' after prof approval,
-- 'rejected' after prof refusal. Legacy rows (auto-seeded from events) default
-- to 'validated' via _migrate() so existing classrooms keep working.
CREATE TABLE IF NOT EXISTS students (
    cohort_id          TEXT    NOT NULL,
    student_token      TEXT    NOT NULL,
    display_name       TEXT,
    email              TEXT,
    status             TEXT    NOT NULL DEFAULT 'pending',
    dashboard_url_used TEXT,
    decided_at         TEXT,
    decided_by         TEXT,
    created_at         TEXT    NOT NULL,
    updated_at         TEXT    NOT NULL,
    PRIMARY KEY (cohort_id, student_token)
);
CREATE INDEX IF NOT EXISTS idx_students_cohort ON students(cohort_id);
-- idx_students_status is created by db._migrate() after the status column
-- is ensured to exist (legacy DBs predate the column).
