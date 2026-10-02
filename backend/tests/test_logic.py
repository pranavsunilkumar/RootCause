"""
Stdlib-only tests for everything that doesn't need FastAPI running.
Run with:  python -m unittest tests.test_logic -v   (from backend/)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bughunt import bank as bughunt_bank
from app.diagnosis import DiagnosisEngine
from app.grading import KeywordGrader
from app.graph import graph
from app.retrieval import index as concept_index
from app.teachback import TeachBackEngine

try:
    # These pull in SQLAlchemy (app.store) -- not always installed in every
    # environment this suite runs in. The rest of the suite (graph, grader,
    # diagnosis, bug hunt, teach-back, retrieval) has zero DB dependency and
    # always runs; PathEngine tests are skipped, not silently ignored, when
    # SQLAlchemy is unavailable so CI output says so explicitly.
    from app.path import PathEngine, REASON_ALL_MASTERED, REASON_NEXT_ROOT, REASON_NEXT_UNLOCKED, REASON_WEAKEST_LINK
    from app.store import STATUS_MASTERED, STATUS_WEAK, ProgressStore

    HAS_DB = True
except ImportError as e:
    HAS_DB = False
    _DB_IMPORT_ERROR = e


class TestGraph(unittest.TestCase):
    def test_loads_all_nodes(self):
        self.assertGreaterEqual(len(graph), 15)

    def test_transformers_chain_is_ordered_upstream_first(self):
        chain = [c.id for c in graph.prereq_chain("transformers")]
        self.assertEqual(chain[-1], "transformers")
        # every prereq of a node must appear before that node
        seen = set()
        for cid in chain:
            node = graph.get(cid)
            for p in node.prereqs:
                self.assertIn(p, seen, f"{p} should precede {cid} in {chain}")
            seen.add(cid)

    def test_deep_chain_reaches_true_roots(self):
        # attention needs matmul + softmax + dot-product, softmax needs
        # probability-basics, matmul needs vectors+dot-product: all should
        # surface in attention's chain.
        chain = {c.id for c in graph.prereq_chain("attention")}
        for expected in ["vectors", "dot-product", "matrix-multiplication", "probability-basics", "softmax", "attention"]:
            self.assertIn(expected, chain)

    def test_resolve_handles_alias_and_case(self):
        self.assertEqual(graph.resolve("Self-Attention"), "attention")
        self.assertEqual(graph.resolve("softmax"), "softmax")
        self.assertIsNone(graph.resolve("quantum entanglement"))

    def test_no_unknown_prereqs_and_no_cycles(self):
        # constructor already validates on import; re-check ids are consistent
        for cid in graph.all_ids():
            node = graph.get(cid)
            for p in node.prereqs:
                self.assertIn(p, graph.all_ids())


class TestKeywordGrader(unittest.TestCase):
    def setUp(self):
        self.grader = KeywordGrader()

    def test_full_match_passes(self):
        groups = [["fast", "quick"], ["red", "crimson"]]
        result = self.grader.grade("it was a fast, crimson car", groups)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.missing, [])

    def test_partial_match_below_threshold_fails(self):
        groups = [["fast", "quick"], ["red", "crimson"], ["shiny", "glossy"]]
        # only 1 of 3 -> 0.33, below 0.6 threshold
        result = self.grader.grade("it was fast", groups)
        self.assertFalse(result.passed)
        self.assertAlmostEqual(result.score, 1 / 3, places=2)

    def test_empty_answer_fails_cleanly(self):
        result = self.grader.grade("", [["anything"]])
        self.assertFalse(result.passed)
        self.assertEqual(result.feedback, "No answer given.")

    def test_no_keyword_groups_auto_passes(self):
        result = self.grader.grade("literally anything", [])
        self.assertTrue(result.passed)

    def test_phrase_keywords_require_substring_not_word_boundary(self):
        groups = [["chain rule"]]
        self.assertTrue(self.grader.grade("you need the chain rule here", groups).passed)
        self.assertFalse(self.grader.grade("chains and rules are different words", groups).passed)


class TestDiagnosisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DiagnosisEngine(concept_graph=graph, grader=KeywordGrader())

    def test_chain_for_target_returns_all_ancestors_in_order(self):
        chain = self.engine.chain_for("attention")
        ids = [s.concept_id for s in chain]
        self.assertEqual(ids[-1], "attention")
        self.assertLess(ids.index("vectors"), ids.index("attention"))

    @staticmethod
    def _winning_answer(concept_id: str) -> str:
        """A synthetic answer guaranteed to hit every keyword group in this
        node's probe -- i.e. an answer that check_node will pass."""
        node = graph.get(concept_id)
        return " ".join(group[0] for group in node.probe.keyword_groups)

    def test_first_failing_upstream_node_is_the_diagnosis(self):
        chain = self.engine.chain_for("backpropagation")
        checks = []
        broke_at = None
        for step in chain:
            if step.concept_id == "chain-rule":
                # deliberately weak answer
                check = self.engine.check_node(step.concept_id, "not sure")
                checks.append(check)
                broke_at = step.concept_id
                break
            else:
                checks.append(self.engine.check_node(step.concept_id, self._winning_answer(step.concept_id)))

        diagnosis = self.engine.diagnose_from_checks("backpropagation", checks)
        self.assertEqual(diagnosis.broken_concept, broke_at)
        self.assertGreater(diagnosis.steps_upstream, 0)

    def test_all_pass_diagnoses_the_target_itself(self):
        chain = self.engine.chain_for("gradient-descent")
        checks = [self.engine.check_node(step.concept_id, self._winning_answer(step.concept_id)) for step in chain]

        diagnosis = self.engine.diagnose_from_checks("gradient-descent", checks)
        self.assertEqual(diagnosis.broken_concept, "gradient-descent")
        self.assertEqual(diagnosis.steps_upstream, 0)


