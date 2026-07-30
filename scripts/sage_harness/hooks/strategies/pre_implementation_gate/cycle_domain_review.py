"""Deterministic pre-implementation L3 review evidence matcher.

Evidence is accepted only from the dedicated review snapshot and must bind to
the exact current cycle stem, one registered domain, and both design rounds.
"""

import yaml


def _frontmatter(content):
    if not (content or "").startswith("---\n"):
        return None, "frontmatter missing"
    end = content.find("\n---\n", 4)
    if end < 0:
        return None, "frontmatter terminator missing"
    try:
        data = yaml.safe_load(content[4:end]) or {}
    except Exception as exc:
        return None, f"frontmatter parse failed: {type(exc).__name__}"
    if not isinstance(data, dict):
        return None, "frontmatter must be a mapping"
    return data, None


def find_l3_review(signals: dict, snapshot: dict) -> dict:
    cycle_stem = str(signals.get("cycle_stem") or "")
    domains = {str(value) for value in (signals.get("matched_domains") or set()) if str(value)}
    if not cycle_stem:
        detail = signals.get("cycle_binding_error") or "current cycle stem unavailable"
        return {"found": False, "enforce": True, "strategy": "cycle_domain_review",
                "reason": detail}
    if not domains:
        return {"found": False, "enforce": True, "strategy": "cycle_domain_review",
                "reason": "L3 change did not match a registered risk domain"}

    covered = set()
    malformed = []
    paths = []
    for doc in snapshot.get("l3_review_docs") or []:
        meta, error = _frontmatter(doc.get("content") or "")
        if error:
            malformed.append(f"{doc.get('path')}: {error}")
            continue
        review_stem = str(meta.get("cycle_stem") or "")
        domain_ref = meta.get("domain_ref")
        rounds = meta.get("round")
        if review_stem != cycle_stem:
            continue
        if not isinstance(domain_ref, str) or domain_ref not in domains:
            continue
        if not isinstance(rounds, list) or {str(value) for value in rounds} != {"1", "2"}:
            malformed.append(f"{doc.get('path')}: round must be [1, 2]")
            continue
        covered.add(domain_ref)
        paths.append(doc.get("path"))

    missing = sorted(domains - covered)
    if missing:
        details = f"missing review evidence for domains: {', '.join(missing)}"
        if malformed:
            details += f"; malformed: {'; '.join(malformed[:3])}"
        return {"found": False, "enforce": True, "strategy": "cycle_domain_review",
                "reason": details, "missing_domains": missing}
    return {"found": True, "enforce": True, "strategy": "cycle_domain_review",
            "paths": paths, "domains": sorted(covered)}
