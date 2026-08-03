"""ChatForYou component implementation-doc gate — deterministic regression.

같은 event/snapshot 이면 항상 같은 decision 이어야 하므로 filesystem 을 쓰지 않고
snapshot 을 직접 조립한다. 실제 allowlist 파일은 단 한 곳(경로 계약 확인)에서만 읽는다.
"""

import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_CORE = os.path.join(_HERE, "..", "chatforyou_dual_implementation_doc_gate_core.py")

_spec = importlib.util.spec_from_file_location("cfy_doc_gate_core", _CORE)
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

TRIGGER = "plan_docs/04-analyze/newcyc.md"
BASE = "plan_docs/00-base_plan/newcyc.md"
BACKEND_DOC = "springboot-backend/plan_docs/newcyc.md"
FRONTEND_DOC = "nodejs-frontend/plan_docs/newcyc.md"
ALLOWLIST = core.LEGACY_CYCLES_FILE

# 도메인 어휘를 피한 중립 stem — 테스트 소스가 자기 위험도를 올리지 않게 한다(03 문서 D5).
LEGACY_STEM = "legacy_alpha"


def event(path=TRIGGER):
    return {"changes": [{"path": path, "op": "write"}]}


def snapshot(allowlist=LEGACY_STEM, **files):
    merged = {}
    if allowlist is not None:
        merged[ALLOWLIST] = "# comment\n\n" + allowlist + "\n"
    merged.update(files)
    return {"files": merged}


def base_plan(marker="ChatForYou-Component-Doc-Gate: v1",
              backend="Component-Backend: REQUIRED",
              frontend="Component-Frontend: N/A: 브라우저 계약 변경 없음",
              extra=()):
    lines = ["# [Base Plan] sample", ""]
    lines += [line for line in (marker, backend, frontend) if line is not None]
    lines += list(extra)
    return "\n".join(lines) + "\n"


def decide(ev, snap):
    return core.decide(ev, {}, snap)


class TestTrigger(unittest.TestCase):
    def test_non_phase4_change_is_skipped(self):
        d = decide(event("springboot-backend/src/main/java/webChat/Sample.java"), snapshot())
        self.assertEqual((d["status"], d["exit_code"]), ("skip", 0))

    def test_two_phase4_targets_have_no_single_cycle(self):
        ev = {"changes": [{"path": "plan_docs/04-analyze/a.md", "op": "write"},
                          {"path": "plan_docs/04-analyze/b.md", "op": "write"}]}
        self.assertEqual(decide(ev, snapshot())["status"], "skip")

    def test_non_markdown_phase4_target_is_ignored(self):
        self.assertEqual(decide(event("plan_docs/04-analyze/notes.txt"), snapshot())["status"], "skip")


class TestLegacyAllowlist(unittest.TestCase):
    def test_listed_stem_is_not_checked_retroactively(self):
        d = decide(event("plan_docs/04-analyze/" + LEGACY_STEM + ".md"), snapshot())
        self.assertEqual((d["status"], d["exit_code"]), ("skip", 0))

    def test_missing_allowlist_does_not_waive_anything(self):
        """파일 삭제가 곧 게이트 해제가 되면 안 된다."""
        d = decide(event("plan_docs/04-analyze/" + LEGACY_STEM + ".md"), snapshot(allowlist=None))
        self.assertEqual(d["status"], "block")
        self.assertIn("missing_base_plan", d["message"])

    def test_comments_and_blank_lines_are_not_stems(self):
        snap = {"files": {ALLOWLIST: "# " + LEGACY_STEM + "\n\n"}}
        d = decide(event("plan_docs/04-analyze/" + LEGACY_STEM + ".md"), snap)
        self.assertEqual(d["status"], "block")

    def test_shipped_allowlist_file_exists_at_contract_path(self):
        self.assertTrue(os.path.isfile(os.path.join(_ROOT, ALLOWLIST)),
                        ALLOWLIST + " 가 계약 경로에 없습니다")


class TestBasePlanContract(unittest.TestCase):
    def test_new_cycle_requires_base_plan(self):
        d = decide(event(), snapshot())
        self.assertEqual(d["exit_code"], 2)
        self.assertIn("missing_base_plan", d["message"])

    def test_missing_marker_blocks(self):
        d = decide(event(), snapshot(**{BASE: base_plan(marker=None)}))
        self.assertIn("missing_gate_marker", d["message"])

    def test_duplicate_marker_blocks(self):
        body = base_plan(extra=("ChatForYou-Component-Doc-Gate: v1",))
        self.assertIn("duplicate_gate_marker", decide(event(), snapshot(**{BASE: body}))["message"])

    def test_wrong_marker_version_blocks(self):
        body = base_plan(marker="ChatForYou-Component-Doc-Gate: v2")
        self.assertIn("invalid_component_status", decide(event(), snapshot(**{BASE: body}))["message"])

    def test_declaration_inside_code_fence_does_not_count(self):
        body = "# [Base Plan] sample\n\n```\nChatForYou-Component-Doc-Gate: v1\n```\n"
        self.assertIn("missing_gate_marker", decide(event(), snapshot(**{BASE: body}))["message"])