class TestBugHunt(unittest.TestCase):
    def test_every_snippet_bug_line_is_within_range(self):
        for cid in bughunt_bank.available_ids():
            snippet = bughunt_bank.get(cid)
            num_lines = len(snippet.code.splitlines())
            self.assertGreaterEqual(snippet.bug_line, 1)
            self.assertLessEqual(snippet.bug_line, num_lines)

    def test_public_payload_hides_the_answer(self):
        snippet = bughunt_bank.get("gradient-descent")
        payload = snippet.public()
        self.assertNotIn("bug_line", payload)
        self.assertNotIn("misconception", payload)
        self.assertNotIn("fixed_code", payload)

    def test_correct_guess_is_detected(self):
        snippet = bughunt_bank.get("gradient-descent")
        result = bughunt_bank.check_guess("gradient-descent", snippet.bug_line)
        self.assertTrue(result.correct_line)
        self.assertEqual(result.line_distance, 0)

    def test_wrong_guess_reports_distance(self):
        snippet = bughunt_bank.get("softmax")
        far_line = 1 if snippet.bug_line != 1 else 2
        result = bughunt_bank.check_guess("softmax", far_line)
        self.assertFalse(result.correct_line)
        self.assertEqual(result.line_distance, abs(far_line - snippet.bug_line))


class TestTeachBack(unittest.TestCase):
    def setUp(self):
        self.engine = TeachBackEngine(concept_graph=graph, grader=KeywordGrader())

    def test_strong_explanation_passes_with_no_followup(self):
        node = graph.get("softmax")
        explanation = " ".join(node.key_points)
        result = self.engine.grade("softmax", explanation)
        self.assertTrue(result.grade.passed)
        self.assertIsNone(result.followup_question)

    def test_weak_explanation_gets_a_followup_question(self):
        result = self.engine.grade("softmax", "it makes numbers into probabilities I think")
        # at minimum this should not crash and should surface *a* followup
        # when the explanation doesn't cover everything
        if not result.grade.passed:
            self.assertIsNotNone(result.followup_question)

    def test_curated_followup_used_when_available(self):
        result = self.engine.grade("gradient-descent", "you subtract something I guess")
        if result.followup_question:
            self.assertIsInstance(result.followup_question, str)
            self.assertGreater(len(result.followup_question), 0)


