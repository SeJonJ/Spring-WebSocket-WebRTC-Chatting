#!/bin/bash
# Desktop sync 검증 회귀 테스트.
# 실제 프로젝트 산출물 대신 임시 프로젝트에서 dry-run 및 freshness 검증의 비변형 계약을 확인한다.

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURE_ROOT=$(mktemp -d)
FIXTURE_DESKTOP="$FIXTURE_ROOT/chatforyou-desktop"
FIXTURE_FRONTEND="$FIXTURE_ROOT/nodejs-frontend"
FIXTURE_SCRIPTS="$FIXTURE_ROOT/scripts"

cleanup() {
    rm -rf "$FIXTURE_ROOT"
}
trap cleanup EXIT INT TERM

PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "  PASS: $1"
}

bad() {
    FAIL=$((FAIL + 1))
    echo "  FAIL: $1"
}

expect_rc() {
    if [ "$2" -eq "$3" ]; then
        ok "$1 (rc=$3)"
    else
        bad "$1 (expected rc=$2, got $3)"
    fi
}

tree_digest() {
    local target="$1"

    if [ ! -e "$target" ]; then
        printf 'MISSING\n'
        return
    fi

    (
        cd "$target" || exit 1
        find . -print | LC_ALL=C sort | while IFS= read -r entry; do
            if [ -L "$entry" ]; then
                printf 'L %s %s\n' "$entry" "$(readlink "$entry")"
            elif [ -f "$entry" ]; then
                if stat -f '%Sp %m' "$entry" >/dev/null 2>&1; then
                    metadata=$(stat -f '%Sp %m' "$entry")
                else
                    metadata=$(stat -c '%A %Y' "$entry")
                fi
                printf 'F %s %s ' "$entry" "$metadata"
                shasum -a 256 "$entry" | awk '{print $1}'
            elif [ -d "$entry" ]; then
                if stat -f '%Sp %m' "$entry" >/dev/null 2>&1; then
                    metadata=$(stat -f '%Sp %m' "$entry")
                else
                    metadata=$(stat -c '%A %Y' "$entry")
                fi
                printf 'D %s %s\n' "$entry" "$metadata"
            fi
        done
    ) | shasum -a 256 | awk '{print $1}'
}

mkdir -p \
    "$FIXTURE_DESKTOP/build-scripts" \
    "$FIXTURE_FRONTEND/static/js" \
    "$FIXTURE_FRONTEND/templates" \
    "$FIXTURE_FRONTEND/config" \
    "$FIXTURE_SCRIPTS"

cp -a "$PROJECT_ROOT/chatforyou-desktop/build-scripts/lib" "$FIXTURE_DESKTOP/build-scripts/lib"
cp "$PROJECT_ROOT/chatforyou-desktop/build-scripts/sync-frontend.js" "$FIXTURE_DESKTOP/build-scripts/sync-frontend.js"
cp "$PROJECT_ROOT/chatforyou-desktop/build-scripts/convert_path.json" "$FIXTURE_DESKTOP/build-scripts/convert_path.json"
cp "$PROJECT_ROOT/chatforyou-desktop/package.json" "$FIXTURE_DESKTOP/package.json"
cp "$PROJECT_ROOT/scripts/verify-desktop-sync.sh" "$FIXTURE_SCRIPTS/verify-desktop-sync.sh"
: > "$FIXTURE_SCRIPTS/desktop-sync-extra-baseline.txt"

printf 'console.log("fixture");\n' > "$FIXTURE_FRONTEND/static/js/app.js"
printf '<main>fixture</main>\n' > "$FIXTURE_FRONTEND/templates/index.html"
printf 'window.__CONFIG__ = { API_BASE_URL: "http://localhost" };\n' > "$FIXTURE_FRONTEND/config/config.js"
cp "$FIXTURE_FRONTEND/config/config.js" "$FIXTURE_FRONTEND/config/config.local.js"
cp "$FIXTURE_FRONTEND/config/config.js" "$FIXTURE_FRONTEND/config/config.prod.js"

(
    cd "$FIXTURE_DESKTOP" &&
    node build-scripts/sync-frontend.js --skip-backup >/dev/null 2>&1
) || {
    echo "fixture 초기 sync 실패"
    exit 1
}

