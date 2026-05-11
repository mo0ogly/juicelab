#!/usr/bin/env bash
# Functional recette for /api/students + /admin/students.
# Requires dashboard running on :5050 with DASHBOARD_TEACHER_TOKEN matching TOKEN below.
set -u
H="X-Teacher-Token: ${DASHBOARD_TEACHER_TOKEN:-change-me-please-1234567890}"
BASE="http://127.0.0.1:5050"
COHORT="M2-IA-2026"
TMP_TOKEN="apex-recette-$(date +%s)"
FAIL=0

pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s -- %s\n' "$1" "$2"; FAIL=1; }

# C-D1 health
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/health")
[ "$code" = "200" ] && pass "C-D1 /api/health 200" || fail "C-D1" "got $code"

# C-D2 GET /api/students unauth -> 401
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/students?cohort=$COHORT")
[ "$code" = "401" ] && pass "C-D2 unauth -> 401" || fail "C-D2" "got $code"

# C-D3 GET /api/students authorized
body=$(curl -s -H "$H" "$BASE/api/students?cohort=$COHORT")
count=$(printf '%s' "$body" | /usr/bin/python3 -c "import sys,json; print(len(json.load(sys.stdin).get('students',[])))" 2>/dev/null || echo "0")
[ "$count" -ge 4 ] && pass "C-D3 GET returns >= 4 students (got $count)" || fail "C-D3" "count=$count body=${body:0:120}"

# C-D4 POST upsert new student
body=$(curl -s -H "$H" -H "Content-Type: application/json" \
  -X POST "$BASE/api/students" \
  -d "{\"cohort_id\":\"$COHORT\",\"student_token\":\"$TMP_TOKEN\",\"display_name\":\"Recette Smith\"}")
ok=$(printf '%s' "$body" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))" 2>/dev/null || echo "False")
[ "$ok" = "True" ] && pass "C-D4 POST upsert ok" || fail "C-D4" "$body"

# C-D5 GET sees the new student with the name
body=$(curl -s -H "$H" "$BASE/api/students?cohort=$COHORT")
name=$(printf '%s' "$body" | /usr/bin/python3 -c "
import sys,json
d=json.load(sys.stdin)
m={s['student_token']:s['display_name'] for s in d['students']}
print(m.get('$TMP_TOKEN',''))
" 2>/dev/null)
[ "$name" = "Recette Smith" ] && pass "C-D5 GET sees new name" || fail "C-D5" "got '$name'"

# C-D6 POST clear name (display_name='')
body=$(curl -s -H "$H" -H "Content-Type: application/json" \
  -X POST "$BASE/api/students" \
  -d "{\"cohort_id\":\"$COHORT\",\"student_token\":\"$TMP_TOKEN\",\"display_name\":\"\"}")
ok=$(printf '%s' "$body" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))" 2>/dev/null)
[ "$ok" = "True" ] && pass "C-D6 POST clear ok" || fail "C-D6" "$body"

# C-D7 DELETE row
body=$(curl -s -H "$H" -X DELETE "$BASE/api/students/$TMP_TOKEN?cohort=$COHORT")
deleted=$(printf '%s' "$body" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('deleted'))" 2>/dev/null)
[ "$deleted" = "1" ] && pass "C-D7 DELETE removed 1 row" || fail "C-D7" "$body"

# C-D8 DELETE again -> deleted=0 (idempotent)
body=$(curl -s -H "$H" -X DELETE "$BASE/api/students/$TMP_TOKEN?cohort=$COHORT")
deleted=$(printf '%s' "$body" | /usr/bin/python3 -c "import sys,json; print(json.load(sys.stdin).get('deleted'))" 2>/dev/null)
[ "$deleted" = "0" ] && pass "C-D8 DELETE idempotent" || fail "C-D8" "$body"

# C-D9 POST without token -> 400
code=$(curl -s -o /dev/null -w "%{http_code}" -H "$H" -H "Content-Type: application/json" \
  -X POST "$BASE/api/students" -d "{\"cohort_id\":\"$COHORT\"}")
[ "$code" = "400" ] && pass "C-D9 POST missing token -> 400" || fail "C-D9" "got $code"

# C-D10 auto-discovery via /api/sync (event triggers ensure_student)
AUTO_TOKEN="apex-auto-$(date +%s)"
code=$(curl -s -o /dev/null -w "%{http_code}" -H "Content-Type: application/json" \
  -X POST "$BASE/api/sync" \
  -d "{\"student_token\":\"$AUTO_TOKEN\",\"cohort_id\":\"$COHORT\",\"event_type\":\"hint_revealed\",\"challenge_key\":\"recette-c\",\"data\":{\"level\":\"N1\",\"cost_pct\":5},\"client_timestamp\":\"2026-05-11T12:00:00Z\"}")
if [ "$code" = "200" ] || [ "$code" = "201" ] || [ "$code" = "204" ]; then
  body=$(curl -s -H "$H" "$BASE/api/students?cohort=$COHORT")
  found=$(printf '%s' "$body" | /usr/bin/python3 -c "
import sys,json
d=json.load(sys.stdin)
print('YES' if any(s['student_token']=='$AUTO_TOKEN' for s in d['students']) else 'NO')
" 2>/dev/null)
  [ "$found" = "YES" ] && pass "C-D10 auto-discovery on /api/sync" || fail "C-D10" "sync $code but student not registered"
else
  fail "C-D10" "/api/sync returned $code"
fi

# Cleanup auto-discovery token
curl -s -H "$H" -X DELETE "$BASE/api/students/$AUTO_TOKEN?cohort=$COHORT" >/dev/null

# C-D11 /admin/students unauth -> redirect 302
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/admin/students?cohort=$COHORT")
[ "$code" = "302" ] || [ "$code" = "303" ] && pass "C-D11 admin unauth -> $code redirect" || fail "C-D11" "got $code (expect 302/303)"

# C-D12 /admin/students auth -> 200 HTML
body=$(curl -s -H "$H" "$BASE/admin/students?cohort=$COHORT")
case "$body" in
  *"Roster de la cohorte"*) pass "C-D12 admin page renders" ;;
  *) fail "C-D12" "body head: ${body:0:120}" ;;
esac

echo
if [ "$FAIL" = "0" ]; then echo "RECETTE PASS (12/12)"; exit 0; else echo "RECETTE FAIL"; exit 1; fi
