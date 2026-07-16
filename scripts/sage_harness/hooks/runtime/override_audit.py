"""override_audit — 게이트 BLOCK 의 합법적 우회 + 감사 추적.

게이트(pre-implementation-gate · pre-phase4-checklist-gate)가 BLOCK 을 걸면, 운영자가 사유·기한과
함께 명시적으로 우회한다. 권한과 감사를 두 저장소로 분리한다:

- 감사 로그 `.sage/override.jsonl` — grant·bypass 전 이력(append-only). 커밋 대상이라
  "누가 언제 왜 무엇을 우회했는지"를 동료·CI·리뷰어가 clone 후에도 추적할 수 있다.
- 권한 캐시 `.sage/tmp/grants.jsonl` — 이 머신에서 활성인 grant. 로컬 전용(.gitignore)이라
  레포를 clone/pull 해도 남이 발급한 우회 권한이 자동으로 활성화되지 않는다.

활성 여부는 권한 캐시만으로 판정한다. TTL 만료 시 자동 회수되어 상시 우회를 막는다(wall-clock 기준,
세션 교차에도 일관). gate 스코프는 특정 게이트 id 또는 "all" — 우회는 grant.gate ∈ {요청 gate, "all"}.

엔진 모듈(도메인값 0): 게이트 id 는 호출자가 주입하고, 경로/시간만 여기서 결정한다.
"""
import json
import os
import time
import uuid

AUDIT_REL = os.path.join(".sage", "override.jsonl")        # 커밋되는 감사 이력
GRANTS_REL = os.path.join(".sage", "tmp", "grants.jsonl")  # 로컬 전용 활성 권한 캐시
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

# TTL 상한. "시한부 우회"가 임의로 길어지면 사실상 상시 우회가 되므로 24h 로 캡한다. 초과 grant 는
# 거부하고, 더 길게 필요하면 만료 후 재발급하게 강제한다.
MAX_TTL_SECONDS = 24 * 3600


def audit_path(root):
    return os.path.join(root, AUDIT_REL)


def grants_path(root):
    return os.path.join(root, GRANTS_REL)


def parse_ttl(s):
    """'30m' | '2h' | '1d' | '90s' | '1800'(초) → seconds(int). 음수/0/무효 → None."""
    s = (s or "").strip().lower()
    if not s:
        return None
    try:
        if s[-1] in _UNITS:
            secs = int(float(s[:-1]) * _UNITS[s[-1]])
        else:
            secs = int(float(s))
    except (ValueError, IndexError):
        return None
    return secs if secs > 0 else None


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _append(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def read_records(root):
    """감사 로그 전 레코드(파싱 실패 줄 skip). 부재 → []."""
    return _read_jsonl(audit_path(root))


def grant(root, reason, ttl_seconds, gate="all", user=None, now=None):
    """override grant 1건 발급 → 레코드 반환. reason·ttl 필수(상위에서 검증).

    감사 로그(커밋·영속)와 권한 캐시(로컬·집행) 양쪽에 기록한다. TTL 상한 초과는 거부(ValueError):
    라이브러리 레벨 불변식이라 CLI 를 우회해 직접 호출해도 시한부 보장이 깨지지 않는다."""
    if int(ttl_seconds) > MAX_TTL_SECONDS:
        raise ValueError(f"TTL {int(ttl_seconds)}s 가 상한 {MAX_TTL_SECONDS}s(24h) 초과 — 더 짧게 발급하거나 만료 후 재발급")
    t = time.time() if now is None else now
    rec = {"event": "grant", "grant_id": uuid.uuid4().hex[:12], "ts": _iso(t), "epoch": int(t),
           "expires_epoch": int(t) + int(ttl_seconds), "expires_at": _iso(t + ttl_seconds),
           "ttl_seconds": int(ttl_seconds), "gate": gate, "reason": reason,
           "user": user or os.environ.get("USER") or "unknown"}
    _append(audit_path(root), rec)    # 추적용(커밋)
    _append(grants_path(root), rec)   # 집행용(로컬)
    return rec


def revoke(root, grant_id, reason=None, user=None, now=None):
    """활성 grant 를 만료 전에 회수한다 → revoke 레코드 반환, 대상이 없으면 None.

    append-only 를 유지하며 revoke 이벤트를 감사 로그와 권한 캐시 양쪽에 남긴다 — 이후
    active_grants 가 같은 grant_id 를 제외한다. 미존재/이미 만료/이미 회수된 id 는 무효(None)."""
    t = time.time() if now is None else now
    target = next((g for g in active_grants(root, now=t) if g.get("grant_id") == grant_id), None)
    if target is None:
        return None
    rec = {"event": "revoke", "ts": _iso(t), "epoch": int(t), "grant_id": grant_id,
           "gate": target.get("gate"), "reason": reason or "(no reason)",
           "user": user or os.environ.get("USER") or "unknown"}
    # 집행 캐시를 먼저 쓴다 — 이게 실패하면 권한이 그대로 살아 있으므로 예외로 알려야 한다.
    # (반대로 grant 는 집행 캐시를 마지막에 써서, 실패 시 권한이 안 생기는 안전한 방향이 된다.)
    # 여기서 감사부터 쓰면 "감사엔 회수, 집행엔 활성"인 상태가 생겨 회수가 무력화될 수 있다.
    _append(grants_path(root), rec)   # 집행(실패 시 권한 유지 — 예외 전파로 운영자 인지)
    _append(audit_path(root), rec)    # 추적(집행 성공 후 기록)
    return rec


def active_grants(root, gate=None, now=None):
    """미만료·미회수 grant 레코드. 권한 캐시(로컬)만 읽어 판정하므로 clone 시 남의 권한은 비활성이다.
    gate 지정 시 grant.gate ∈ {gate, 'all'} 만. 최신순."""
    t = time.time() if now is None else now
    records = _read_jsonl(grants_path(root))
    revoked = {r.get("grant_id") for r in records if r.get("event") == "revoke"}
    out = []
    for r in records:
        if r.get("event") != "grant":
            continue
        if r.get("grant_id") in revoked:
            continue
        if r.get("expires_epoch", 0) <= t:
            continue
        if gate is not None and r.get("gate") not in (gate, "all"):
            continue
        out.append(r)
    return sorted(out, key=lambda r: r.get("epoch", 0), reverse=True)


def is_override_active(root, gate, now=None):
    return bool(active_grants(root, gate=gate, now=now))


def record_bypass(root, gate, files, message_key, grant_rec, now=None):
    """grant 가 실제로 BLOCK 을 통과시킨 사실을 감사 로그에 기록 — 무엇을(message_key) 어느 파일에
    적용했는지 추적. 권한이 아니라 사후 추적이므로 감사 로그에만 남긴다."""
    t = time.time() if now is None else now
    _append(audit_path(root), {"event": "bypass", "ts": _iso(t), "epoch": int(t), "gate": gate,
                               "message_key": message_key, "files": files or [],
                               "grant_id": (grant_rec or {}).get("grant_id"),
                               "grant_ts": (grant_rec or {}).get("ts"),
                               "reason": (grant_rec or {}).get("reason")})
