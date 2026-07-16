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
- block(exit 2): 경로가 `*.claude/{agents,hooks,skills}/*` 또는 `*.codex/{agents,hooks,skills}/*`
- pass(exit 0): 그 외 전부. 특히 `docs/sage_harness/**`·`scripts/sage_harness/**`(소스)는 우선 허용
- 경로 없음/파싱 실패 → pass (가드 대상 아님, 조용한 오작동 방지)
- 예외 처리 불필요: `sage generate` CLI 는 편집도구(Write/Edit/apply_patch)를 거치지 않으므로
  애초에 이 PreToolUse 가드에 걸리지 않는다 (설계 §5.6 G3)

## CORE 부트스트랩 렌더 차단 + overlay redirect (exit 2)
CORE hand-shipped 렌더(CORE skill·로스터 에이전트)도 다른 산출물과 동일하게 block 한다. 과거엔
spec→generate 산출물이 아니라는 이유로 면제했으나, 그러면 CORE 렌더 직접수정이 무방비였고
`sage install --force` 가 그 수정을 조용히 덮어썼다(첫 실 사이클 실증에서 드러난 갭).

이제 프로젝트 로컬 커스터마이즈의 정식 경로는 `sage/asset_overrides/**`(install 미ship, `--force`
생존)이며, block 메시지가 CORE 경로면 그 overlay 경로로 redirect 한다(`core_overlay_hint`). redirect
대상:
- `*.claude/skills/{sage-init,sage-cycle,sage-plan,sage-team,sage-review,sage-asset,sage-profile-modify,sage-asset-override}/*`
  → `sage/asset_overrides/skills/<id>.md` (CORE skill 렌더, claude)
- `*.claude/agents/{leader,implementer-a,implementer-b,qa,reviewer,convention-checker}.md`
  → `sage/asset_overrides/agents/<id>.md` (CORE 로스터 렌더, claude)
- `*.codex/agents/{...}.md` → 동일 (CORE 로스터 렌더, codex)

codex CORE skill 은 전역 `$CODEX_HOME/skills` 설치라 repo 경로로 가드에 오지 않는다. repo
`.codex/skills/` 는 프로젝트 skill 영역이라 CORE 이름이어도 일반 산출물로 block(spec→generate 안내).
비-CORE 렌더는 기존대로 `docs/sage_harness/<kind>s/<id>.md` spec→generate redirect. 오버레이 저작은
`/sage-asset-override` 스킬이 안내하며, 게이트 완화 여부는 `sage validate` overlay 린트가 표면화한다.

## AGENT_GUIDE.md (CORE 프레임워크 문서) 차단 + project-profile redirect (exit 2)
`AGENT_GUIDE.md`(루트·하위경로)도 CORE 렌더이자 `core_renders` 앵커 대상이라 `sage install --force` 가
덮어쓴다. 직접수정은 업그레이드에 조용히 사라지고, 렌더에 overlay-read 지시를 재주입하는 변조 경로이기도
하다(`sage validate` L2 가 앵커 불일치로 탐지). framework 문서는
`sage/asset_overrides/framework/<파일명>`으로 redirect하며, 값은 `sage/project-profile.yaml`, 문서 prose는
framework override가 소유한다. override는 `domain_refs` 계약과 validate를 통과해야 한다.

## scope 메모 (v1)
- 가드 범위 = agents/hooks/skills 디렉토리 (설계 §5.6 다이어그램 명시 범위)
- settings.json / hooks.json(등록 산출물) 가드는 부트스트랩 중 직접편집 필요성 때문에 v1 보류 — 후속 결정

## tests
scripts/sage_harness/hooks/tests/ (cases.tsv: path → expected exit)

## mode (forward-compat)
- v1 SAGE-mode = block (spec-SSOT 존재 전제)
- spec 미존재 환경에 선적용 시 = warn-mode 미러 drift 탐지로 degrade (profile `guard.mode`)
