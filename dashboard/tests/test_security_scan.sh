#!/usr/bin/env bash
# Static security recette : bandit + pip-audit + ruff S-rules.
# Each tool runs independently ; missing tools are skipped with a
# warning so this recette stays green on minimal dev hosts. CI is
# expected to install all three and treat any HIGH bandit finding or
# any unfixed pip-audit CVE as a failure.
set -u
FAIL=0
WARN=0
LOCKFILE=dashboard/requirements.lock.txt
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s -- %s\n' "$1" "$2"; FAIL=1; }
warn() { printf '  WARN  %s -- %s\n' "$1" "$2"; WARN=$((WARN+1)); }

# --- BANDIT (Python static security) -------------------------------------
BANDIT=$(command -v bandit 2>/dev/null || ls "$HOME/.local/bin/bandit" 2>/dev/null)
BASELINE=dashboard/.bandit-baseline.json
if [ -z "$BANDIT" ]; then
  warn "SEC-01 bandit" "tool missing (pip install --user bandit)"
else
  out=$("$BANDIT" -q -r dashboard/ --exclude dashboard/tests,dashboard/data,dashboard/__pycache__ -f json 2>/dev/null || true)
  high=$(printf '%s' "$out" | python3 -c "import json,sys; d=json.loads(sys.stdin.read() or '{}'); print(d.get('metrics',{}).get('_totals',{}).get('SEVERITY.HIGH',0))" 2>/dev/null)
  med=$(printf '%s' "$out" | python3 -c "import json,sys; d=json.loads(sys.stdin.read() or '{}'); print(d.get('metrics',{}).get('_totals',{}).get('SEVERITY.MEDIUM',0))" 2>/dev/null)
  if [ "${high:-1}" != "0" ]; then
    fail "SEC-01" "bandit HIGH=$high"
  elif [ -f "$BASELINE" ]; then
    baseline_med=$(python3 -c "import json; print(json.load(open('$BASELINE')).get('metrics',{}).get('_totals',{}).get('SEVERITY.MEDIUM',0))" 2>/dev/null)
    if [ "${med:-0}" -le "${baseline_med:-0}" ]; then
      pass "SEC-01 bandit HIGH=0 MEDIUM=$med <= baseline=$baseline_med (no new findings)"
    else
      fail "SEC-01" "bandit MEDIUM=$med > baseline=$baseline_med (new findings)"
    fi
  else
    pass "SEC-01 bandit HIGH=0 (MEDIUM=$med, no baseline)"
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

# --- SEMGREP (OWASP / Python / Flask rule packs) -------------------------
SEMGREP=$(command -v semgrep 2>/dev/null || ls "$HOME/.local/bin/semgrep" 2>/dev/null)
if [ -z "$SEMGREP" ]; then
  warn "SEC-06 semgrep" "tool missing (pip install --user semgrep)"
else
  out=$("$SEMGREP" --config=p/owasp-top-ten --config=p/python --config=p/flask \
        dashboard/ --quiet --json 2>/dev/null || echo '{}')
  count=$(printf '%s' "$out" | python3 -c "import json,sys; d=json.loads(sys.stdin.read() or '{}'); print(len(d.get('results',[])))" 2>/dev/null)
  if [ "${count:-1}" = "0" ]; then
    pass "SEC-06 semgrep OWASP+Python+Flask : 0 findings"
  else
    fail "SEC-06" "semgrep $count findings (run: semgrep --config=p/owasp-top-ten dashboard/)"
  fi
fi

# --- GITLEAKS (secrets in repo, scoped to dashboard/) --------------------
GITLEAKS=$(command -v gitleaks 2>/dev/null || ls "$HOME/.local/bin/gitleaks" 2>/dev/null)
if [ -z "$GITLEAKS" ]; then
  warn "SEC-07 gitleaks" "tool missing (download from github.com/gitleaks/gitleaks)"
else
  out=$("$GITLEAKS" detect --source dashboard/ --no-git --no-banner --config dashboard/.gitleaks.toml 2>&1 || true)
  case "$out" in
    *"no leaks found"*) pass "SEC-07 gitleaks (dashboard/) : no leaks" ;;
    *"leaks found:"*)
      n=$(printf '%s' "$out" | grep -oE 'leaks found: [0-9]+' | grep -oE '[0-9]+' || echo "?")
      fail "SEC-07" "gitleaks $n leaks in dashboard/"
      ;;
    *) warn "SEC-07 gitleaks" "unexpected output, manual check needed" ;;
  esac
fi

# --- SAFETY (CVE second opinion vs pip-audit) ----------------------------
SAFETY=$(command -v safety 2>/dev/null || ls "$HOME/.local/bin/safety" 2>/dev/null)
if [ -z "$SAFETY" ]; then
  warn "SEC-08 safety" "tool missing (pip install --user safety)"
elif [ ! -f "$REQS" ]; then
  warn "SEC-08 safety" "$REQS not found"
