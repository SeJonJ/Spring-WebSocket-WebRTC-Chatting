"""ChatForYou component implementation-doc gate — pure decision core.

Root 03 문서 검사는 CORE pre-phase4-checklist-gate 가 계속 소유한다. 이 core 는 ChatForYou
고유 규칙만 본다 — Phase 04 진입 전에 backend/frontend 각각이 영향을 받는지 00 base-plan 이
선언했는지, 영향받는 컴포넌트의 구현 문서가 존재하고 완료됐는지.

filesystem/clock/environment 에 직접 접근하지 않는다. 읽을 경로는 plan_reads 가 지목하고
런타임이 읽어 snapshot['files'] 로 넘긴다.
"""

import posixpath
import re

CONTRACT_VERSION = "1"

GATE_MARKER = "ChatForYou-Component-Doc-Gate"
GATE_MARKER_VERSION = "v1"

BASE_PLAN_DIR = "plan_docs/00-base_plan"
PHASE4_DIR = "plan_docs/04-analyze"

# rollout 스냅샷은 로직이 아니라 데이터다. 소스에 두지 않는 실무적 이유가 하나 더 있다 —
# 사이클 stem 은 프로젝트 도메인 어휘를 그대로 쓰므로 게이트 소스에 나열하면 risk 분류의
# content keyword 와 매칭돼 이 파일 자신의 위험도가 올라간다.
LEGACY_CYCLES_FILE = "sage/chatforyou-legacy-cycles.txt"

# 선언 이름 → 그 컴포넌트가 REQUIRED 일 때 있어야 하는 구현 문서 디렉터리.
COMPONENTS = (
    ("Backend", "springboot-backend/plan_docs"),
    ("Frontend", "nodejs-frontend/plan_docs"),
)

# stem 은 경로 basename 이자 다시 경로로 조립되는 값이라 구분자·상대 참조가 섞이면 안 된다.
_SAFE_STEM = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}\Z")
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_UNCHECKED_BOX = re.compile(r"^\s*[-*+]\s+\[ \]\s*(.*)$")
_ANY_COMPONENT = re.compile(r"^Component-([A-Za-z0-9_-]+)\s*:")

_KNOWN_LABELS = frozenset(label for label, _ in COMPONENTS)

_MAX_EVIDENCE_LINES = 10


def _plain_lines(text):
    """fenced code block 밖의 (줄번호, 원문) 만 흘린다.

    코드 예시 안의 선언·체크박스가 판정에 쓰이면 문서가 자기 문법 설명 때문에 차단된다.
    """
    in_fence = False
    fence_char = ""
    fence_len = 0
    for number, raw in enumerate((text or "").splitlines(), start=1):
        marker = _FENCE.match(raw)
        if marker:
            token = marker.group(1)
            if not in_fence:
                in_fence, fence_char, fence_len = True, token[0], len(token)
                continue
            # CommonMark: closing fence 는 info string 을 가질 수 없다. 이걸 안 보면
            # ```text 안의 ```python 이 fence 를 닫아버려 그 뒤 코드 예시가 본문 선언으로 읽힌다.
            if (token[0] == fence_char and len(token) >= fence_len
                    and not raw[marker.end():].strip()):
                in_fence = False
            continue
        if not in_fence:
            yield number, raw


def _legacy_stems(snapshot):
    """allowlist 파일 → stem 집합. 파일이 없으면 빈 집합(=아무것도 면제하지 않음).

    없을 때 전면 skip 이 아니라 전면 검사인 이유는 파일 삭제가 곧 게이트 해제가 되면 안 되기 때문이다.
    """
    text = ((snapshot or {}).get("files") or {}).get(LEGACY_CYCLES_FILE)
    stems = set()
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            stems.add(line)
    return stems


def _stem_of(path):
    name = posixpath.basename((path or "").replace("\\", "/"))
    if not name.lower().endswith(".md"):
        return None
    name = name[:-3]
    return name if _SAFE_STEM.match(name) else None


