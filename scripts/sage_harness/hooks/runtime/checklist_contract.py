"""Dependency-free contract for ``checklist_scan_targets``."""

import re


_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
_CONTROL = re.compile(r"[\x00-\x1f\x7f\x85\u2028\u2029]")
_TARGET_KEYS = {"label", "glob", "is_impl"}


def unsafe_glob(value):
    if not isinstance(value, str) or not value.strip():
        return "glob은 비어있지 않은 문자열이어야 함"
    if len(value) > 512:
        return "glob은 512자 이하여야 함"
    if _CONTROL.search(value):
        return "glob에 제어문자나 줄바꿈을 사용할 수 없음"
    if value.startswith(("/", "\\")) or _DRIVE_PREFIX.match(value):
        return "glob은 POSIX/Windows 절대·rooted·drive-relative 경로일 수 없음"
    if any(part == ".." for part in value.replace("\\", "/").split("/")):
        return "glob에 '..' 경로 세그먼트를 사용할 수 없음"
    return ""


def checklist_target_issues(profile):
    if "checklist_scan_targets" not in profile:
        return []
    targets = profile.get("checklist_scan_targets")
    if not isinstance(targets, list):
        return ["checklist_scan_targets 는 리스트여야 함"]

    issues = []
    for index, target in enumerate(targets):
        where = f"checklist_scan_targets[{index}]"
        if not isinstance(target, dict):
            issues.append(f"{where} 는 label/glob 매핑이어야 함")
            continue
        non_string_keys = [key for key in target if not isinstance(key, str)]
        if non_string_keys:
            issues.append(f"{where} 키는 문자열이어야 함")
        unknown = sorted((str(key) for key in target if key not in _TARGET_KEYS))
        if unknown:
            issues.append(f"{where} 에 미지 키 {unknown}; label/glob/is_impl 만 허용")
        label = target.get("label")
        if (not isinstance(label, str) or not label.strip() or len(label) > 80
                or _CONTROL.search(label)):
            issues.append(f"{where}.label 은 1..80자의 단일행 문자열이어야 함")
        reason = unsafe_glob(target.get("glob"))
        if reason:
            issues.append(f"{where}.glob: {reason}")
        if "is_impl" in target and not isinstance(target.get("is_impl"), bool):
            issues.append(f"{where}.is_impl 은 bool이어야 함")
    return issues
