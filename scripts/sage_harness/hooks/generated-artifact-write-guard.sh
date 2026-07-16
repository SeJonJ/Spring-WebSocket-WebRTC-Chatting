#!/usr/bin/env bash
# SAGE generated-artifact write guard — canonical algorithm
# spec: docs/sage_harness/hooks/generated-artifact-write-guard.md
#
# 목적: 생성 산출물(.claude/.codex 의 agents/hooks/skills) 직접수정을 block 하고 spec 으로 redirect.
#       산출물 직접수정을 막아야 "항상 spec 을 고친다"가 권고가 아닌 강제가 된다 (설계 §5.6).
#
# 입력 우선순위:
#   1) --path <p>            (테스트/직접호출, 단일)
#   2) $SAGE_GUARD_PATH       (테스트/직접호출, 단일)
#   3) stdin JSON            (런타임 PreToolUse 어댑터)
#      - Claude: tool_input.file_path / path
#      - Codex apply_patch: tool_input.command 본문의 *** Add/Update/Delete File:, *** Move to: 다중 target
#   하나라도 guarded path 면 block (audit 1회차 P0: Codex apply_patch 우회 차단).
#
# 종료코드: 0 = 통과, 2 = block (stderr 메시지가 모델에 전달됨)
set -euo pipefail

extract_paths_from_stdin() {
  # Claude file_path + Codex apply_patch command 본문 다중 target 모두 추출(줄단위 출력).
  # 프로그램은 -c 인자로 주고 stdin 은 JSON 으로 유지(heredoc-as-program 회피).
  python3 -c '
import sys, json, re
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = (d.get("tool_input") or {}) if isinstance(d, dict) else {}
out = []
fp = ti.get("file_path") or ti.get("path")
if fp:
    out.append(fp)
cmd = ti.get("command") or ""
for line in cmd.splitlines():
    m = re.match(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", line) or re.match(r"^\*\*\* Move to: (.+)$", line)
    if m:
        out.append(m.group(1).strip())
for p in out:
    print(p)
' 2>/dev/null || true
}

# guarded = .claude/.codex 의 agents/hooks/skills 산출물 + .mcp.json(SAGE 소유 생성물). (source/spec 경로는 여기 매칭 안 됨 → 자연 통과)
# audit 4회차 P1: 소문자 정규화로 대소문자 우회(.CODEX 등, macOS case-insensitive fs) 차단.
# (symlink 기반 우회는 §5.6 원칙상 범위 밖 — adversarial 은 OS 권한/CI 영역. 본 가드는 drift 방지용)
# .mcp.json: claude MCP 생성물(SAGE 전적 소유, repo 루트) → 직접수정 차단. (.codex/config.toml 은 managed-block 만
#  소유하고 비-MCP 설정 공존이라 파일 통째 가드 안 함 — staleness+소유권 검사로 보호. MCP plan §2.3 비대칭.)
is_guarded() {
  local p; p="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  # framework override는 CORE 렌더의 정식 저작 경로다. 렌더와 basename이 같으므로
  # 일반 framework 문서 패턴보다 먼저 예외 처리하지 않으면 redirect 대상 자체를 차단한다.
  case "$p" in
    sage/asset_overrides/framework/*.md|*/sage/asset_overrides/framework/*.md) return 1 ;;
  esac
  # CORE 부트스트랩 렌더(install hand-ship: CORE skill·로스터 에이전트)도 이제 가드한다.
  #   과거엔 spec→generate 산출물이 아니라는 이유로 면제했으나, 그러면 CORE 렌더 직접수정이 무방비였고
  #   sage install --force 가 그 수정을 조용히 덮어썼다. 이제 sage/asset_overrides/** (install-safe overlay)가
  #   프로젝트 로컬 커스터마이즈의 정식 경로이므로, CORE 렌더도 가드하고 block() 이 overlay 로 redirect 한다.
  #   (id→overlay 매핑은 core_overlay_hint. hook_runtime.make_rel 가 절대경로를 root 상대로 먼저 정규화한다.)
  case "$p" in
    *.claude/agents/*|*.claude/hooks/*|*.claude/skills/*) return 0 ;;
    *.codex/agents/*|*.codex/hooks/*|*.codex/skills/*)    return 0 ;;
    .mcp.json|*/.mcp.json)                                 return 0 ;;
    # AGENT_GUIDE.md 도 CORE 렌더(sage install --force 가 덮어씀)이자 core_renders 앵커 대상.
    #   직접 편집은 업그레이드에 조용히 사라지고, overlay-read 재주입 변조 경로이기도 하다. framework
    #   문서는 framework override 로 프로젝트 고유 규칙을 보존한다.
    agent_guide.md|*/agent_guide.md|claude.md|*/claude.md|codex.md|*/codex.md|agents.md|*/agents.md) return 0 ;;
  esac
  return 1
}