def _phase4_stem(event):
    """이 이벤트가 건드리는 Phase 04 문서의 stem. 없거나 둘 이상이면 None(=판정 안 함).

    둘 이상을 None 으로 두는 이유는 어느 사이클로 판정할지 고를 근거가 없기 때문이다.
    """
    stems = set()
    for change in (event or {}).get("changes") or []:
        path = ((change or {}).get("path") or "").replace("\\", "/")
        if posixpath.dirname(path) != PHASE4_DIR:
            continue
        stem = _stem_of(path)
        if stem:
            stems.add(stem)
    return stems.pop() if len(stems) == 1 else None


def _base_plan_path(stem):
    return BASE_PLAN_DIR + "/" + stem + ".md"


def _component_doc_path(directory, stem):
    return directory + "/" + stem + ".md"


def plan_reads(event, profile=None):
    """판정에 필요한 정확 경로만 지목한다.

    legacy 여부는 snapshot 을 받아야 알 수 있으므로 allowlist 파일을 항상 포함한다.
    리터럴 경로는 자기 자신만 매칭하는 glob 이라 prefix 유사 파일이나 최근 파일 fallback 이
    끼어들 여지가 없다. 경로 안전(절대·상대탈출·symlink·root 이탈)은 런타임이 검사한다.
    """
    stem = _phase4_stem(event)
    if stem is None:
        return {"globs": []}
    globs = [LEGACY_CYCLES_FILE, _base_plan_path(stem)]
    globs.extend(_component_doc_path(directory, stem) for _, directory in COMPONENTS)
    return {"globs": globs}


def _marker_error(lines):
    prefix = GATE_MARKER + ":"
    found = [line.strip() for _, line in lines if line.strip().startswith(prefix)]
    if not found:
        return "missing_gate_marker"
    if len(found) > 1:
        return "duplicate_gate_marker"
    if found[0][len(prefix):].strip() != GATE_MARKER_VERSION:
        return "invalid_component_status"
    return None


def _declaration(lines, label):
    """Component-<label> 선언 1건 → (status, reason, error_key)."""
    prefix = "Component-" + label + ":"
    found = [line.strip() for _, line in lines if line.strip().startswith(prefix)]
    if not found:
        return None, None, "missing_component_declaration"
    if len(found) > 1:
        return None, None, "duplicate_component_declaration"
    body = found[0][len(prefix):].strip()
    if body == "REQUIRED":
        return "REQUIRED", None, None
    if body == "N/A":
        return None, None, "empty_na_reason"
    if body.startswith("N/A:"):
        reason = body[len("N/A:"):].strip()
        if not reason:
            return None, None, "empty_na_reason"
        return "N/A", reason, None
    return None, None, "invalid_component_status"


def _unknown_component_labels(lines):
    """본문의 Component-* 선언 중 이 프로젝트가 모르는 이름들.

    Backend/Frontend 만 조회하면 Component-Desktop 같은 선언이 조용히 무시돼,
    작성자는 선언했다고 믿는데 게이트는 아무것도 검사하지 않는 상태가 된다.
    """
    seen = []
    for _, line in lines:
        match = _ANY_COMPONENT.match(line.strip())
        if match and match.group(1) not in _KNOWN_LABELS:
            seen.append(match.group(1))
    return seen


def _conflicting_paths(event, stem):
    """같은 이벤트가 Phase 04 와 함께 건드리는 00/컴포넌트 문서 경로.

    snapshot 은 쓰기 **전** 디스크 상태라, 한 번의 patch 로 00 을 무효화하면서 04 를 쓰면
    아직 유효한 00 으로 판정돼 게이트가 통과한다. 그 조합은 판정할 수 없으므로 거부한다.
    """
    governed = {_base_plan_path(stem)}
    governed.update(_component_doc_path(directory, stem) for _, directory in COMPONENTS)
    hit = []
    for change in (event or {}).get("changes") or []:
        path = ((change or {}).get("path") or "").replace("\\", "/")
        if path in governed:
            hit.append(path)
    return sorted(set(hit))


