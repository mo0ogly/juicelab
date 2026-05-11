#!/usr/bin/env bash
# Functional recette for /api/cohorts CRUD.
set -u
H="X-Teacher-Token: ${DASHBOARD_TEACHER_TOKEN:-change-me-please-1234567890}"
BASE="http://127.0.0.1:5050"
CID="apex-recette-$(date +%s)"
FAIL=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s -- %s\n' "$1" "$2"; FAIL=1; }

# C-H1 GET list unauth -> 401
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/cohorts")
[ "$code" = "401" ] && pass "C-H1 unauth -> 401" || fail "C-H1" "got $code"

# C-H2 GET list auth -> 200 + list
body=$(curl -s -H "$H" "$BASE/api/cohorts")
n=$(printf '%s' "$body" | /usr/bin/python3 -c "import sys,json; print(len(json.load(sys.stdin).get('cohorts',[])))" 2>/dev/null || echo 0)
[ "$n" -ge 1 ] && pass "C-H2 GET cohorts >= 1 (got $n)" || fail "C-H2" "$body"

# C-H3 POST create new cohort
body=$(curl -s -H "$H" -H "Content-Type: application/json" -X POST "$BASE/api/cohorts" \
  -d "{\"cohort_id\":\"$CID\",\"label\":\"Recette label\"}")
ok=$(printf '%s' "$body" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))" 2>/dev/null)
[ "$ok" = "True" ] && pass "C-H3 POST create ok" || fail "C-H3" "$body"

# C-H4 GET sees new cohort with label
body=$(curl -s -H "$H" "$BASE/api/cohorts")
found=$(printf '%s' "$body" | /usr/bin/python3 -c "
import sys,json
d=json.load(sys.stdin)
m={c['cohort_id']:c['label'] for c in d['cohorts']}
print(m.get('$CID',''))
" 2>/dev/null)
[ "$found" = "Recette label" ] && pass "C-H4 GET sees label" || fail "C-H4" "got '$found'"

# C-H5 POST rejects invalid id
code=$(curl -s -o /dev/null -w "%{http_code}" -H "$H" -H "Content-Type: application/json" \
  -X POST "$BASE/api/cohorts" -d "{\"cohort_id\":\"bad id with spaces\"}")
[ "$code" = "400" ] && pass "C-H5 invalid id -> 400" || fail "C-H5" "got $code"

# C-H6 auto-discovery via /api/sync (new cohort_id appears in /api/cohorts)
AUTO_CID="apex-auto-$(date +%s)"
code=$(curl -s -o /dev/null -w "%{http_code}" -H "Content-Type: application/json" \
  -X POST "$BASE/api/sync" \
  -d "{\"student_token\":\"auto-tok\",\"cohort_id\":\"$AUTO_CID\",\"event_type\":\"challenge_solved\",\"challenge_key\":\"scoreBoardChallenge\",\"data\":{},\"client_timestamp\":\"2026-05-11T12:00:00Z\"}")
if [ "$code" = "200" ] || [ "$code" = "201" ] || [ "$code" = "204" ]; then
  body=$(curl -s -H "$H" "$BASE/api/cohorts")
  hit=$(printf '%s' "$body" | /usr/bin/python3 -c "
import sys,json
d=json.load(sys.stdin)
print('YES' if any(c['cohort_id']=='$AUTO_CID' for c in d['cohorts']) else 'NO')
" 2>/dev/null)
  [ "$hit" = "YES" ] && pass "C-H6 cohort auto-discovered" || fail "C-H6" "sync $code but cohort missing"
else
  fail "C-H6" "/api/sync $code"
fi

# C-H7 reset cohort (auto one): events + students wiped
code=$(curl -s -H "$H" -X POST "$BASE/api/cohorts/$AUTO_CID/reset" -o /tmp/reset.out -w "%{http_code}")
e=$(cat /tmp/reset.out | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('events_deleted'))" 2>/dev/null)
s=$(cat /tmp/reset.out | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('students_deleted'))" 2>/dev/null)
if [ "$code" = "200" ] && [ "$e" = "1" ] && [ "$s" = "1" ]; then
  pass "C-H7 reset wiped 1 event + 1 student"
else
  fail "C-H7" "code=$code events=$e students=$s"
fi

# C-H8 reset keeps cohort row
body=$(curl -s -H "$H" "$BASE/api/cohorts")
still=$(printf '%s' "$body" | /usr/bin/python3 -c "
import sys,json
d=json.load(sys.stdin)
print('YES' if any(c['cohort_id']=='$AUTO_CID' for c in d['cohorts']) else 'NO')
" 2>/dev/null)
[ "$still" = "YES" ] && pass "C-H8 cohort row survives reset" || fail "C-H8" "row disappeared"

# C-H9 DELETE cohort
code=$(curl -s -H "$H" -X DELETE "$BASE/api/cohorts/$AUTO_CID" -o /tmp/del.out -w "%{http_code}")
c=$(cat /tmp/del.out | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('cohorts_deleted'))" 2>/dev/null)
[ "$code" = "200" ] && [ "$c" = "1" ] && pass "C-H9 DELETE removed cohort row" || fail "C-H9" "code=$code c=$c"

# C-H10 DELETE idempotent
body=$(curl -s -H "$H" -X DELETE "$BASE/api/cohorts/$AUTO_CID")
c=$(printf '%s' "$body" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('cohorts_deleted'))" 2>/dev/null)
[ "$c" = "0" ] && pass "C-H10 DELETE idempotent" || fail "C-H10" "$body"

# Cleanup created cohort
curl -s -H "$H" -X DELETE "$BASE/api/cohorts/$CID" >/dev/null

echo
if [ "$FAIL" = "0" ]; then echo "RECETTE PASS (10/10)"; exit 0; else echo "RECETTE FAIL"; exit 1; fi
