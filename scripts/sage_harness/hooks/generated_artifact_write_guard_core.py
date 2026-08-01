#!/usr/bin/env python3
"""Pure decision core for the generated-artifact write guard."""
from __future__ import annotations

import json
import os
import re
from pathlib import PurePosixPath

CONTRACT_VERSION = "2"

_PATCH_PATH = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$")
_MOVE_PATH = re.compile(r"^\*\*\* Move to: (.+)$")
_FRAMEWORK_DOCS = {"agent_guide.md", "claude.md", "codex.md", "agents.md"}
_OVERLAY_AGENTS = {"implementer-a.md", "implementer-b.md", "leader.md", "reviewer.md"}
_BLOCKED_AGENTS = {"qa.md", "convention-checker.md"}
_OVERLAY_SKILLS = {"sage-cycle", "sage-plan", "sage-review", "sage-team"}
_BLOCKED_SKILLS = {"sage-init", "sage-asset", "sage-profile-modify", "sage-asset-override"}


def _normalized(path: object) -> str:
    if not isinstance(path, str):
        return ""
    value = path.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value.lower()


def _parts(path: object) -> tuple[str, ...]:
    normalized = _normalized(path)
    return PurePosixPath(normalized).parts if normalized else ()


def _host_asset(parts: tuple[str, ...]) -> tuple[str, str, tuple[str, ...]] | None:
    for index, part in enumerate(parts):
        if part not in (".claude", ".codex") or index + 2 >= len(parts):
            continue
        kind = parts[index + 1]
        if kind in ("agents", "hooks", "skills"):
            return part, kind, parts[index + 2:]
    return None


def _is_framework_override(parts: tuple[str, ...]) -> bool:
    marker = ("sage", "asset_overrides", "framework")
    for index in range(len(parts) - len(marker)):
        if parts[index:index + len(marker)] == marker:
            tail = parts[index + len(marker):]
            return len(tail) == 1 and tail[0].endswith(".md")
    return False


def is_guarded(path: object) -> bool:
    parts = _parts(path)
    if not parts or _is_framework_override(parts):
        return False
    if parts[-1] == ".mcp.json" or parts[-1] in _FRAMEWORK_DOCS:
        return True
    return _host_asset(parts) is not None


def _overlay_hint(path: object) -> str:
    asset = _host_asset(_parts(path))
    if not asset:
        return ""
    _host, kind, tail = asset
    if kind == "agents" and len(tail) == 1 and tail[0] in _OVERLAY_AGENTS:
        return f"sage/asset_overrides/agents/{tail[0]}"
    if kind == "skills" and len(tail) >= 2 and tail[0] in _OVERLAY_SKILLS:
        return f"sage/asset_overrides/skills/{tail[0]}.md"
    return ""


def _is_blocked_core_render(path: object) -> bool:
    asset = _host_asset(_parts(path))
    if not asset:
        return False
    _host, kind, tail = asset
    if kind == "agents" and len(tail) == 1 and tail[0] in _BLOCKED_AGENTS:
        return True
    return kind == "skills" and len(tail) >= 2 and tail[0] in _BLOCKED_SKILLS


def _is_framework_doc(path: object) -> bool:
    parts = _parts(path)
    return bool(parts) and parts[-1] in _FRAMEWORK_DOCS


def block_message(path: str) -> str:
    if _is_framework_doc(path):
        return "\n".join([
            f"⛔ SAGE write guard: '{path}' 는 CORE 프레임워크 문서입니다. 직접수정 금지 "
            "(sage install --force 가 덮어씀).",
            "→ framework overlay는 독립 gate oracle이 없어 현재 차단됩니다.",
            "→ 프로젝트 값은 'sage/project-profile.yaml', 규칙은 conventions/critical-domain/"
            "project-local 문서에 작성하세요.",
            "→ 그 문서를 세션 시작 라우팅 블록에 노출하려면 profile 의 'governance_docs'"
            "(경로+라벨)에 등록하세요.",
        ])
    overlay = _overlay_hint(path)
    if overlay:
        return "\n".join([
            f"⛔ SAGE write guard: '{path}' 는 CORE 부트스트랩 렌더입니다. 직접수정 금지.",
            f"→ 프로젝트 로컬 커스터마이즈는 '{overlay}' 에 작성하세요 "
            "(sage install --force 에도 보존).",
            "→ 작성 도움: '/sage-asset-override' (게이트 완화 여부까지 점검).",
        ])
    if _is_blocked_core_render(path):
        return "\n".join([
            f"⛔ SAGE write guard: '{path}' 는 CORE 부트스트랩 렌더입니다. 직접수정 금지.",
            "→ 이 gate-bearing CORE 자산은 독립 executable oracle이 없어 현재 overlay 비지원입니다.",
            "→ CORE base 갱신은 선택한 host/scope의 'sage install --force'를 사용하세요.",
            "→ 프로젝트 고유 규칙은 profile/conventions/critical-domain 문서에 두고, "
            "새 프로젝트 자산은 '/sage-asset'으로 작성하세요.",
        ])
    return "\n".join([
        f"⛔ SAGE write guard: '{path}' 는 생성 산출물입니다. 직접수정 금지.",
        "→ docs/sage_harness/<kind>s/<id>.md (spec) 을 고치고 'sage generate' 를 쓰세요.",
        "→ 이미 수정한 diff 라면 'sage absorb --kind <k> --id <id> --from-blocked-diff' 로 "
        "spec patch 로 변환하세요.",
        "(sage generate CLI 는 편집도구를 안 거치므로 이 가드에 걸리지 않습니다.)",
    ])


def extract_paths(raw_text: str) -> list[str]:
    try:
        data = json.loads(raw_text or "{}")
    except (TypeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return []
    paths: list[str] = []
    direct = tool_input.get("file_path") or tool_input.get("path")
    if isinstance(direct, str) and direct:
        paths.append(direct)
    command = tool_input.get("command") or ""
    if isinstance(command, str):
        for line in command.splitlines():
            match = _PATCH_PATH.match(line) or _MOVE_PATH.match(line)
            if match:
                paths.append(match.group(1).strip())
    return paths


def decide_paths(paths: list[str]) -> dict:
    for path in paths:
        if is_guarded(path):
            return {"status": "block", "exit_code": 2, "path": path, "message": block_message(path)}
    return {"status": "pass", "exit_code": 0, "path": "", "message": ""}


def decide_json(raw_text: str) -> dict:
    return decide_paths(extract_paths(raw_text))


def decide_input(raw_text: str, direct_path: str | None = None, environ=None) -> dict:
    """Preserve legacy direct-call precedence before falling back to hook stdin JSON."""
    environ = os.environ if environ is None else environ
    if direct_path is not None:
        return decide_paths([direct_path])
    env_path = environ.get("SAGE_GUARD_PATH")
    if env_path:
        return decide_paths([env_path])
    return decide_json(raw_text)
