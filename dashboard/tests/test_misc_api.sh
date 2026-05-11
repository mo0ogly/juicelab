#!/usr/bin/env bash
# Functional recette for the previously-uncovered endpoints :
#   POST /api/verify-flag         (HMAC flag verification, public)
#   GET  /api/journal-text        (gated, reads journal_filled events)
#   GET  /api/proof               (HMAC-signed PDF proof, public via secret)
#   GET  /logout                  (cookie clear + redirect)
#   POST /api/cohort/join         (rate limit 11th call returns 429)
set -u
H="X-Teacher-Token: ${DASHBOARD_TEACHER_TOKEN:-change-me-please-1234567890}"
COOKIE="teacher_token=change-me-please-1234567890"
BASE="http://127.0.0.1:5050"
FAIL=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s -- %s\n' "$1" "$2"; FAIL=1; }

# M-01 GET /logout clears cookie + redirects
code=$(curl -s -o /tmp/logout.body -D /tmp/logout.hdr -w "%{http_code}" -b "$COOKIE" "$BASE/logout")
[ "$code" = "302" ] || [ "$code" = "303" ] && pass "M-01 /logout redirects ($code)" || fail "M-01" "got $code"
grep -qi "set-cookie: teacher_token=;\|set-cookie: teacher_token=\"\"" /tmp/logout.hdr && pass "M-01b /logout clears teacher_token" || fail "M-01b" "no clear cookie"

# M-02 POST /api/verify-flag missing fields -> 400
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/verify-flag" \
  -H "Content-Type: application/json" -d '{}')
[ "$code" = "400" ] && pass "M-02 verify-flag missing fields -> 400" || fail "M-02" "got $code"

# M-03 POST /api/verify-flag full payload, wrong flag -> {valid: false}
body=$(curl -s -X POST "$BASE/api/verify-flag" \
  -H "Content-Type: application/json" \
  -d '{"student_token":"t1","cohort_id":"M2-IA-2026","challenge_key":"loginAdminChallenge","challenge_name":"Login Admin","flag":"deadbeef"}')
# Either 200 with valid:false, or 503 if JUICESHOP_CTF_SECRET missing (acceptable).
case "$body" in
  *'"valid":false'*) pass "M-03 verify-flag rejects wrong flag" ;;
  *'flag verification disabled'*) pass "M-03 verify-flag returns 503 (CTF secret not set, acceptable in dev)" ;;
  *) fail "M-03" "unexpected body: ${body:0:120}" ;;
esac

# M-04 GET /api/journal-text unauth -> 401
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/journal-text?student_token=x&cohort=y&key=z")
[ "$code" = "401" ] && pass "M-04 journal-text unauth -> 401" || fail "M-04" "got $code"

# M-05 GET /api/journal-text missing params -> 400 even when authed
code=$(curl -s -o /dev/null -w "%{http_code}" -H "$H" "$BASE/api/journal-text")
[ "$code" = "400" ] && pass "M-05 journal-text missing params -> 400" || fail "M-05" "got $code"

# M-06 GET /api/journal-text valid args -> 200 (may return empty text if no journal_filled event yet)
code=$(curl -s -o /tmp/j.body -w "%{http_code}" -H "$H" "$BASE/api/journal-text?student_token=t1&cohort=M2-IA-2026&key=loginAdminChallenge")
[ "$code" = "200" ] && pass "M-06 journal-text valid args -> 200" || fail "M-06" "got $code"

# M-07 GET /api/proof missing student_token -> 400
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/proof")
[ "$code" = "400" ] && pass "M-07 proof missing student_token -> 400" || fail "M-07" "got $code"

# M-08 GET /api/proof missing cohort -> 400
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/proof?student_token=t")
[ "$code" = "400" ] && pass "M-08 proof missing cohort -> 400" || fail "M-08" "got $code"

# M-09 GET /api/proof missing key -> 400
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/proof?student_token=t&cohort=c")
[ "$code" = "400" ] && pass "M-09 proof missing key -> 400" || fail "M-09" "got $code"

# M-10 rate limit on /api/cohort/join : 11th call returns 429
# Need a fresh-ish IP-bucket key; the rate_limit module keys by IP so it
# accumulates across this recette. We just hit /api/cohort/exists which
# is also rate-limited but with a larger bucket; here we send 12 quick
# /api/cohort/join requests with intentionally invalid bodies (400) and
# expect the bucket to flip to 429 by the 11th call.
got_429=0
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/cohort/join" \
    -H "Content-Type: application/json" -d '{}')
  if [ "$code" = "429" ]; then got_429=1; break; fi
done
[ "$got_429" = "1" ] && pass "M-10 rate limit triggers 429 on flood" || fail "M-10" "no 429 after 12 calls"

echo
if [ "$FAIL" = "0" ]; then echo "RECETTE PASS (11/11)"; exit 0; else echo "RECETTE FAIL"; exit 1; fi