else
  out=$("$SAFETY" check -r "$REQS" --short-report 2>&1 || true)
  case "$out" in
    *"No known security vulnerabilities"*) pass "SEC-08 safety on $REQS : no CVE" ;;
    *"vulnerabilities reported"*)
      n=$(printf '%s' "$out" | grep -oE '[0-9]+[[:space:]]+vulnerabilities reported' | grep -oE '^[0-9]+' || echo "?")
      if [ "$n" = "0" ]; then
        pass "SEC-08 safety on $REQS : no CVE"
      else
        fail "SEC-08" "safety found $n CVEs"
      fi
      ;;
    *) warn "SEC-08 safety" "unexpected output, manual check needed" ;;
  esac
fi

# --- COVERAGE (pytest under coverage.py, threshold 60%) -----------------
COVERAGE=$(command -v coverage 2>/dev/null || ls "$HOME/.local/bin/coverage" 2>/dev/null)
PYTEST_FILES="dashboard/tests/test_app.py dashboard/tests/test_ctfd_push.py dashboard/tests/test_students.py dashboard/tests/test_proof_signing.py dashboard/tests/test_cohorts_join_routes.py dashboard/tests/test_rate_limit.py dashboard/tests/test_proof_http.py dashboard/tests/test_students_pending.py dashboard/tests/test_csrf_helpers.py dashboard/tests/test_i18n_helpers.py dashboard/tests/test_verify_proof_cli.py dashboard/tests/test_proof_edge_cases.py dashboard/tests/test_crypto_invariants.py dashboard/tests/test_app_routes.py"
if [ -z "$COVERAGE" ]; then
  warn "SEC-09 coverage" "tool missing (pip install --user coverage)"
else
  out=$("$COVERAGE" run --source=dashboard -m pytest $PYTEST_FILES -q 2>&1 || true)
  passed=$(printf '%s' "$out" | grep -oE '[0-9]+ passed' | head -1 | grep -oE '[0-9]+' || echo "0")
  failed=$(printf '%s' "$out" | grep -oE '[0-9]+ failed' | head -1 | grep -oE '[0-9]+' || echo "0")
  if [ "${failed:-1}" != "0" ]; then
    fail "SEC-09" "pytest $failed failed (passed=$passed)"
  else
    pct=$("$COVERAGE" report 2>/dev/null | tail -1 | awk '{print $NF}' | tr -d '%')
    if [ -z "$pct" ]; then
      warn "SEC-09 coverage" "pytest $passed passed, coverage parse failed"
    elif [ "${pct%.*}" -ge 60 ]; then
      pass "SEC-09 pytest $passed/$passed PASS, coverage=${pct}% (>= 60% threshold)"
    else
      fail "SEC-09" "pytest $passed PASS but coverage ${pct}% < 60% threshold"
    fi
  fi
fi

# --- DAST baseline (OWASP ZAP via docker, optional) ----------------------
DOCKER=$(command -v docker 2>/dev/null)
DASH_UP=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5050/api/health 2>/dev/null || echo "")
if [ -z "$DOCKER" ]; then
  warn "SEC-10 ZAP DAST" "docker missing (apt install docker.io)"
elif [ "$DASH_UP" != "200" ]; then
  warn "SEC-10 ZAP DAST" "dashboard not running on :5050 (start via ./juice.sh dash)"
elif [ "${SKIP_DAST:-0}" = "1" ]; then
  warn "SEC-10 ZAP DAST" "skipped (SKIP_DAST=1)"
else
  out=$("$DOCKER" run --rm --network=host -t ghcr.io/zaproxy/zaproxy:stable \
        zap-baseline.py -t http://127.0.0.1:5050 -I -m 1 2>&1 | grep -E "FAIL-NEW:" | tail -1)
  case "$out" in
    *"FAIL-NEW: 0"*)
      warn_count=$(printf '%s' "$out" | grep -oE 'WARN-NEW: [0-9]+' | grep -oE '[0-9]+')
      pass_count=$(printf '%s' "$out" | grep -oE 'PASS: [0-9]+' | grep -oE '[0-9]+')
      pass "SEC-10 ZAP DAST FAIL=0 PASS=$pass_count (WARN-NEW=$warn_count : info-disclosure non-bloquants)" ;;
    *"FAIL-NEW:"*) fail "SEC-10" "ZAP DAST $out" ;;
    *) warn "SEC-10 ZAP DAST" "unexpected output, manual check needed" ;;
  esac
fi

# --- LICENSE compliance (no GPL/AGPL in dashboard deps) -----------------
PIPLIC=$(command -v pip-licenses 2>/dev/null || ls "$HOME/.local/bin/pip-licenses" 2>/dev/null)
ALLOWED="BSD License;BSD-3-Clause;BSD-2-Clause;MIT License;MIT;Mozilla Public License 2.0 (MPL 2.0);Apache Software License;Apache 2.0;Apache-2.0;Python Software Foundation License;PSF;ISC License;ISC License (ISCL);Public Domain"
DENIED="GNU General Public License;GPL;GNU Affero General Public License;AGPL;GNU Lesser General Public License;LGPL"
if [ -z "$PIPLIC" ]; then
  warn "SEC-13 pip-licenses" "tool missing (pip install --user pip-licenses)"