def _unchecked(text):
    result = []
    for number, line in _plain_lines(text):
        match = _UNCHECKED_BOX.match(line)
        if match:
            result.append((number, match.group(1).strip()))
    return result


def _block(key, stem, detail):
    body = "\n".join("  " + line for line in detail)
    header = "[chatforyou-dual-implementation-doc-gate/" + key + "] cycle=" + stem
    return {"status": "block", "exit_code": 2, "message": header + "\n" + body}


def decide(event, profile, snapshot):
    stem = _phase4_stem(event)
    if stem is None or stem in _legacy_stems(snapshot):
        return {"status": "skip", "exit_code": 0, "message": ""}

    conflicting = _conflicting_paths(event, stem)
    if conflicting:
        return _block("mixed_change_scope", stem, [
            "Phase 04 와 게이트 판정 대상 문서를 한 번에 바꾸면 판정할 수 없습니다.",
            "함께 변경된 문서: " + ", ".join(conflicting),
            "문서를 먼저 확정한 뒤 Phase 04 를 별도 변경으로 작성하세요.",
        ])

    files = (snapshot or {}).get("files") or {}
    base_path = _base_plan_path(stem)
    base_text = files.get(base_path)
    if base_text is None:
        return _block("missing_base_plan", stem, [
            "Phase 04 를 쓰기 전에 00 base-plan 이 있어야 합니다: " + base_path,
            "신규 사이클은 00 에서 컴포넌트 영향을 선언해야 합니다.",
        ])

    lines = list(_plain_lines(base_text))
    marker_error = _marker_error(lines)
    if marker_error:
        return _block(marker_error, stem, [
            base_path + " 에 " + GATE_MARKER + ": " + GATE_MARKER_VERSION
            + " 선언이 정확히 한 번 필요합니다.",
        ])

    unknown = _unknown_component_labels(lines)
    if unknown:
        return _block("unknown_component_declaration", stem, [
            base_path + " 에 이 프로젝트가 모르는 컴포넌트 선언이 있습니다: "
            + ", ".join("Component-" + name for name in unknown),
            "허용 컴포넌트: " + ", ".join(sorted(_KNOWN_LABELS)),
        ])

    required, waived = [], []
    for label, directory in COMPONENTS:
        status, reason, error_key = _declaration(lines, label)
        if error_key:
            return _block(error_key, stem, [
                base_path + " 의 Component-" + label + " 선언을 확인하세요.",
                "허용 형식: Component-" + label + ": REQUIRED"
                + " 또는 Component-" + label + ": N/A: <사유>",
            ])
        if status == "REQUIRED":
            required.append((label, _component_doc_path(directory, stem)))
        else:
            waived.append(label + "=N/A(" + reason + ")")

    for label, doc_path in required:
        text = files.get(doc_path)
        if text is None:
            return _block("missing_component_doc", stem, [
                label + " 이 REQUIRED 인데 구현 문서가 없습니다: " + doc_path,
                "영향이 없다면 " + base_path + " 에서 Component-" + label
                + ": N/A: <사유> 로 바꾸세요.",
            ])
        unchecked = _unchecked(text)
        if unchecked:
            detail = [label + " 구현 문서에 미완료 항목 " + str(len(unchecked))
                      + "건: " + doc_path]
            detail.extend("  L" + str(number) + ": " + body
                          for number, body in unchecked[:_MAX_EVIDENCE_LINES])
            if len(unchecked) > _MAX_EVIDENCE_LINES:
                detail.append("... 외 " + str(len(unchecked) - _MAX_EVIDENCE_LINES) + "건")
            return _block("unchecked_component_doc", stem, detail)

    summary = ", ".join([label + "=REQUIRED" for label, _ in required] + waived)
    return {"status": "ok", "exit_code": 0,
            "message": "[chatforyou-dual-implementation-doc-gate/gate_ok] cycle="
                       + stem + " | " + summary}
