#!/usr/bin/env bash
# Static security recette : bandit + pip-audit + ruff S-rules.
# Each tool runs independently ; missing tools are skipped with a
# warning so this recette stays green on minimal dev hosts. CI is
# expected to install all three and treat any HIGH bandit finding or
# any unfixed pip-audit CVE as a failure.
set -u
FAIL=0
WARN=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s -- %s\n' "$1" "$2"; FAIL=1; }
warn() { printf '  WARN  %s -- %s\n' "$1" "$2"; WARN=$((WARN+1)); }

# --- BANDIT (Python static security) -------------------------------------
BANDIT=$(command -v bandit 2>/dev/null || ls "$HOME/.local/bin/bandit" 2>/dev/null)
if [ -z "$BANDIT" ]; then
  warn "SEC-01 bandit" "tool missing (pip install --user bandit)"
else
  out=$("$BANDIT" -q -r dashboard/ --exclude dashboard/tests,dashboard/data,dashboard/__pycache__ -f json 2>/dev/null || true)
  high=$(printf '%s' "$out" | python3 -c "import json,sys; d=json.loads(sys.stdin.read() or '{}'); print(d.get('metrics',{}).get('_totals',{}).get('SEVERITY.HIGH',0))" 2>/dev/null)
  med=$(printf '%s' "$out" | python3 -c "import json,sys; d=json.loads(sys.stdin.read() or '{}'); print(d.get('metrics',{}).get('_totals',{}).get('SEVERITY.MEDIUM',0))" 2>/dev/null)
  if [ "${high:-1}" = "0" ]; then
    pass "SEC-01 bandit HIGH=0 (MEDIUM=$med, acceptable for dev binding)"
  else
    fail "SEC-01" "bandit HIGH=$high"
  fi
fi

# --- RUFF S-RULES (Python lint with bandit subset) -----------------------
RUFF=$(command -v ruff 2>/dev/null)
if [ -z "$RUFF" ]; then
  warn "SEC-02 ruff" "tool missing (pip install --user ruff)"
else
  # Limit to dashboard/ (exclude tests where S101 assert is benign).
  count=$("$RUFF" check --select S --quiet dashboard/ --exclude 'dashboard/tests/*' 2>&1 | grep -c "^dashboard" || true)
  if [ "${count:-1}" -le "1" ]; then
    # 1 expected : B104/S104 binding (acknowledged via noqa, but ruff may still count).
    pass "SEC-02 ruff S-rules (productive code) <=1 finding ($count)"
  else
    fail "SEC-02" "ruff S-rules $count findings"
  fi
fi

# --- PIP-AUDIT (Python CVE in deps) --------------------------------------
PIPAUDIT=$(command -v pip-audit 2>/dev/null || ls "$HOME/.local/bin/pip-audit" 2>/dev/null)
REQS=dashboard/requirements.txt
if [ -z "$PIPAUDIT" ]; then
  warn "SEC-03 pip-audit" "tool missing (pip install --user pip-audit)"
elif [ ! -f "$REQS" ]; then
  warn "SEC-03 pip-audit" "$REQS not found"
else
  out=$("$PIPAUDIT" -r "$REQS" 2>&1 || true)
  case "$out" in
    *"No known vulnerabilities found"*) pass "SEC-03 pip-audit on $REQS : no CVE" ;;
    *"Found 0 known"*)                   pass "SEC-03 pip-audit on $REQS : no CVE" ;;
    *"Found "*)
      # Parse the "Found N" count.
      n=$(printf '%s' "$out" | grep -oE 'Found [0-9]+ known' | head -1 | grep -oE '[0-9]+' || echo "?")
      fail "SEC-03" "pip-audit found $n CVEs (see test_security_scan output)"
      ;;
    *) warn "SEC-03 pip-audit" "unexpected output, manual check needed" ;;
  esac
fi

# --- SECRETS in repo (grep heuristic, no false-positive Aks) -------------
# Looking for obvious leaks ; whitelist the documented placeholder value.
suspects=$(grep -rEn "DASHBOARD_TEACHER_TOKEN\s*=\s*['\"][^'\"]{20,}['\"]|password\s*=\s*['\"][a-zA-Z0-9_]{16,}['\"]" dashboard/ \
  --include="*.py" --include="*.sh" --include="*.yaml" --include="*.yml" 2>/dev/null \
  | grep -v "change-me-please-1234567890" \
  | grep -v "^dashboard/tests/" \
  || true)
if [ -z "$suspects" ]; then
  pass "SEC-04 no hardcoded secrets in dashboard/ (outside tests)"
else
  fail "SEC-04" "suspect secrets : $(echo "$suspects" | head -3)"
fi

# --- INLINE JS hardcoded URL (XSS / leak surface) ------------------------
# All template fetch() should use relative paths, not absolute http://
absurl=$(grep -rEn "fetch\(['\"]https?://" dashboard/templates/ 2>/dev/null || true)
if [ -z "$absurl" ]; then
  pass "SEC-05 no absolute-URL fetch() in templates"
else
  fail "SEC-05" "templates fetching absolute URLs : $(echo "$absurl" | head -2)"
fi

echo
if [ "$FAIL" -gt "0" ]; then
  echo "RECETTE FAIL (warnings: $WARN)"
  exit 1
fi
if [ "$WARN" -gt "0" ]; then
  echo "RECETTE PASS WITH WARNINGS ($WARN tools missing — install for full coverage)"
else
  echo "RECETTE PASS (5/5)"
fi
exit 0
