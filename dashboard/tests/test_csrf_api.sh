#!/usr/bin/env bash
# Functional recette for CSRF double-submit + security headers.
set -u
TOK="${DASHBOARD_TEACHER_TOKEN:-change-me-please-1234567890}"
H="X-Teacher-Token: $TOK"
COOKIE="teacher_token=$TOK"
BASE="http://127.0.0.1:5050"
FAIL=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s -- %s\n' "$1" "$2"; FAIL=1; }
contains() { case "$1" in *"$2"*) return 0 ;; *) return 1 ;; esac; }

# CSRF-01 Security headers present on /api/health
hdrs=$(curl -sI "$BASE/api/health")
contains "$hdrs" "X-Content-Type-Options: nosniff" && pass "CSRF-01 X-Content-Type-Options nosniff" || fail "CSRF-01" "missing"
contains "$hdrs" "X-Frame-Options: DENY" && pass "CSRF-02 X-Frame-Options DENY" || fail "CSRF-02" "missing"
contains "$hdrs" "Referrer-Policy:" && pass "CSRF-03 Referrer-Policy present" || fail "CSRF-03" "missing"
contains "$hdrs" "Content-Security-Policy:" && pass "CSRF-04 CSP present" || fail "CSRF-04" "missing"
contains "$hdrs" "Permissions-Policy:" && pass "CSRF-05 Permissions-Policy present" || fail "CSRF-05" "missing"
contains "$hdrs" "frame-ancestors 'none'" && pass "CSRF-06 CSP forbids framing" || fail "CSRF-06" "frame-ancestors missing"

# CSRF-07 /login POST sets csrf_token cookie
rsp=$(curl -s -i -X POST "$BASE/login" -d "token=$TOK&next=/dashboard" 2>&1)
contains "$rsp" "Set-Cookie: csrf_token=" && pass "CSRF-07 /login issues csrf_token cookie" || fail "CSRF-07" "no csrf cookie issued"

# CSRF-08 POST with cookie-only auth but NO csrf header -> 403
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/cohorts" \
  -b "$COOKIE" -H "Content-Type: application/json" -d '{"cohort_id":"csrftest"}')
[ "$code" = "403" ] && pass "CSRF-08 cookie auth without X-CSRF-Token -> 403" || fail "CSRF-08" "got $code (expected 403)"

# CSRF-09 POST with cookie + matching csrf header -> 200
CSRF="abcd1234deadbeef"
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/cohorts" \
  -b "$COOKIE; csrf_token=$CSRF" \
  -H "X-CSRF-Token: $CSRF" -H "Content-Type: application/json" \
  -d '{"cohort_id":"csrftest","label":"Recette CSRF"}')
[ "$code" = "200" ] && pass "CSRF-09 cookie+matching CSRF -> 200" || fail "CSRF-09" "got $code"

# CSRF-10 POST with cookie + MISMATCHING csrf -> 403
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/cohorts" \
  -b "$COOKIE; csrf_token=$CSRF" \
  -H "X-CSRF-Token: WRONG" -H "Content-Type: application/json" \
  -d '{"cohort_id":"csrftest"}')
[ "$code" = "403" ] && pass "CSRF-10 cookie+mismatched CSRF -> 403" || fail "CSRF-10" "got $code"

# CSRF-11 POST with X-Teacher-Token header (API client) -> NO csrf needed
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/cohorts" \
  -H "$H" -H "Content-Type: application/json" \
  -d '{"cohort_id":"csrftest2","label":"API client"}')
[ "$code" = "200" ] && pass "CSRF-11 X-Teacher-Token header exempts CSRF" || fail "CSRF-11" "got $code"

# CSRF-12 GET request -> CSRF check skipped (read-only)
code=$(curl -s -o /dev/null -w "%{http_code}" -b "$COOKIE" "$BASE/api/cohorts")
[ "$code" = "200" ] && pass "CSRF-12 GET bypasses CSRF (read-only)" || fail "CSRF-12" "got $code"

# Cleanup
curl -s -X DELETE "$BASE/api/cohorts/csrftest" -H "$H" >/dev/null
curl -s -X DELETE "$BASE/api/cohorts/csrftest2" -H "$H" >/dev/null

echo
if [ "$FAIL" = "0" ]; then echo "RECETTE PASS (12/12)"; exit 0; else echo "RECETTE FAIL"; exit 1; fi