class TestComponentDeclaration(unittest.TestCase):
    def test_missing_declaration_blocks(self):
        d = decide(event(), snapshot(**{BASE: base_plan(backend=None)}))
        self.assertIn("missing_component_declaration", d["message"])

    def test_duplicate_declaration_blocks(self):
        body = base_plan(extra=("Component-Backend: REQUIRED",))
        self.assertIn("duplicate_component_declaration", decide(event(), snapshot(**{BASE: body}))["message"])

    def test_unknown_status_blocks(self):
        body = base_plan(backend="Component-Backend: MAYBE")
        self.assertIn("invalid_component_status", decide(event(), snapshot(**{BASE: body}))["message"])

    def test_required_with_trailing_reason_is_rejected(self):
        body = base_plan(backend="Component-Backend: REQUIRED: 사유")
        self.assertIn("invalid_component_status", decide(event(), snapshot(**{BASE: body}))["message"])

    def test_na_without_reason_blocks(self):
        for value in ("Component-Backend: N/A", "Component-Backend: N/A:", "Component-Backend: N/A:   "):
            body = base_plan(backend=value)
            with self.subTest(value=value):
                self.assertIn("empty_na_reason", decide(event(), snapshot(**{BASE: body}))["message"])


class TestPhase05Findings(unittest.TestCase):
    """Phase-05 cross-model 리뷰(codex)가 재현한 결함의 회귀 고정."""

    def test_info_string_line_does_not_close_a_fence(self):
        """```text 안의 ```python 은 닫는 fence 가 아니다 — 코드 예시가 본문 선언이 되면 안 된다."""
        body = ("# sample\n```text\n```python\nChatForYou-Component-Doc-Gate: v1\n"
                "Component-Backend: N/A: 예시\nComponent-Frontend: N/A: 예시\n```\n")
        d = decide(event(), snapshot(**{BASE: body}))
        self.assertEqual(d["status"], "block")
        self.assertIn("missing_gate_marker", d["message"])

    def test_plain_closing_fence_still_closes(self):
        body = ("# sample\n```\nComponent-Backend: REQUIRED\n```\n"
                "ChatForYou-Component-Doc-Gate: v1\n"
                "Component-Backend: N/A: 무관\nComponent-Frontend: N/A: 무관\n")
        self.assertEqual(decide(event(), snapshot(**{BASE: body}))["status"], "ok")

    def test_unknown_component_declaration_blocks(self):
        """모르는 컴포넌트 선언을 무시하면 작성자는 선언했다고 믿는데 아무것도 검사되지 않는다."""
        body = base_plan(backend="Component-Backend: N/A: 무관",
                         extra=("Component-Desktop: REQUIRED",))
        d = decide(event(), snapshot(**{BASE: body}))
        self.assertIn("unknown_component_declaration", d["message"])
        self.assertIn("Component-Desktop", d["message"])

    def test_changing_governed_doc_in_the_same_event_blocks(self):
        """snapshot 은 쓰기 전 상태다 — 같은 patch 로 00 을 무효화하며 04 를 쓰면 판정할 수 없다."""
        ev = {"changes": [{"path": TRIGGER, "op": "write"}, {"path": BASE, "op": "write"}]}
        d = decide(ev, snapshot(**{BASE: base_plan()}))
        self.assertIn("mixed_change_scope", d["message"])
        self.assertIn(BASE, d["message"])

    def test_changing_component_doc_in_the_same_event_blocks(self):
        ev = {"changes": [{"path": TRIGGER, "op": "write"}, {"path": BACKEND_DOC, "op": "write"}]}
        d = decide(ev, snapshot(**{BASE: base_plan(), BACKEND_DOC: "- [x] ok\n"}))
        self.assertIn("mixed_change_scope", d["message"])

    def test_unrelated_co_change_is_still_allowed(self):
        """게이트 판정 대상이 아닌 파일이 함께 바뀌는 것은 막지 않는다."""
        ev = {"changes": [{"path": TRIGGER, "op": "write"},
                          {"path": "docs/unrelated.md", "op": "write"}]}
        snap = snapshot(**{BASE: base_plan(), BACKEND_DOC: "- [x] ok\n"})
        self.assertEqual(decide(ev, snap)["status"], "ok")