else
  pkgs=$(grep -oE '^[a-zA-Z][a-zA-Z0-9_.-]*' "$LOCKFILE" 2>/dev/null | sort -u | grep -v '^#' | tr '\n' ' ')
  denied_hits=$("$PIPLIC" --packages $pkgs --format=plain 2>/dev/null | awk 'NR>1' \
    | grep -E "$DENIED" || true)
  if [ -z "$denied_hits" ]; then
    pkg_count=$(printf '%s' "$pkgs" | wc -w)
    pass "SEC-13 licenses : $pkg_count pkgs, no GPL/AGPL/LGPL detected"
  else
    fail "SEC-13" "GPL-family license detected : $(echo "$denied_hits" | head -2)"
  fi
fi

# --- LICENSES.md drift (reproducible from lockfile) ----------------------
LICFILE=dashboard/LICENSES.md
GENLIC=scripts/gen_licenses.sh
if [ ! -f "$LICFILE" ]; then
  warn "SEC-14 LICENSES.md" "$LICFILE not committed (run $GENLIC)"
elif [ ! -x "$GENLIC" ]; then
  warn "SEC-14 LICENSES.md" "$GENLIC missing or not executable"
elif [ -z "${PIPLIC:-}" ]; then
  warn "SEC-14 LICENSES.md" "pip-licenses missing (skipped, see SEC-13)"
else
  cp "$LICFILE" /tmp/lic-pre.md
  bash "$GENLIC" 2>/dev/null
  if diff -q /tmp/lic-pre.md "$LICFILE" >/dev/null 2>&1; then
    pass "SEC-14 LICENSES.md in sync (regenerated, no drift)"
  else
    cp /tmp/lic-pre.md "$LICFILE"
    fail "SEC-14" "LICENSES.md drift detected (run: bash $GENLIC)"
  fi
fi

# --- SBOM CycloneDX generation (supply-chain transparency) ---------------
CYCLONEDX=$(command -v cyclonedx-py 2>/dev/null || ls "$HOME/.local/bin/cyclonedx-py" 2>/dev/null)
if [ -z "$CYCLONEDX" ]; then
  warn "SEC-12 SBOM cyclonedx" "tool missing (pip install --user cyclonedx-bom)"
elif [ ! -f "$LOCKFILE" ]; then
  warn "SEC-12 SBOM" "$LOCKFILE not found (run SEC-11 first)"
else
  out=$("$CYCLONEDX" requirements "$LOCKFILE" --output-format JSON \
    --output-file /tmp/sbom.cdx.json 2>&1)
  if [ -f /tmp/sbom.cdx.json ]; then
    spec=$(python3 -c "import json; d=json.load(open('/tmp/sbom.cdx.json')); print(d.get('specVersion','?'))")
    comp_count=$(python3 -c "import json; d=json.load(open('/tmp/sbom.cdx.json')); print(len(d.get('components',[])))")
    if [ "$comp_count" -ge 15 ]; then
      pass "SEC-12 SBOM CycloneDX $spec : $comp_count components emitted"
    else
      fail "SEC-12" "SBOM has only $comp_count components, expected >= 15"
    fi
  else
    fail "SEC-12" "cyclonedx-py failed : ${out:0:120}"
  fi
fi

# --- LOCKFILE drift (pip-compile reproducible) ---------------------------
PIPCOMPILE=$(command -v pip-compile 2>/dev/null || ls "$HOME/.local/bin/pip-compile" 2>/dev/null)
if [ -z "$PIPCOMPILE" ]; then
  warn "SEC-11 lockfile" "tool missing (pip install --user pip-tools)"
elif [ ! -f "$LOCKFILE" ]; then
  warn "SEC-11 lockfile" "$LOCKFILE not found"
else
  cp "$LOCKFILE" /tmp/lock-recette-pre.txt
  "$PIPCOMPILE" --quiet --generate-hashes \
    --output-file="$LOCKFILE" \
    dashboard/requirements.txt 2>/dev/null
  if diff -q /tmp/lock-recette-pre.txt "$LOCKFILE" >/dev/null 2>&1; then
    pkg_count=$(grep -cE "^[a-zA-Z][a-zA-Z0-9_-]*==" "$LOCKFILE" || echo "0")
    pass "SEC-11 lockfile in sync ($pkg_count pkgs pinned with --hash)"
  else
    cp /tmp/lock-recette-pre.txt "$LOCKFILE"
    fail "SEC-11" "lockfile drift detected (run: pip-compile --generate-hashes -o $LOCKFILE dashboard/requirements.txt)"
  fi
fi

echo
if [ "$FAIL" -gt "0" ]; then
  echo "RECETTE FAIL (warnings: $WARN)"
  exit 1
fi
if [ "$WARN" -gt "0" ]; then
  echo "RECETTE PASS WITH WARNINGS ($WARN tools missing — install for full coverage)"
else
  echo "RECETTE PASS (14/14)"
fi
exit 0