echo "## Desktop dry-run 비변형"
BEFORE_DRY_RUN=$(tree_digest "$FIXTURE_DESKTOP")
(
    cd "$FIXTURE_DESKTOP" &&
    node build-scripts/sync-frontend.js --dry-run --skip-backup >/dev/null 2>&1
)
DRY_RUN_RC=$?
AFTER_DRY_RUN=$(tree_digest "$FIXTURE_DESKTOP")
expect_rc "dry-run 실행 성공" 0 "$DRY_RUN_RC"
if [ "$BEFORE_DRY_RUN" = "$AFTER_DRY_RUN" ]; then
    ok "dry-run 후 Desktop 트리 불변"
else
    bad "dry-run 후 Desktop 트리가 변경됨"
fi

echo "## Desktop tree digest 메타데이터 감지"
BEFORE_MODE_CHANGE=$(tree_digest "$FIXTURE_DESKTOP")
chmod +x "$FIXTURE_DESKTOP/src/static/js/app.js"
AFTER_MODE_CHANGE=$(tree_digest "$FIXTURE_DESKTOP")
chmod -x "$FIXTURE_DESKTOP/src/static/js/app.js"
if [ "$BEFORE_MODE_CHANGE" != "$AFTER_MODE_CHANGE" ]; then
    ok "파일 mode 변경 감지"
else
    bad "파일 mode 변경을 digest가 놓침"
fi

echo "## Desktop sync check clean 비변형"
BEFORE_CLEAN_CHECK=$(tree_digest "$FIXTURE_DESKTOP")
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
CLEAN_RC=$?
AFTER_CLEAN_CHECK=$(tree_digest "$FIXTURE_DESKTOP")
expect_rc "clean baseline PASS" 0 "$CLEAN_RC"
if [ "$BEFORE_CLEAN_CHECK" = "$AFTER_CLEAN_CHECK" ]; then
    ok "clean 검증 후 Desktop 트리 불변"
else
    bad "clean 검증 후 Desktop 트리가 변경됨"
fi

echo "## Desktop sync check macOS 메타파일 제외"
printf 'metadata\n' > "$FIXTURE_DESKTOP/src/static/.DS_Store"
printf 'metadata\n' > "$FIXTURE_DESKTOP/src/config/.DS_Store"
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
STATIC_DS_STORE_RC=$?
expect_rc "static/config .DS_Store drift 제외" 0 "$STATIC_DS_STORE_RC"
rm "$FIXTURE_DESKTOP/src/static/.DS_Store"
rm "$FIXTURE_DESKTOP/src/config/.DS_Store"

echo "## Desktop sync check drift 비변형"
printf 'console.log("drift");\n' > "$FIXTURE_FRONTEND/static/js/app.js"
BEFORE_DRIFT_CHECK=$(tree_digest "$FIXTURE_DESKTOP")
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
DRIFT_RC=$?
AFTER_DRIFT_CHECK=$(tree_digest "$FIXTURE_DESKTOP")
expect_rc "source drift FAIL" 1 "$DRIFT_RC"
if [ "$BEFORE_DRIFT_CHECK" = "$AFTER_DRIFT_CHECK" ]; then
    ok "drift 검증 후 Desktop 트리 불변"
else
    bad "drift 검증 후 Desktop 트리가 변경됨"
fi

printf 'console.log("fixture");\n' > "$FIXTURE_FRONTEND/static/js/app.js"
(
    cd "$FIXTURE_DESKTOP" &&
    node build-scripts/sync-frontend.js --skip-backup >/dev/null 2>&1
) || exit 1

echo "## Desktop sync check source 삭제"
rm "$FIXTURE_FRONTEND/static/js/app.js"
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
SOURCE_DELETE_RC=$?
expect_rc "source 삭제로 남은 stale target FAIL" 1 "$SOURCE_DELETE_RC"
printf 'console.log("fixture");\n' > "$FIXTURE_FRONTEND/static/js/app.js"

echo "## Desktop sync check target-only baseline"
printf 'console.log("electron-only");\n' > "$FIXTURE_DESKTOP/src/static/js/electron-only.js"
printf 'static/js/electron-only.js\n' > "$FIXTURE_SCRIPTS/desktop-sync-extra-baseline.txt"
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
EXTRA_BASELINE_RC=$?
expect_rc "승인된 target-only 파일 PASS" 0 "$EXTRA_BASELINE_RC"