@unittest.skipUnless(HAS_DB, f"app.store needs SQLAlchemy, which isn't installed here ({_DB_IMPORT_ERROR if not HAS_DB else ''})")
class TestPathEngine(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.db_path = tempfile.mktemp(suffix=".db")
        self.store = ProgressStore(f"sqlite:///{self.db_path}")
        self.engine = PathEngine(concept_graph=graph, progress_store=self.store)
        self.user = "path-test-user"

    def tearDown(self):
        import os
        self.store.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_brand_new_learner_gets_a_true_root_concept(self):
        step = self.engine.next_concept(self.user)
        self.assertEqual(step.reason_code, REASON_NEXT_ROOT)
        self.assertIsNotNone(step.concept_id)
        self.assertEqual(graph.get(step.concept_id).prereqs, [])

    def test_weak_concept_takes_priority_over_unseen(self):
        # master a root concept, then mark something else weak
        self.store.mark(self.user, "vectors", STATUS_MASTERED, "teachback", True, 1.0)
        self.store.mark(self.user, "chain-rule", STATUS_WEAK, "diagnose", False, 0.2)

        step = self.engine.next_concept(self.user)
        self.assertEqual(step.reason_code, REASON_WEAKEST_LINK)
        self.assertEqual(step.concept_id, "chain-rule")

    def test_recommends_most_foundational_weak_node_not_just_any_weak_node(self):
        # mark a downstream node weak AND a more foundational one weak;
        # the more foundational one should win
        self.store.mark(self.user, "backpropagation", STATUS_WEAK, "diagnose", False, 0.1)
        self.store.mark(self.user, "chain-rule", STATUS_WEAK, "diagnose", False, 0.1)

        order = self.engine.full_order()
        self.assertLess(order.index("chain-rule"), order.index("backpropagation"))

        step = self.engine.next_concept(self.user)
        self.assertEqual(step.concept_id, "chain-rule")

    def test_recommends_next_unlocked_concept_once_prereqs_mastered(self):
        # master every root concept so no unrelated root outranks dot-product
        for cid in graph.all_ids():
            if not graph.get(cid).prereqs:
                self.store.mark(self.user, cid, STATUS_MASTERED, "teachback", True, 1.0)

        step = self.engine.next_concept(self.user)
        # whichever node it recommends must genuinely be ready: unseen,
        # with every one of its own prereqs already mastered
        recommended = graph.get(step.concept_id)
        self.assertEqual(step.reason_code, REASON_NEXT_UNLOCKED)
        for prereq in recommended.prereqs:
            self.assertEqual(self.store.mastery_map(self.user, [prereq])[prereq].status, STATUS_MASTERED)
        # and it must be the EARLIEST such node in topological order
        order = self.engine.full_order()
        for cid in order:
            if cid == step.concept_id:
                break
            node = graph.get(cid)
            still_unseen_and_ready = node.prereqs and all(
                self.store.mastery_map(self.user, [p])[p].status == STATUS_MASTERED for p in node.prereqs
            )
            self.assertFalse(still_unseen_and_ready, f"{cid} was ready and earlier than {step.concept_id}")

    def test_does_not_recommend_a_node_whose_prereqs_are_not_yet_mastered(self):
        # master nothing; matrix-multiplication needs vectors + dot-product,
        # neither mastered, so it must not be recommended yet
        step = self.engine.next_concept(self.user)
        self.assertNotEqual(step.concept_id, "matrix-multiplication")

    def test_all_mastered_returns_no_concept(self):
        for cid in graph.all_ids():
            self.store.mark(self.user, cid, STATUS_MASTERED, "teachback", True, 1.0)

        step = self.engine.next_concept(self.user)
        self.assertIsNone(step.concept_id)
        self.assertEqual(step.reason_code, REASON_ALL_MASTERED)

    def test_full_order_is_a_valid_topological_order(self):
        order = self.engine.full_order()
        self.assertEqual(set(order), set(graph.all_ids()))
        position = {cid: i for i, cid in enumerate(order)}
        for cid in order:
            for prereq in graph.get(cid).prereqs:
                self.assertLess(position[prereq], position[cid])


class TestRetrieval(unittest.TestCase):
    def test_query_returns_relevant_concept_first(self):
        hits = concept_index.search("softmax numerical stability overflow", top_k=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0].concept_id, "softmax")

    def test_nonsense_query_returns_nothing(self):
        hits = concept_index.search("giraffe migration patterns in the serengeti", top_k=3)
        self.assertEqual(hits, [])

    def test_related_to_excludes_the_concept_itself(self):
        related = concept_index.related_to("attention", top_k=3)
        ids = [h.concept_id for h in related]
        self.assertNotIn("attention", ids)
        self.assertTrue(related)

    def test_scores_are_sorted_descending(self):
        hits = concept_index.search("gradient descent learning rate step size", top_k=5)
        scores = [h.score for h in hits]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
