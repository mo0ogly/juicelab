#!/usr/bin/env bash
# Functional recette for dashboard i18n FR/EN.
#   - URL ?lang= switches language
#   - Cookie dash_lang persists
#   - Default = fr
#   - All 4 pages (dashboard, /admin/cohorts, /admin/students, /login)
set -u
H="X-Teacher-Token: ${DASHBOARD_TEACHER_TOKEN:-change-me-please-1234567890}"
COOKIE="teacher_token=change-me-please-1234567890"
BASE="http://127.0.0.1:5050"
FAIL=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s -- %s\n' "$1" "$2"; FAIL=1; }
contains() { case "$1" in *"$2"*) return 0 ;; *) return 1 ;; esac; }

# I-01 default = fr
body=$(curl -s -b "$COOKIE" "$BASE/dashboard?cohort=M2-IA-2026")
contains "$body" "Suivi pedagogique" && pass "I-01 default lang = fr" || fail "I-01" "missing FR marker"

# I-02 ?lang=en flips
body=$(curl -s -b "$COOKIE" "$BASE/dashboard?cohort=M2-IA-2026&lang=en")
contains "$body" "Pedagogical monitoring" && pass "I-02 ?lang=en flips to EN" || fail "I-02" "EN marker missing"

# I-03 ?lang=fr explicit
body=$(curl -s -b "$COOKIE" "$BASE/dashboard?cohort=M2-IA-2026&lang=fr")
contains "$body" "Suivi pedagogique" && pass "I-03 ?lang=fr explicit OK" || fail "I-03" "FR marker missing"

# I-04 cookie persists EN choice
body=$(curl -s -b "$COOKIE;dash_lang=en" "$BASE/dashboard?cohort=M2-IA-2026")
contains "$body" "Pedagogical monitoring" && pass "I-04 cookie dash_lang=en persists" || fail "I-04" "EN not retained via cookie"

# I-05 invalid lang falls back to default
body=$(curl -s -b "$COOKIE" "$BASE/dashboard?cohort=M2-IA-2026&lang=xx")
contains "$body" "Suivi pedagogique" && pass "I-05 unknown lang falls back to fr" || fail "I-05" "no fallback"

# I-06 cohorts page i18n EN
body=$(curl -s -b "$COOKIE" "$BASE/admin/cohorts?lang=en")
contains "$body" "Cohort management" && pass "I-06 /admin/cohorts EN" || fail "I-06" "missing"

# I-07 students page i18n EN
body=$(curl -s -b "$COOKIE" "$BASE/admin/students?cohort=M2-IA-2026&lang=en")
contains "$body" "Roster of cohort" && pass "I-07 /admin/students EN" || fail "I-07" "missing"

# I-08 login page i18n EN (unauth)
body=$(curl -s "$BASE/login?lang=en")
contains "$body" "Sign in" && pass "I-08 /login EN button" || fail "I-08" "missing"

# I-09 lang switch sets cookie on response
cookie_set=$(curl -s -i -b "$COOKIE" "$BASE/dashboard?cohort=M2-IA-2026&lang=en" | grep -i "set-cookie: dash_lang=en")
[ -n "$cookie_set" ] && pass "I-09 ?lang=en sets dash_lang cookie" || fail "I-09" "no Set-Cookie"

# I-10 JS catalog injected (window.I18N)
body=$(curl -s -b "$COOKIE" "$BASE/dashboard?cohort=M2-IA-2026&lang=en")
contains "$body" "window.I18N" && pass "I-10 JS catalog injected" || fail "I-10" "window.I18N missing"

# I-11 html lang attr reflects active lang
body=$(curl -s -b "$COOKIE" "$BASE/dashboard?cohort=M2-IA-2026&lang=en")
contains "$body" '<html lang="en">' && pass "I-11 html lang=en attr" || fail "I-11" "wrong html lang"

# I-12 lang switcher links present
body=$(curl -s -b "$COOKIE" "$BASE/dashboard?cohort=M2-IA-2026&lang=fr")
contains "$body" 'class="lang-pill active"' && pass "I-12 lang switcher renders" || fail "I-12" "no switcher"

echo
if [ "$FAIL" = "0" ]; then echo "RECETTE PASS (12/12)"; exit 0; else echo "RECETTE FAIL"; exit 1; fi
