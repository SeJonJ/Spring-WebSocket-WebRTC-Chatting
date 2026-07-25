#!/bin/bash
# test-frontend-verification.sh — 9-A 프론트 검증 도구 자기 테스트 (회귀 가드)
#
# CFY-FB-01/02/03 의 acceptance(A-01~A-07)를 실파일 주입·복원으로 재현·단언한다.
# 실행 후 모든 변경을 원복하므로 net 비변형.
#
# EXIT: 0 = 전체 PASS, 1 = 하나 이상 실패

set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "  ✅ $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  ❌ $1"; }
expect() { # expect <desc> <expected_rc> <actual_rc>
    if [ "$2" -eq "$3" ]; then ok "$1 (rc=$3)"; else bad "$1 (expected rc=$2, got $3)"; fi
}

FE_FILE="nodejs-frontend/static/js/rtc/participant.js"
SERVER="nodejs-frontend/server.js"
ESLINT_CONFIG="nodejs-frontend/eslint.config.js"
CONFIG_TEST="nodejs-frontend/config/sage-lint-trigger-test.js"
BAK=$(mktemp -d)
cp "$FE_FILE" "$BAK/fe.js"
cp "$SERVER" "$BAK/server.js"
cp "$ESLINT_CONFIG" "$BAK/eslint.config.js"
restore() {
    cp "$BAK/fe.js" "$FE_FILE"; cp "$BAK/server.js" "$SERVER"; cp "$BAK/eslint.config.js" "$ESLINT_CONFIG"
    rm -f "$CONFIG_TEST"
    rm -rf "$BAK"
}
trap restore EXIT INT TERM

echo "## CFY-FB-01 route 구문 baseline"
O1=$(bash scripts/verify-frontend-syntax.sh); O2=$(bash scripts/verify-frontend-syntax.sh)
[ "$O1" = "$O2" ] && ok "A-01 결정론 (반복 출력 동일)" || bad "A-01 결정론"
bash scripts/verify-frontend-syntax.sh >/dev/null 2>&1; expect "A-01 clean PASS" 0 $?
printf '\nfunction sageBroken( {\n' >> "$SERVER"
bash scripts/verify-frontend-syntax.sh >/dev/null 2>&1; expect "A-02 구문오류 주입 FAIL" 1 $?
cp "$BAK/server.js" "$SERVER"
bash scripts/verify-frontend-syntax.sh >/dev/null 2>&1; expect "A-02 복원 PASS" 0 $?

echo "## CFY-FB-02 desktop sync freshness"
bash scripts/test-desktop-sync-verification.sh >/dev/null 2>&1
expect "A-03/A-04 임시 프로젝트 sync 검증" 0 $?

echo "## CFY-FB-03 변경파일 ESLint 게이트"
bash scripts/verify-frontend-lint.sh >/dev/null 2>&1; expect "A-07 미변경 시 legacy 억제 PASS" 0 $?
printf '\nconst sageTestViolation = sageUndefinedGlobal;\n' >> "$FE_FILE"
bash scripts/verify-frontend-lint.sh >/dev/null 2>&1; expect "A-06 신규 위반 차단 FAIL" 1 $?
cp "$BAK/fe.js" "$FE_FILE"
bash scripts/verify-frontend-lint.sh >/dev/null 2>&1; expect "A-06 복원 PASS" 0 $?

printf '\nconst sageServerViolation = sageUndefinedServer;\n' >> "$SERVER"
bash scripts/verify-frontend-lint.sh >/dev/null 2>&1; expect "A-06 최상위 server.js 위반 차단 FAIL" 1 $?
cp "$BAK/server.js" "$SERVER"

printf '\nthis is not valid javascript {\n' >> "$ESLINT_CONFIG"
bash scripts/verify-frontend-lint.sh >/dev/null 2>&1; expect "ESLint 설정 오류 DEGRADE" 3 $?
cp "$BAK/eslint.config.js" "$ESLINT_CONFIG"

printf 'module.exports = sageUndefinedConfigTrigger;\n' > "$CONFIG_TEST"
bash scripts/verify-changes.sh --level L2 >/dev/null 2>&1; expect "config JS 변경도 L2 lint 게이트 트리거" 2 $?
rm "$CONFIG_TEST"

echo "## CFY-FB-03 A-05 lint 가시성 (clean baseline)"
( cd nodejs-frontend && ./node_modules/.bin/eslint . >/dev/null 2>&1 ); expect "A-05 npm lint clean exit 0" 0 $?

echo "## A-08 게이트 연결 (verify-changes.sh L2 block)"
printf '\nconst sageA08Violation = sageUndefinedA08;\n' >> "$FE_FILE"
bash scripts/verify-changes.sh --level L2 >/dev/null 2>&1; expect "A-08 신규위반 → L2 BLOCK exit 2" 2 $?
cp "$BAK/fe.js" "$FE_FILE"

echo ""
echo "== 결과: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ]
