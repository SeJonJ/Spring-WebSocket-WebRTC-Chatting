#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT
CORE="$ROOT/scripts/sage_harness/hooks"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0
fail=0

expect_rc() {
  local expected="$1"
  local label="$2"
  shift 2
  set +e
  "$@" >/dev/null 2>&1
  local actual=$?
  set -e
  if [[ "$actual" -eq "$expected" ]]; then
    printf 'PASS %s\n' "$label"
    pass=$((pass + 1))
  else
    printf 'FAIL %s expected=%s actual=%s\n' "$label" "$expected" "$actual"
    fail=$((fail + 1))
  fi
}

run_hook() {
  local runtime="$1"
  local hook_root="$2"
  printf '{}\n' | sage-hook --runtime "$runtime" --hook pre-implementation-gate \
    --root "$hook_root" --core-dir "$CORE"
}

mkdir -p "$TMP/valid/sage" "$TMP/missing/sage" "$TMP/broken/sage" "$TMP/drift/sage"
cp "$ROOT/sage/project-profile.yaml" "$TMP/valid/sage/project-profile.yaml"
cp "$ROOT/sage/project-profile.json" "$TMP/valid/sage/project-profile.json"
cp "$ROOT/sage/project-profile.yaml" "$TMP/missing/sage/project-profile.yaml"
cp "$ROOT/sage/project-profile.yaml" "$TMP/broken/sage/project-profile.yaml"
printf '{\n' > "$TMP/broken/sage/project-profile.json"
cp "$ROOT/sage/project-profile.yaml" "$TMP/drift/sage/project-profile.yaml"
printf '{}\n' > "$TMP/drift/sage/project-profile.json"

for runtime in claude codex; do
  expect_rc 0 "$runtime valid explicit root" run_hook "$runtime" "$TMP/valid"
  expect_rc 2 "$runtime missing compiled profile" run_hook "$runtime" "$TMP/missing"
  expect_rc 2 "$runtime broken compiled profile" run_hook "$runtime" "$TMP/broken"
  expect_rc 2 "$runtime YAML JSON drift" run_hook "$runtime" "$TMP/drift"
  expect_rc 2 "$runtime core load failure" bash -c \
    "printf '{}\\n' | sage-hook --runtime '$runtime' --hook pre-implementation-gate --root '$TMP/valid' --core-dir '$TMP/no-core'"
done

expect_rc 0 "claude root env from wrong cwd" bash -c \
  "cd '$TMP' && printf '{}\\n' | CLAUDE_PROJECT_DIR='$TMP/valid' sage-hook --runtime claude --hook pre-implementation-gate --core-dir '$CORE'"
expect_rc 0 "codex root env from wrong cwd" bash -c \
  "cd '$TMP' && printf '{}\\n' | CODEX_PROJECT_ROOT='$TMP/valid' sage-hook --runtime codex --hook pre-implementation-gate --core-dir '$CORE'"
expect_rc 0 "claude root env absent uses git root" bash -c \
  "cd '$ROOT' && env -u CLAUDE_PROJECT_DIR -u SAGE_PROFILE sh -c \"printf '{}\\n' | sage-hook --runtime claude --hook pre-implementation-gate --core-dir '$CORE'\""
expect_rc 0 "codex root env absent uses git root" bash -c \
  "cd '$ROOT' && env -u CODEX_PROJECT_ROOT -u SAGE_PROFILE sh -c \"printf '{}\\n' | sage-hook --runtime codex --hook pre-implementation-gate --core-dir '$CORE'\""

PYTHONPATH="$CORE:$CORE/runtime:$CORE/strategies/pre_implementation_gate" python3 - <<'PY'
import json
import os
import pre_implementation_gate_core as gate
import cycle_domain_review as review

root = os.environ["ROOT"]
with open(os.path.join(root, "sage", "project-profile.json"), encoding="utf-8") as fh:
    profile = json.load(fh)
profile["pdca"]["enabled"] = False
event = {"branch": "chatforyou_v2_sage", "declared_max": None, "changes": [{
    "path": "nodejs-frontend/static/js/common/ajaxUtil.js",
    "op": "write",
    "content": "const peer = new RTCPeerConnection();",
}]}
decision = gate.decide(event, profile, {"plan_files": [], "review_candidates": []}, {"found": False})
assert decision["message_key"] == "block_l3_no_plan", decision
assert "content_l3" in gate.classify_risk(event, profile)["trigger_sources"]

valid = {"path": "r.md", "content": "---\ncycle_id: chatforyou_v2_sage\nround: [1, 2]\ndomain_ref: webrtc\n---\n"}
signals = {"cycle_ids": {"chatforyou_v2_sage"}, "matched_domains": {"webrtc"}}
assert review.find_l3_review(signals, {"l3_review_docs": [valid]})["found"]
for bad in (
    {"path": "r.md", "content": valid["content"].replace("chatforyou_v2_sage", "old-cycle")},
    {"path": "r.md", "content": valid["content"].replace("[1, 2]", "[1]")},
    {"path": "r.md", "content": valid["content"].replace("webrtc", "security")},
):
    assert not review.find_l3_review(signals, {"l3_review_docs": [bad]})["found"]
PY
pass=$((pass + 2))
printf 'PASS content-L3 block provenance\n'
printf 'PASS cycle-domain-round review oracle\n'

printf 'RESULT pass=%s fail=%s\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]]
