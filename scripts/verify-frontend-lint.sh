#!/bin/bash
# verify-frontend-lint.sh — 변경 파일 ESLint blocking 게이트 (CFY-FB-03 단계 ③)
#
# 목적: git 으로 변경된 nodejs-frontend JS 파일에만 ESLint 를 적용해, legacy 는 건드리지 않고
#       신규/변경 코드의 규칙 위반만 차단한다(단계적 도입 — 전체 CI blocking 은 이월).
#
# 격리: eslint-suppressions.json(baseline)이 기존 위반을 동결하므로, legacy 파일을 수정해도
#       baseline 초과분(신규 위반)만 error 로 잡힌다.
#
# 사용:
#   scripts/verify-frontend-lint.sh              # 작업트리(vs HEAD)+untracked 변경분
#   scripts/verify-frontend-lint.sh --base REF   # REF..HEAD 커밋 변경분 포함(CI 용)
#
# EXIT:
#   0  → PASS (변경 JS 없음 또는 신규 위반 없음)
#   1  → FAIL (baseline 에 없는 신규 ESLint 위반)
#   3  → degrade (node/eslint 부재 또는 ESLint 설정/실행 오류)

set -uo pipefail

PROJECT_ROOT="${CODEX_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$PROJECT_ROOT" ] && PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
FRONTEND_DIR="$PROJECT_ROOT/nodejs-frontend"

BASE_REF=""
[ "${1:-}" = "--base" ] && BASE_REF="${2:-}"

if ! command -v node >/dev/null 2>&1 || [ ! -x "$FRONTEND_DIR/node_modules/.bin/eslint" ]; then
    echo "⚠️  node/eslint 부재 → 프론트 lint 검증 불가 (degrade)"
    exit 3
fi

# 변경된 nodejs-frontend JS 파일 수집 (작업트리 vs HEAD + staged + untracked, 선택적 base..HEAD)
collect() {
    git -C "$PROJECT_ROOT" diff --name-only --diff-filter=ACMR HEAD -- \
        'nodejs-frontend/*.js' 'nodejs-frontend/**/*.js'
    git -C "$PROJECT_ROOT" ls-files --others --exclude-standard -- \
        'nodejs-frontend/*.js' 'nodejs-frontend/**/*.js'
    [ -n "$BASE_REF" ] && git -C "$PROJECT_ROOT" diff --name-only --diff-filter=ACMR "$BASE_REF"...HEAD -- \
        'nodejs-frontend/*.js' 'nodejs-frontend/**/*.js'
}
# nodejs-frontend/ 접두 제거(eslint 는 FRONTEND_DIR cwd 에서 실행) + 중복 제거
CHANGED=$(collect 2>/dev/null | sed 's#^nodejs-frontend/##' | LC_ALL=C sort -u | sed '/^$/d')

echo "## Frontend Lint Gate (CFY-FB-03)"
if [ -z "$CHANGED" ]; then
    echo "- 변경된 프론트 JS 없음 → PASS"
    exit 0
fi

COUNT=$(printf '%s\n' "$CHANGED" | grep -c .)
echo "- 대상 변경 JS: $COUNT 파일"

# ignored(vendor 등) 파일이 섞여도 --no-warn-ignored 로 경고화하지 않음. suppressions 는 자동 적용.
# xargs 는 ESLint exit 1(규칙 위반)과 exit 2(설정/실행 오류)를 플랫폼별로 다르게 변환하므로
# Bash 배열로 한 번에 전달해 ESLint 원본 상태 코드를 보존한다.
FILES=()
while IFS= read -r file; do
    [ -n "$file" ] && FILES[${#FILES[@]}]="$file"
done <<EOF
$CHANGED
EOF

( cd "$FRONTEND_DIR" && ./node_modules/.bin/eslint --no-warn-ignored "${FILES[@]}" )
RC=$?

if [ "$RC" -eq 0 ]; then
    echo "- 판정: PASS — 변경 파일에 신규 위반 없음"
    exit 0
fi
if [ "$RC" -eq 1 ]; then
    echo "- 판정: FAIL — baseline 초과 신규 ESLint 위반 (위 목록)"
    exit 1
fi

echo "- 판정: DEGRADE — ESLint 설정 또는 실행 오류 (exit $RC)"
exit 3
