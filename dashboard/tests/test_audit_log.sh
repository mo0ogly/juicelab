#!/usr/bin/env bash
# Functional recette for the audit log (data/audit.jsonl).
# Verifies that key security events land in the JSONL file with the
# expected fields, and that the file is append-only across requests.
set -u
TOK="${DASHBOARD_TEACHER_TOKEN:-change-me-please-1234567890}"
H="X-Teacher-Token: $TOK"
BASE="http://127.0.0.1:5050"
LOG="${DASHBOARD_AUDIT_LOG:-/home/fpizzi/juice/dashboard/data/audit.jsonl}"
FAIL=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s -- %s\n' "$1" "$2"; FAIL=1; }

# Reset baseline length before triggering events.
[ -f "$LOG" ] && BASELINE=$(wc -l < "$LOG") || BASELINE=0

# AUDIT-01 login_fail logged
curl -s -X POST "$BASE/login" -d "token=BAD-token-wrong-length-1234567890&next=/dashboard" >/dev/null
sleep 0.2
[ -f "$LOG" ] && grep '"event": "login_fail"' "$LOG" | tail -1 | grep -q '"source": "form"' && pass "AUDIT-01 login_fail (form)" || fail "AUDIT-01" "no login_fail line"

# AUDIT-02 login_success logged
curl -s -X POST "$BASE/login" -d "token=$TOK&next=/dashboard" >/dev/null
sleep 0.2
grep '"event": "login_success"' "$LOG" | tail -1 | grep -q '"ts"' && pass "AUDIT-02 login_success" || fail "AUDIT-02" "no login_success line"

# AUDIT-03 join_request logged
curl -s -X POST "$BASE/api/cohort/join" -H "Content-Type: application/json" \
  -d '{"cohort_id":"M2-IA-2026","student_token":"audit-test-token-12345","email":"audit@example.com"}' >/dev/null
sleep 0.2
grep '"event": "join_request"' "$LOG" | tail -1 | grep -q '"email_domain": "example.com"' && pass "AUDIT-03 join_request" || fail "AUDIT-03" "no join_request line"

# AUDIT-04 sync_blocked logged (student status=pending)
curl -s -X POST "$BASE/api/sync" -H "Content-Type: application/json" \
  -d '{"student_token":"audit-test-token-12345","cohort_id":"M2-IA-2026","event_type":"session_start","client_timestamp":"2026-05-11T00:00:00Z"}' >/dev/null
sleep 0.2
last_block=$(grep '"event": "sync_blocked"' "$LOG" | tail -1)
case "$last_block" in
  *'"status": "pending"'*|*'"status": "rejected"'*) pass "AUDIT-04 sync_blocked" ;;
  *) fail "AUDIT-04" "no sync_blocked line (last: ${last_block:0:120})" ;;
esac

# AUDIT-05 decision logged (approve via API client)
curl -s -X POST "$BASE/api/students/audit-test-token-12345/approve" \
  -H "$H" -H "Content-Type: application/json" \
  -d '{"cohort_id":"M2-IA-2026","decided_by":"audit-test"}' >/dev/null
sleep 0.2
grep '"event": "decision"' "$LOG" | tail -1 | grep -q '"decision": "validated"' && pass "AUDIT-05 decision validated" || fail "AUDIT-05" "no decision line"

# AUDIT-06 csrf_fail logged (cookie auth without CSRF header)
curl -s -X POST "$BASE/api/cohorts" -b "teacher_token=$TOK" \
  -H "Content-Type: application/json" -d '{"cohort_id":"audit-csrf"}' >/dev/null
sleep 0.2
grep '"event": "csrf_fail"' "$LOG" | tail -1 | grep -q '"path": "/api/cohorts"' && pass "AUDIT-06 csrf_fail" || fail "AUDIT-06" "no csrf_fail line"

# AUDIT-07 JSONL : each line parses as JSON
NEW=$(wc -l < "$LOG")
ADDED=$((NEW - BASELINE))
if [ "$ADDED" -ge 6 ]; then
  pass "AUDIT-07 added $ADDED audit lines (>=6)"
else
  fail "AUDIT-07" "only $ADDED audit lines added"
fi

# AUDIT-08 each line is valid JSON
tail -n "$ADDED" "$LOG" | python3 -c '
import json, sys
ok = True
for i, line in enumerate(sys.stdin):
    line = line.strip()
    if not line: continue
    try: json.loads(line)
    except Exception as e:
        print(f"line {i}: {e}"); ok=False
sys.exit(0 if ok else 1)
' && pass "AUDIT-08 JSONL parses cleanly" || fail "AUDIT-08" "malformed JSON"

# Cleanup created student
curl -s -X POST "$BASE/api/students/audit-test-token-12345/reject" \
  -H "$H" -H "Content-Type: application/json" \
  -d '{"cohort_id":"M2-IA-2026"}' >/dev/null

echo
if [ "$FAIL" = "0" ]; then echo "RECETTE PASS (8/8)"; exit 0; else echo "RECETTE FAIL"; exit 1; fi
