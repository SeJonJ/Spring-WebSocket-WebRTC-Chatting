"""cycle_state — 사이클 선언 파일(`<root>/.sage/cycle.json`)의 단일소스.

`sage cycle` CLI 와 게이트가 같은 코드를 공유한다. env(`SAGE_CYCLE_STEM`)로만 선언하던 통로는
셸이 사이클보다 오래 살고, 자식 프로세스를 전부 따라가고, 조회할 방법이 없었다. 파일로 옮기면
그 셋이 한꺼번에 해소되는 대신 새 성질이 셋 생긴다 — 세션을 넘겨 살아남고, 편집 도구로 심을 수
있고, 손상될 수 있다. 각각 완결 사이클 차단(gate core)·write guard·아래 degrade 로 받는다.

**저장 위치를 탐색하지 않는다.** root 가 정본이고 선언은 항상 그 바로 아래다. 상위로 올라가며
찾으면 파일이 `install` 이 `.gitignore` 를 쓴 앵커 밖에 놓여 커밋 대상이 된다.

root 해석은 CLI 전용이다. 게이트는 자기 root 를 이미 알고 들어오므로 `read_declaration` 만 쓴다.
둘이 어긋날 수 있다는 사실은 설계의 알려진 한계이고, `sage cycle use` 가 절대경로를 찍어 보이게 한다.
"""
import json
import os
import sys
import tempfile
import time

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HOOKS_DIR not in sys.path:
    sys.path.insert(0, HOOKS_DIR)
import cycle_binding

# "여기가 SAGE 프로젝트다" 의 정의 — sage install 이 만든다. git 과 무관하다.
MARKER_REL = os.path.join("docs", "sage_harness", ".manifest.json")
DECLARATION_REL = os.path.join(".sage", "cycle.json")
SCHEMA_VERSION = 1


class DeclarationRootError(RuntimeError):
    """SAGE 표식이 없는 곳에서 선언을 요구했다 — 조용히 다른 자리에 쓰지 않는다."""


def find_project_root(start=None):
    """가장 가까운 SAGE 표식을 가진 조상 디렉터리, 없으면 None.

    시작 경로를 `realpath` 로 정규화한다. `abspath` 만 쓰면 symlink 를 경유한 cwd 에서 상위
    탐색이 실제 트리가 아니라 링크 경로를 거슬러 올라가 프로젝트 밖으로 나간다. macOS 의
    `/tmp`→`/private/tmp` 가 일상적 사례고, 실측에서 8갈래 중 4갈래가 틀렸다(그중 하나는 정상
    프로젝트를 `None` 으로 거부한다).
    """
    cur = os.path.realpath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(cur, MARKER_REL)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def declaration_path(root):
    return os.path.join(root, DECLARATION_REL)


def read_declaration(root):
    """선언 stem 을 읽어 (stem, error) 로 돌려준다.

    - 부재: `("", "")` — 선언한 적이 없는 정상 상태다
    - 손상·스키마 위반: `("", "<사유>")` — **부재와 갈라서 돌려준다**

    호출부는 error 를 degrade 로 처리하되(파일 하나 깨진 것으로 모든 편집을 멈추지 않는다)
    반드시 표면화해야 한다. 부재·손상·스키마 위반이 전부 `""` 로 뭉개지면 파일을 1바이트만
    잘라도 선언이 조용히 사라지고, 그게 곧 우회 레버가 된다.
    """
    path = declaration_path(root)
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return "", ""
    except (OSError, UnicodeDecodeError) as exc:
        return "", f"{path}: 읽기 실패 ({type(exc).__name__})"
    try:
        data = json.loads(raw)
    except ValueError:
        return "", f"{path}: JSON 파싱 실패 — 손상됐거나 직접 편집됨"
    if not isinstance(data, dict):
        return "", f"{path}: 최상위가 객체가 아님"
    stem = cycle_binding.normalize_stem(data.get("cycle_stem"))
    if stem is None:
        return "", f"{path}: cycle_stem 값이 없거나 유효하지 않음"
    return stem, ""


def write_declaration(root, stem, now=None):
    """선언을 원자적으로 기록하고 파일 경로를 돌려준다. 형식이 틀린 stem 은 ValueError.

    `mkstemp` + `os.replace`: 같은 디렉터리에 온전한 파일을 만든 뒤 한 번에 갈아끼운다.
    직접 `open(w)` 로 쓰면 쓰는 도중 중단된 순간 게이트가 읽는 자리에 잘린 파일이 남는다.
    """
    normalized = cycle_binding.normalize_stem(stem)
    if normalized is None:
        raise ValueError(f"cycle stem 형식 오류: {stem!r}")
    target = declaration_path(root)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    payload = json.dumps({"version": SCHEMA_VERSION, "cycle_stem": normalized,
                          "declared_at": time.strftime(
                              "%Y-%m-%dT%H:%M:%SZ",
                              time.gmtime(time.time() if now is None else now))},
                         ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), prefix=".cycle-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return target


def clear_declaration(root):
    """선언을 지우고 실제로 있었는지 돌려준다."""
    try:
        os.unlink(declaration_path(root))
        return True
    except FileNotFoundError:
        return False


def resolve_stem(root, environ=None):
    """게이트가 쓸 (stem, origin, error). env > 파일 > 없음.

    env 를 위에 두는 이유는 범위가 더 좁아서다 — 프로세스 1회용이라 CI 에서 정당하고, 파일보다
    의도가 명확하다. **origin 을 함께 돌려주는 것이 핵심이다**: 둘이 같이 있으면 env 가 이기는데
    화면이 "파일 선언" 이라고 적으면 확정적으로 거짓이 된다.

    env 가 이겨도 파일 손상은 그대로 보고한다 — 지금 판정에 안 쓰였을 뿐 깨진 파일은 남아 있고,
    env 가 사라지는 순간 조용히 발화한다.
    """
    environ = os.environ if environ is None else environ
    stem, error = read_declaration(root)
    env_stem = (environ.get("SAGE_CYCLE_STEM") or "").strip()
    if env_stem:
        return env_stem, "env", error
    if stem:
        return stem, "cli", error
    return "", "", error
