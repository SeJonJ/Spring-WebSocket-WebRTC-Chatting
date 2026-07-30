---
id: generated-artifact-write-guard
kind: hook
runtime_bindings:
  claude: { event: PreToolUse, matcher: "Write|Edit|MultiEdit", timeout: 10 }
  codex: { event: PreToolUse, matcher: "apply_patch", timeout: 10 }
---
## intent
생성 산출물(.claude/.codex 의 agents/hooks/skills) 직접수정을 결정론적으로 block 하고
spec(docs/sage_harness)으로 redirect 한다. SSOT 모델의 잠금장치 — 없으면 "항상 spec을 고친다"가
권고에 그치고 AI가 개발 중 산출물을 곁다리로 고쳐 조용한 drift가 생긴다 (설계 §5.6).

## runtime_bindings
- claude: { event: PreToolUse, matcher: "Write|Edit|MultiEdit" }
- codex:  { event: PreToolUse, matcher: "apply_patch" }
- on_fail: block            # adapter가 exit 2(stderr) / JSON 으로 매핑

## canonical
scripts/sage_harness/hooks/generated-artifact-write-guard.sh
- 입력: --path | $SAGE_GUARD_PATH | stdin JSON(tool_input.file_path)
- 핵심 알고리즘 = "경로가 생성 산출물인가" 분류 (런타임별 입력 추출은 얇은 어댑터)

## enforcement
- block(exit 2): `*.claude/{agents,hooks,skills}/*`, `*.codex/{agents,hooks,skills}/*`,
  repo의 `.mcp.json`, CORE framework 문서(`AGENT_GUIDE.md`, `CLAUDE.md`, `CODEX.md`, `AGENTS.md`)
- pass(exit 0): 위 소유 경계 밖의 경로. 특히 `docs/sage_harness/**`·`scripts/sage_harness/**` 소스
- 경로 없음/파싱 실패 → pass (가드 대상 아님, 조용한 오작동 방지)
- 예외 처리 불필요: `sage generate` CLI 는 편집도구(Write/Edit/apply_patch)를 거치지 않으므로
  애초에 이 PreToolUse 가드에 걸리지 않는다 (설계 §5.6 G3)

## CORE 부트스트랩 렌더 차단 + eligibility-aware 안내 (exit 2)
CORE hand-shipped 렌더(CORE skill·로스터 에이전트)도 다른 산출물과 동일하게 block 한다. 과거엔
spec→generate 산출물이 아니라는 이유로 면제했으나, 그러면 CORE 렌더 직접수정이 무방비였고
`sage install --force` 가 그 수정을 조용히 덮어썼다(첫 실 사이클 실증에서 드러난 갭).

프로젝트 로컬 overlay 경로는 executable eligibility가 입증된 자산에만 안내한다. 현재 대상은
양 host의 non-gate 워커 `implementer-a`/`implementer-b`와, FB23 로 재분류된 gate-bearing 자산
`leader`/`reviewer`(agents)·`sage-cycle`/`sage-plan`/`sage-review`/`sage-team`(skills)이며,
canonical lowercase overlay 경로로 redirect 한다(`core_overlay_hint`; skill overlay id 는 skill
디렉터리명). 이들은 게이트를 자산-불read 결정론 오라클이 floor 하므로 overlay 물리 합성이 안전하다.
남은 `qa`/`convention-checker`(agents)·`sage-init`/`sage-asset`/`sage-asset-override`/
`sage-profile-modify`(skills)는 독립 oracle이 없어 현재 overlay 비지원임을 안내한다(`is_blocked_core_render`).
따라서 보존되지만 합성할 수 없는 overlay 파일 생성을 유도하지 않는다.

codex CORE skill은 선택 scope가 global이면 `$CODEX_HOME/skills`, project-local이면 repo `.codex/skills/`에
설치된다. project-local CORE 이름은 일반 생성 skill이 아니라 install-owned CORE render로 식별해 직접수정을
block하고, 같은 `--skill-scope project-local --force` 재설치 또는 지원되는 overlay 흐름으로 안내한다.
비-CORE `.codex/skills/`는 기존대로 일반 프로젝트 skill 산출물로 block(spec→generate 안내).
비-CORE 렌더는 기존대로 `docs/sage_harness/<kind>s/<id>.md` spec→generate redirect. eligible 오버레이 저작은
`/sage-asset-override` 스킬이 현재 eligible non-gate 자산만 안내하며, 게이트 완화는 materialization
preflight와 `sage validate --strict`가 hard-fail한다.

## AGENT_GUIDE.md (CORE 프레임워크 문서) 차단 + project-profile redirect (exit 2)
`AGENT_GUIDE.md`(루트·하위경로)도 CORE 렌더이자 `core_renders` 앵커 대상이라 `sage install --force` 가
덮어쓴다. 직접수정은 업그레이드에 조용히 사라지고, 렌더에 overlay-read 지시를 재주입하는 변조 경로이기도
하다(`sage validate` L2 가 앵커 불일치로 탐지). framework overlay는 독립 gate oracle이 없어 차단한다.
프로젝트 값은 `sage/project-profile.yaml`, 규칙은 conventions/critical-domain/project-local 문서가 소유한다.

## scope 메모 (v1)
- 가드 범위 = agents/hooks/skills 디렉토리 (설계 §5.6 다이어그램 명시 범위)
- settings.json / hooks.json(등록 산출물) 가드는 부트스트랩 중 직접편집 필요성 때문에 v1 보류 — 후속 결정

## tests
scripts/sage_harness/hooks/tests/ (cases.tsv: path → expected exit)

## mode (forward-compat)
- v1 SAGE-mode = block (spec-SSOT 존재 전제)
- spec 미존재 환경에 선적용 시 = warn-mode 미러 drift 탐지로 degrade (profile `guard.mode`)
