## Loop A 프롬프트 보강 (project-local)

`chatforyou_dual_implementation_doc_gate` 사이클(2026-08-02~08, 1~4차 리뷰)에서 반복 관찰된
패턴에 대한 보강이다: REWORK가 지적된 사례 하나만 닫고 그 사례가 속한 부류를 안 닫아서,
같은 결함이 다음 라운드에 형태만 바꿔 재지적되는 일이 4연속(F1→G3, F4→G2, G3→H2, H3→S1)
있었다. CORE의 FIND/REFUTE/TRIAGE/REWORK 골격은 그대로 두고, 아래 세 지점만 추가한다.

### REWORK — 부류 단위 수정 (CORE §REWORK 에 추가)

CORE `[TASK]` 뒤에 다음을 추가로 지킨다:

- **[CLASS]** 수정은 지적된 입력이 아니라 그 입력이 속한 **부류**를 닫아야 한다.
  1. 부류 경계를 한 줄로 적는다(예: "경로 case 비교" 이지 "이 파일 하나의 경로"가 아니다).
  2. 회귀는 부류의 양 끝을 덮는다 — 집합이면 증가/감소 양방향, 판정이면 관할/충돌 양쪽처럼
     대칭되는 두 축을 최소한으로 삼는다.
  3. 제출 전 **수정하기 전 코드로 그 회귀를 돌려 실제로 실패하는지** 확인하고 결과를
     `[OUTPUT]` 표에 한 줄로 보고한다 — 실패하지 않는 회귀는 아무것도 고정하지 않은 것이므로
     그 자체가 finding 미해결로 취급된다.

### TRIAGE — severity 분기 (CORE §TRIAGE 출력에 필드 추가)

CORE 는 scope(within_design/architecture_change)만 분기한다. 여기에 severity 분기를 더한다
— **REFUTE 를 생략하거나 finding 을 폐기하는 것이 아니라**, TRIAGE 이후 REWORK 로 보낼지를
가르는 추가 분기다. survivor 는 여전히 전부 `[OUTPUT]` 표에 남고 05 문서에 기록된다.

- `severity` 가 `profile.pdca.review_loop.severity_block`(예: `[P0, P1]`) 에 **없으면**
  기본 `disposition` 은 **`accept`** 다 — 05 잔여 위험 절에 근거와 함께 기록하고 REWORK 로
  보내지 않는다.
- `disposition: rework` 로 올리려면 (a) 한 줄 수정으로 끝나거나 (b) 리더가 명시 승인해야
  한다. 승인 근거는 이 자산의 **위협 모델**(상대가 누구인가)을 한 줄로 명시하는 것으로 한다.
- `[OUTPUT]` 에 `severity`(finding 원본에서 그대로 가져옴)와 `disposition: rework|accept`
  두 필드를 추가한다: `{ "finding_id":"{id}", "scope":"...", "severity":"P0|P1|P2|P3",
  "disposition":"rework|accept", "reason":"..." }`

### FIND (lifecycle/correctness 렌즈) — 04 의 미검증 주장 탐지 (CORE §FIND 에 추가)

lifecycle·correctness 렌즈는 위 두 렌즈에 한해 다음을 추가로 본다:

- `04-analyze` 의 커버리지 공백 절을 읽고, 각 항목의 근거가 **실행 증거**(테스트/로그/실측)
  인지 **추정**(서술만 있고 검증 없음)인지 판별한다.
- 추정이면서 그 항목이 게이트 판정(risk 등급, 통과/차단)에 실제로 영향을 주면, 그 자체를
  하나의 finding 으로 낸다 — `claim`: "04 §X 의 '위험 낮음' 주장이 실행 증거 없이 게이트
  판정에 쓰인다". 저자가 갭을 찾아놓고 크기를 잘못 매기는 것이 갭을 아예 못 찾는 것보다
  흔하다.