printf 'console.log("web-copy");\n' > "$FIXTURE_FRONTEND/static/js/electron-only.js"
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
NON_DESKTOP_BASELINE_RC=$?
expect_rc "web에도 존재하는 baseline 항목 DEGRADE" 3 "$NON_DESKTOP_BASELINE_RC"
rm "$FIXTURE_FRONTEND/static/js/electron-only.js"
rm "$FIXTURE_DESKTOP/src/static/js/electron-only.js"

CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
STALE_BASELINE_RC=$?
expect_rc "실제 파일이 없는 stale baseline DEGRADE" 3 "$STALE_BASELINE_RC"
: > "$FIXTURE_SCRIPTS/desktop-sync-extra-baseline.txt"

echo "## Desktop sync check CRLF 및 점 포함 baseline 경로"
printf 'console.log("version");\n' > "$FIXTURE_DESKTOP/src/static/js/version..desktop.js"
printf 'static/js/version..desktop.js\r\n' > "$FIXTURE_SCRIPTS/desktop-sync-extra-baseline.txt"
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
CRLF_BASELINE_RC=$?
expect_rc "CRLF 및 점 포함 정상 경로 PASS" 0 "$CRLF_BASELINE_RC"
rm "$FIXTURE_DESKTOP/src/static/js/version..desktop.js"
: > "$FIXTURE_SCRIPTS/desktop-sync-extra-baseline.txt"

echo "## Desktop sync check config drift"
printf 'window.__CONFIG__ = { API_BASE_URL: "http://changed" };\n' > "$FIXTURE_FRONTEND/config/config.local.js"
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
CONFIG_DRIFT_RC=$?
expect_rc "시간 필드 외 config 변경 FAIL" 1 "$CONFIG_DRIFT_RC"
cp "$FIXTURE_FRONTEND/config/config.js" "$FIXTURE_FRONTEND/config/config.local.js"

echo "## Desktop sync check config 산출물 누락"
rm -rf "$FIXTURE_DESKTOP/src/config"
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
CONFIG_MISSING_RC=$?
expect_rc "config 산출물 누락 FAIL" 1 "$CONFIG_MISSING_RC"
(
    cd "$FIXTURE_DESKTOP" &&
    node build-scripts/sync-frontend.js --skip-backup >/dev/null 2>&1
) || exit 1

echo "## Desktop sync check 비교 오류"
chmod 000 "$FIXTURE_DESKTOP/src/templates/index.html"
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
DIFF_ERROR_RC=$?
chmod 644 "$FIXTURE_DESKTOP/src/templates/index.html"
expect_rc "I/O 오류 DEGRADE" 3 "$DIFF_ERROR_RC"

echo "## Desktop sync check drift와 비교 오류 동시 발생"
printf 'console.log("combined-drift");\n' > "$FIXTURE_FRONTEND/static/js/app.js"
chmod 000 "$FIXTURE_DESKTOP/src/templates/index.html"
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
COMBINED_ERROR_RC=$?
chmod 644 "$FIXTURE_DESKTOP/src/templates/index.html"
printf 'console.log("fixture");\n' > "$FIXTURE_FRONTEND/static/js/app.js"
expect_rc "확정 drift가 있으면 FAIL 우선" 1 "$COMBINED_ERROR_RC"

echo "## Desktop sync check 산출물 누락 비변형"
rm -rf "$FIXTURE_DESKTOP/src/static"
BEFORE_MISSING_CHECK=$(tree_digest "$FIXTURE_DESKTOP")
CODEX_PROJECT_ROOT="$FIXTURE_ROOT" bash "$FIXTURE_SCRIPTS/verify-desktop-sync.sh" >/dev/null 2>&1
MISSING_RC=$?
AFTER_MISSING_CHECK=$(tree_digest "$FIXTURE_DESKTOP")
expect_rc "산출물 누락 FAIL" 1 "$MISSING_RC"
if [ "$BEFORE_MISSING_CHECK" = "$AFTER_MISSING_CHECK" ]; then
    ok "산출물 누락 검증 후 Desktop 트리 불변"
else
    bad "산출물 누락 검증이 Desktop 트리를 생성함"
fi

echo ""
echo "== 결과: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ]
