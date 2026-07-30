"""sage-feedback 마커 원시 로직 (§10-a-C) — hook 코어와 CLI 의 단일 출처.

hook 코어는 `sage` 패키지에 의존하지 않는다(프로젝트가 자기 hook 코어를 소유하는 모델).
그래서 마커 정규식과 해소 판정은 여기 runtime 트리에 두고, `sage/feedback.py`(CLI)가
이 모듈을 로드해 쓴다 — acceptance_waiver 와 같은 구조. 정규식이 두 곳에 복제되면
게이트와 CLI 가 서로 다른 마커를 보게 되므로 반드시 단일 출처를 유지한다.

이 모듈은 **순수**하다(문자열 in / 판정 out). 파일 읽기는 어댑터가 한다.
"""
import re

# (!?)  = 심각도. `!` 접두 = 차단성, 없으면 advisory.
# 두 토큰을 따로 검색하면 `sage-feedback` 이 `!sage-feedback` 의 부분문자열이라
# 차단성 마커가 advisory 검색에도 걸린다. optional 그룹으로 한 번에 뽑는다.
MARKER_RE = re.compile(r"(!?)sage-feedback\s*::[ \t]*(.*)")

# 블록 주석 종료자. 주석 문법을 해석하진 않지만(언어 무관성 유지) 마커 본문 끝에 딸려온
# 종료자는 기록·표시에 노이즈라 잘라낸다. 판정에는 영향이 없다.
_TRAILING_COMMENT_ENDS = ("-->", "*/", "--}}", "#}", "*)", '"""', "'''")


def clean_text(value):
    value = (value or "").strip()
    for end in _TRAILING_COMMENT_ENDS:
        if value.endswith(end):
            value = value[: -len(end)].rstrip()
            break
    return value


def scan_text(text, path="<text>"):
    """문자열에서 마커를 뽑는다 → [{path, line, blocking, text}]."""
    found = []
    for number, raw in enumerate((text or "").splitlines(), start=1):
        match = MARKER_RE.search(raw)
        if match:
            found.append({"path": path, "line": number,
                          "blocking": match.group(1) == "!",
                          "text": clean_text(match.group(2))})
    return found


def count_blocking(text):
    return sum(1 for m in scan_text(text or "") if m["blocking"])


def has_blocking(text):
    return count_blocking(text) > 0


def resolves_blocking(change, on_disk_text):
    """이 쓰기가 차단성 마커를 **전부** 해소하는가?

    게이트 규칙은 "마커 있는 파일은 못 고침" 이 아니라 **"고친 뒤에도 마커가 남는가"** 다.
    전자로 만들면 마커를 지우려는 편집까지 막혀서 영원히 해소할 수 없다(자기차단).

    - Write(full_content): 새 전체 내용에 차단성 마커가 없으면 해소.
    - Edit: 지워지는 조각이 **파일에 있는 차단성 마커를 남김없이** 담고, 새 조각이 새 마커를
      들이지 않을 때만 해소. "지워지는 쪽에 하나라도 있으면 통과" 로 두면 마커 3개 중 1개만
      지우는 편집이 통과해 나머지 2개 위에 새 구현을 쌓게 된다(우회).

    개수 비교가 성립하는 근거: `removed_content` 는 파일에서 실제로 사라지는 조각(들)이라
    거기 담긴 차단성 마커는 파일 안 서로 다른 실물이다. 따라서 removed 개수 ≥ 파일 개수는
    "전부 지워진다" 와 같다. MultiEdit 는 조각을 개행으로 이어 붙이므로 이어 붙이는 과정에서
    없던 마커가 생기지도 않는다(마커는 한 줄 안에서만 성립).
    """
    remaining = count_blocking(on_disk_text)
    if remaining == 0:
        return True                       # 애초에 차단할 마커가 없음
    if change.get("full_content"):
        return not has_blocking(change.get("content") or "")
    if has_blocking(change.get("content") or ""):
        return False                      # 새 조각이 마커를 (다시) 심는다
    return count_blocking(change.get("removed_content") or "") >= remaining


def blocking_markers(text, path):
    return [m for m in scan_text(text or "", path) if m["blocking"]]