# CORE 프레임워크 문서면 return 0. block() 이 framework overlay 로 안내한다.
is_framework_doc() {
  local p; p="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$p" in
    agent_guide.md|*/agent_guide.md|claude.md|*/claude.md|codex.md|*/codex.md|agents.md|*/agents.md) return 0 ;;
  esac
  return 1
}

# CORE 부트스트랩 렌더면 프로젝트 로컬 overlay 경로를 출력(return 0), 아니면 return 1.
#   block() 안내 전용 — is_guarded 판정과 무관. 대상 = 과거 가드 면제였던 CORE 렌더와 동일:
#   claude CORE skill 렌더 + 양 host 로스터 에이전트(codex CORE skill 은 전역설치라 repo 경로로 안 옴).
core_overlay_hint() {
  local p; p="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$p" in
    *.claude/skills/sage-init/*|*.claude/skills/sage-cycle/*|*.claude/skills/sage-plan/*|*.claude/skills/sage-team/*|*.claude/skills/sage-review/*|*.claude/skills/sage-asset/*|*.claude/skills/sage-profile-modify/*|*.claude/skills/sage-asset-override/*)
      printf 'sage/asset_overrides/skills/%s.md' "$(basename "$(dirname "$1")")"; return 0 ;;
    *.claude/agents/leader.md|*.claude/agents/implementer-a.md|*.claude/agents/implementer-b.md|*.claude/agents/qa.md|*.claude/agents/reviewer.md|*.claude/agents/convention-checker.md|*.codex/agents/leader.md|*.codex/agents/implementer-a.md|*.codex/agents/implementer-b.md|*.codex/agents/qa.md|*.codex/agents/reviewer.md|*.codex/agents/convention-checker.md)
      printf 'sage/asset_overrides/agents/%s' "$(basename "$1")"; return 0 ;;
  esac
  return 1
}

block() {
  # printf 사용(heredoc temp 파일 회피 — 제한 환경에서도 exit 2 보장, audit 5회차 P1).
  if is_framework_doc "$1"; then
    local framework_overlay="sage/asset_overrides/framework/$(basename "$1")"
    printf '%s\n' \
      "⛔ SAGE write guard: '$1' 는 CORE 프레임워크 문서입니다. 직접수정 금지 (sage install --force 가 덮어씀)." \
      "→ 프로젝트 값은 'sage/project-profile.yaml', 문서 고유 prose는 '$framework_overlay' 에 작성하세요." \
      "→ framework override는 domain_refs frontmatter 계약과 'sage validate'를 통과해야 합니다." >&2
    exit 2
  fi
  local overlay=""; overlay="$(core_overlay_hint "$1")" || true
  if [ -n "$overlay" ]; then
    printf '%s\n' \
      "⛔ SAGE write guard: '$1' 는 CORE 부트스트랩 렌더입니다. 직접수정 금지." \
      "→ 프로젝트 로컬 커스터마이즈는 '$overlay' 에 작성하세요 (sage install --force 에도 보존)." \
      "→ 작성 도움: '/sage-asset-override' (게이트 완화 여부까지 점검)." >&2
  else
    printf '%s\n' \
      "⛔ SAGE write guard: '$1' 는 생성 산출물입니다. 직접수정 금지." \
      "→ docs/sage_harness/<kind>s/<id>.md (spec) 을 고치고 'sage generate' 를 쓰세요." \
      "→ 이미 수정한 diff 라면 'sage absorb --kind <k> --id <id> --from-blocked-diff' 로 spec patch 로 변환하세요." \
      "(sage generate CLI 는 편집도구를 안 거치므로 이 가드에 걸리지 않습니다.)" >&2
  fi
  exit 2
}

# 검사 대상 경로 수집(단일 또는 다중)
declare -a TARGETS=()
if [[ "${1:-}" == "--path" ]]; then
  TARGETS+=("${2:-}")
elif [[ -n "${SAGE_GUARD_PATH:-}" ]]; then
  TARGETS+=("$SAGE_GUARD_PATH")
elif [[ ! -t 0 ]]; then
  while IFS= read -r line; do
    [[ -n "$line" ]] && TARGETS+=("$line")
  done < <(extract_paths_from_stdin)
fi

# 경로 없음 → 가드 대상 아님
[[ ${#TARGETS[@]} -eq 0 ]] && exit 0

# guarded 판정 우선(P1: source-allow 선판정 제거). guarded path 면 즉시 block.
# docs/sage_harness·scripts/sage_harness 같은 소스는 guarded 패턴(.claude/.codex/{agents,hooks,skills})에
# 애초에 매칭되지 않으므로 자연 통과한다. (.codex/hooks/scripts/... 같은 산출물 하위는 guarded 가 먼저 걸림)
for t in "${TARGETS[@]}"; do
  norm="${t#./}"
  if is_guarded "$norm"; then
    block "$t"
  fi
done

exit 0
