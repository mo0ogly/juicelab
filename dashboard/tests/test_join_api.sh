#!/usr/bin/env bash
# Functional recette for the cohort join workflow (UX-driven):
#   - POST /api/cohort/join (public)
#   - GET  /api/cohort/exists (public)
#   - GET  /api/student/status (public)
#   - GET  /api/students/pending (gated)
#   - POST /api/students/<token>/approve (gated)
#   - POST /api/students/<token>/reject (gated)
#   - Server-side sync gate (403 on pending/rejected)
set -u
H="X-Teacher-Token: ${DASHBOARD_TEACHER_TOKEN:-change-me-please-1234567890}"
BASE="http://127.0.0.1:5050"
CID="join-recette-$(date +%s)"
TOK="recette-student-token-$(date +%s)"
FAIL=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s -- %s\n' "$1" "$2"; FAIL=1; }
py() { /usr/bin/python3 -c "$1" 2>/dev/null; }

# J-01 cohort/exists for unknown cohort -> {"exists":false}
body=$(curl -s "$BASE/api/cohort/exists?cohort_id=$CID")
exists=$(printf '%s' "$body" | py "import sys,json; print(json.load(sys.stdin).get('exists'))")
[ "$exists" = "False" ] && pass "J-01 exists=false on unknown cohort" || fail "J-01" "$body"

# Pre-req : prof creates the cohort
curl -s -H "$H" -H "Content-Type: application/json" -X POST "$BASE/api/cohorts" \
  -d "{\"cohort_id\":\"$CID\",\"label\":\"Recette join\"}" >/dev/null

# J-02 cohort/exists now true
body=$(curl -s "$BASE/api/cohort/exists?cohort_id=$CID")
exists=$(printf '%s' "$body" | py "import sys,json; print(json.load(sys.stdin).get('exists'))")
[ "$exists" = "True" ] && pass "J-02 exists=true after prof create" || fail "J-02" "$body"

# J-03 join unknown cohort -> 404
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/cohort/join" \
  -H "Content-Type: application/json" \
  -d "{\"cohort_id\":\"ghost-${CID}\",\"student_token\":\"$TOK\",\"email\":\"alice@example.com\"}")
[ "$code" = "404" ] && pass "J-03 join unknown cohort -> 404" || fail "J-03" "got $code"

# J-04 join invalid email -> 400
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/cohort/join" \
  -H "Content-Type: application/json" \
  -d "{\"cohort_id\":\"$CID\",\"student_token\":\"$TOK\",\"email\":\"notanemail\"}")
[ "$code" = "400" ] && pass "J-04 invalid email -> 400" || fail "J-04" "got $code"

# J-05 join valid -> 202 + status=pending
body=$(curl -s -X POST "$BASE/api/cohort/join" -H "Content-Type: application/json" \
  -d "{\"cohort_id\":\"$CID\",\"student_token\":\"$TOK\",\"email\":\"alice@example.com\",\"dashboard_url\":\"http://127.0.0.1:5050\"}")
status=$(printf '%s' "$body" | py "import sys,json; print(json.load(sys.stdin).get('status'))")
[ "$status" = "pending" ] && pass "J-05 first join -> pending" || fail "J-05" "$body"

# J-06 student/status public poll -> pending
body=$(curl -s "$BASE/api/student/status?student_token=$TOK&cohort=$CID")
status=$(printf '%s' "$body" | py "import sys,json; print(json.load(sys.stdin).get('status'))")
[ "$status" = "pending" ] && pass "J-06 status poll -> pending" || fail "J-06" "$body"

# J-07 sync gate blocks pending -> 403
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/sync" \
  -H "Content-Type: application/json" \
  -d "{\"student_token\":\"$TOK\",\"cohort_id\":\"$CID\",\"event_type\":\"session_start\",\"client_timestamp\":\"2026-05-11T00:00:00Z\"}")
[ "$code" = "403" ] && pass "J-07 sync gate 403 on pending" || fail "J-07" "got $code"

# J-08 prof lists pending -> finds our token
body=$(curl -s -H "$H" "$BASE/api/students/pending?cohort=$CID")
hit=$(printf '%s' "$body" | py "import sys,json; d=json.load(sys.stdin); print('YES' if any(p['student_token']=='$TOK' for p in d.get('pending',[])) else 'NO')")
[ "$hit" = "YES" ] && pass "J-08 pending list contains token" || fail "J-08" "$body"

# J-09 prof approves -> 200 + status=validated
body=$(curl -s -H "$H" -H "Content-Type: application/json" -X POST "$BASE/api/students/$TOK/approve" \
  -d "{\"cohort_id\":\"$CID\",\"decided_by\":\"recette\"}")
status=$(printf '%s' "$body" | py "import sys,json; print(json.load(sys.stdin).get('status'))")
[ "$status" = "validated" ] && pass "J-09 approve -> validated" || fail "J-09" "$body"

# J-10 sync gate now passes -> 201
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/sync" \
  -H "Content-Type: application/json" \
  -d "{\"student_token\":\"$TOK\",\"cohort_id\":\"$CID\",\"event_type\":\"session_start\",\"client_timestamp\":\"2026-05-11T00:00:00Z\"}")
[ "$code" = "201" ] && pass "J-10 sync 201 after approve" || fail "J-10" "got $code"

# J-11 prof rejects -> 200 + status=rejected
body=$(curl -s -H "$H" -H "Content-Type: application/json" -X POST "$BASE/api/students/$TOK/reject" \
  -d "{\"cohort_id\":\"$CID\"}")
status=$(printf '%s' "$body" | py "import sys,json; print(json.load(sys.stdin).get('status'))")
[ "$status" = "rejected" ] && pass "J-11 reject -> rejected" || fail "J-11" "$body"

# J-12 sync gate blocks rejected -> 403
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/sync" \
  -H "Content-Type: application/json" \
  -d "{\"student_token\":\"$TOK\",\"cohort_id\":\"$CID\",\"event_type\":\"session_start\",\"client_timestamp\":\"2026-05-11T00:00:00Z\"}")
[ "$code" = "403" ] && pass "J-12 sync gate 403 on rejected" || fail "J-12" "got $code"

# J-13 unauth approve -> 401
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/students/$TOK/approve" \
  -H "Content-Type: application/json" -d "{\"cohort_id\":\"$CID\"}")
[ "$code" = "401" ] && pass "J-13 approve unauth -> 401" || fail "J-13" "got $code"

# J-14 admin/cohorts HTML page (gated)
code=$(curl -s -o /dev/null -w "%{http_code}" -b "teacher_token=${DASHBOARD_TEACHER_TOKEN:-change-me-please-1234567890}" "$BASE/admin/cohorts")
[ "$code" = "200" ] && pass "J-14 /admin/cohorts renders" || fail "J-14" "got $code"

# Cleanup
curl -s -H "$H" -X DELETE "$BASE/api/cohorts/$CID" >/dev/null

echo
if [ "$FAIL" = "0" ]; then echo "RECETTE PASS (14/14)"; exit 0; else echo "RECETTE FAIL"; exit 1; fi