class TestComponentDocuments(unittest.TestCase):
    def test_required_backend_document_must_exist(self):
        d = decide(event(), snapshot(**{BASE: base_plan()}))
        self.assertIn("missing_component_doc", d["message"])
        self.assertIn(BACKEND_DOC, d["message"])

    def test_required_frontend_document_must_exist(self):
        body = base_plan(backend="Component-Backend: N/A: 서버 변경 없음",
                         frontend="Component-Frontend: REQUIRED")
        d = decide(event(), snapshot(**{BASE: body}))
        self.assertIn(FRONTEND_DOC, d["message"])

    def test_both_required_blocks_when_either_is_missing(self):
        body = base_plan(frontend="Component-Frontend: REQUIRED")
        d = decide(event(), snapshot(**{BASE: body, BACKEND_DOC: "- [x] done\n"}))
        self.assertIn("missing_component_doc", d["message"])
        self.assertIn(FRONTEND_DOC, d["message"])

    def test_unchecked_box_blocks_with_line_evidence(self):
        doc = "# impl\n- [x] done\n- [ ] 남은 작업\n"
        d = decide(event(), snapshot(**{BASE: base_plan(), BACKEND_DOC: doc}))
        self.assertIn("unchecked_component_doc", d["message"])
        self.assertIn("L3", d["message"])
        self.assertIn("남은 작업", d["message"])

    def test_unchecked_box_inside_fence_is_ignored(self):
        doc = "# impl\n```\n- [ ] 예시\n```\n- [x] done\n"
        self.assertEqual(decide(event(), snapshot(**{BASE: base_plan(), BACKEND_DOC: doc}))["status"], "ok")

    def test_evidence_is_capped(self):
        doc = "# impl\n" + "- [ ] item\n" * 25
        message = decide(event(), snapshot(**{BASE: base_plan(), BACKEND_DOC: doc}))["message"]
        self.assertIn("25건", message)
        self.assertIn("외 15건", message)

    def test_na_component_document_is_not_required(self):
        body = base_plan(backend="Component-Backend: N/A: governance 전용 변경")
        d = decide(event(), snapshot(**{BASE: body}))
        self.assertEqual((d["status"], d["exit_code"]), ("ok", 0))
        self.assertIn("gate_ok", d["message"])

    def test_na_component_stale_document_is_ignored(self):
        body = base_plan(backend="Component-Backend: N/A: governance 전용 변경")
        snap = snapshot(**{BASE: body, BACKEND_DOC: "- [ ] 남은 작업\n"})
        self.assertEqual(decide(event(), snap)["status"], "ok")

    def test_complete_backend_cycle_passes(self):
        snap = snapshot(**{BASE: base_plan(), BACKEND_DOC: "# impl\n- [x] done\n"})
        d = decide(event(), snap)
        self.assertEqual((d["status"], d["exit_code"]), ("ok", 0))
        self.assertIn("Backend=REQUIRED", d["message"])


class TestPlanReads(unittest.TestCase):
    def test_exact_paths_only(self):
        self.assertEqual(core.plan_reads(event()),
                         {"globs": [ALLOWLIST, BASE, BACKEND_DOC, FRONTEND_DOC]})

    def test_no_globs_without_trigger(self):
        self.assertEqual(core.plan_reads(event("src/Sample.java")), {"globs": []})

    def test_globs_have_no_wildcard_or_escape(self):
        for pattern in core.plan_reads(event())["globs"]:
            self.assertNotIn("*", pattern)
            self.assertNotIn("..", pattern)
            self.assertFalse(pattern.startswith("/"))

    def test_prefix_similar_stem_is_not_matched(self):
        """정확 경로만 읽으므로 유사 prefix 파일은 판정에 쓰이지 않는다."""
        snap = snapshot(**{BASE: base_plan(),
                           "springboot-backend/plan_docs/newcyc_extra.md": "- [x] done\n"})
        self.assertIn("missing_component_doc", decide(event(), snap)["message"])


class TestDecisionContract(unittest.TestCase):
    def test_decision_shape_matches_runtime_contract(self):
        for snap in (snapshot(), snapshot(**{BASE: base_plan()}),
                     snapshot(**{BASE: base_plan(), BACKEND_DOC: "- [x] ok\n"})):
            d = decide(event(), snap)
            with self.subTest(status=d["status"]):
                self.assertEqual(set(d), {"status", "exit_code", "message"})
                self.assertIn(d["status"], ("block", "ok", "warn", "skip"))
                self.assertEqual(d["exit_code"], 2 if d["status"] == "block" else 0)
                self.assertIsInstance(d["message"], str)

    def test_contract_version_is_declared(self):
        self.assertTrue(isinstance(core.CONTRACT_VERSION, str) and core.CONTRACT_VERSION)

    def test_same_input_is_deterministic(self):
        snap = snapshot(**{BASE: base_plan()})
        self.assertEqual(decide(event(), snap), decide(event(), snap))


class TestHostParity(unittest.TestCase):
    """양 host 는 입력 추출만 다르다 — 같은 changes 면 같은 decision 이어야 한다."""

    def test_claude_and_codex_changes_agree(self):
        claude_changes = [{"path": TRIGGER, "op": "write"}]
        codex_changes = [{"path": TRIGGER, "op": "update"}]
        snap = snapshot(**{BASE: base_plan()})
        self.assertEqual(decide({"changes": claude_changes}, snap),
                         decide({"changes": codex_changes}, snap))


if __name__ == "__main__":
    unittest.main(verbosity=2)
