# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
"""Tests for the py_trees and BehaviorTree.CPP targets."""

import shutil
import unittest
from pathlib import Path
from xml.etree import ElementTree

from coord_dsl.generators.bt import gen_dot, gen_json, gen_python_code, gen_xml
from coord_dsl.generators.dot import write_dot
from coord_dsl.rdf.bt import get_bt_graph
from coord_dsl.registration import bt_metamodel

MODELS = Path(__file__).parents[1] / "examples/models/bt"

try:
    import py_trees

    HAVE_PY_TREES = True
except ImportError:
    HAVE_PY_TREES = False


def _ir(name):
    mm = bt_metamodel()
    graph, entry = get_bt_graph(mm.model_from_file(str(MODELS / f"{name}.btree")))
    return gen_json(graph, entry)


def _kinds(node):
    yield node["kind"]
    for child in node.get("children", ()):
        yield from _kinds(child)


class BtIrTest(unittest.TestCase):
    def test_entry_and_trees_are_named(self):
        ir = _ir("warehouse")
        self.assertEqual(ir["entry"], "warehouse_order")
        self.assertEqual(
            [tree["name"] for tree in ir["trees"]],
            ["fetch_item", "go_to_shelf", "reach_shelf", "warehouse_order"],
        )

    def test_a_subtree_is_read_as_the_tree_it_names(self):
        ir = _ir("pick")
        root = next(t for t in ir["trees"] if t["name"] == "pick")["root"]
        self.assertEqual(
            root["children"][0],
            {
                "kind": "subtree",
                "uri": root["children"][0]["uri"],
                "tree": "approach_object",
            },
        )

    def test_every_leaf_names_an_action_or_a_flag(self):
        ir = _ir("warehouse")
        self.assertEqual(
            {action["name"] for action in ir["actions"]},
            {
                "recharge",
                "drive_to_shelf",
                "clear_obstacle",
                "replan_route",
                "pick_item",
                "drive_to_dropoff",
                "place_item",
            },
        )
        self.assertEqual(
            {flag["name"] for flag in ir["flags"]},
            {"battery_ok", "shelf_reachable", "item_held", "at_dropoff"},
        )

    def test_parallel_carries_both_thresholds(self):
        ir = _ir("pick")
        root = next(t for t in ir["trees"] if t["name"] == "pick")["root"]
        parallel = next(c for c in root["children"] if c["kind"] == "parallel")
        # the book fails a parallel once N - M + 1 children have failed
        self.assertEqual(parallel["threshold"], 2)
        self.assertEqual(parallel["failure_threshold"], 1)


class BtFsmCouplingTest(unittest.TestCase):
    def test_a_state_machine_is_a_node_of_the_tree(self):
        ir = _ir("coordinated_pick")
        self.assertEqual(
            ir["state_machines"],
            [
                {
                    "name": "pick_coordination",
                    "uri": "https://secorolab.github.io/models/fsm/"
                    "pick_coordination/pick_coordination",
                }
            ],
        )
        # like a subtree, the machine stands in the child slot as itself
        guarded = next(t for t in ir["trees"] if t["name"] == "run_coordination")
        self.assertEqual(
            [child["kind"] for child in guarded["root"]["children"]],
            ["condition", "state_machine"],
        )

    def test_a_condition_guards_the_state_machine(self):
        # a machine reports no status, so a selector puts a flag check above it
        ir = _ir("coordinated_pick")
        guarded = next(t for t in ir["trees"] if t["name"] == "run_coordination")
        self.assertEqual(guarded["root"]["kind"], "selector")
        self.assertFalse(guarded["root"]["memory"])

    def test_a_condition_reads_the_flag_the_state_machine_declares(self):
        ir = _ir("coordinated_pick")
        # importing the .fsm makes these the FSM's own flags, not same-named copies
        self.assertEqual(
            [flag["uri"] for flag in ir["flags"]],
            [
                "https://secorolab.github.io/models/fsm/pick_coordination/object_grasped",
                "https://secorolab.github.io/models/fsm/pick_coordination/object_visible",
            ],
        )


class BtXmlTest(unittest.TestCase):
    def setUp(self):
        self.root = ElementTree.fromstring(gen_xml(_ir("warehouse")))

    def test_the_entry_tree_is_the_one_to_execute(self):
        self.assertEqual(self.root.get("BTCPP_format"), "4")
        self.assertEqual(self.root.get("main_tree_to_execute"), "warehouse_order")

    def test_every_subtree_reference_resolves(self):
        declared = {t.get("ID") for t in self.root.findall("BehaviorTree")}
        referenced = {s.get("ID") for s in self.root.iter("SubTree")}
        self.assertTrue(referenced)
        self.assertLessEqual(referenced, declared)

    def test_a_subtree_shares_the_parent_blackboard(self):
        # flags are event-loop scoped, so they must cross the subtree boundary
        for subtree in self.root.iter("SubTree"):
            self.assertEqual(subtree.get("_autoremap"), "true")

    def test_memory_picks_the_reactive_or_remembering_composite(self):
        tags = {e.tag for e in self.root.iter()}
        self.assertIn("ReactiveFallback", tags)  # selector, memory defaults to false
        self.assertIn("Sequence", tags)  # sequence (memory=true)

    def test_a_state_machine_becomes_a_node_to_register(self):
        root = ElementTree.fromstring(gen_xml(_ir("coordinated_pick")))
        self.assertTrue(any(e.tag == "pick_coordination" for e in root.iter()))
        declared = {a.get("ID") for a in root.iter("Action")}
        self.assertIn("pick_coordination", declared)

    def test_a_condition_becomes_a_flag_check(self):
        checks = {c.get("code") for c in self.root.iter("ScriptCondition")}
        self.assertIn("battery_ok == true", checks)


class BtDotTest(unittest.TestCase):
    def test_every_tree_gets_a_cluster(self):
        source = gen_dot(_ir("warehouse"))
        for tree in ("warehouse_order", "fetch_item", "go_to_shelf", "reach_shelf"):
            self.assertIn(f'subgraph "cluster_{tree}"', source)

    def test_a_subtree_edge_points_at_its_cluster(self):
        source = gen_dot(_ir("warehouse"))
        self.assertIn('lhead="cluster_fetch_item"', source)

    def test_a_state_machine_is_drawn_as_itself(self):
        source = gen_dot(_ir("coordinated_pick"))
        self.assertIn('"fsm__pick_coordination" [label="pick_coordination"', source)

    @unittest.skipUnless(shutil.which("dot"), "graphviz is not installed")
    def test_graphviz_accepts_the_source(self):
        for model in ("pick", "warehouse", "coordinated_pick"):
            with self.subTest(model=model):
                out = Path(self.tmp) / f"{model}.svg"
                write_dot(gen_dot(_ir(model)), out, "svg")
                self.assertTrue(out.stat().st_size > 0)

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)


class BtPythonTest(unittest.TestCase):
    def test_generated_module_is_valid_python(self):
        compile(gen_python_code(_ir("warehouse")), "warehouse.py", "exec")

    def test_a_threshold_py_trees_cannot_express_is_refused(self):
        mm = bt_metamodel()
        model = mm.model_from_str(
            'ns g = "https://example.test/"\n'
            "behaviours (ns=g) b { action a1, action a2, action a3 }\n"
            "btree (ns=g) t {\n"
            "  parallel (threshold=2) { <b.a1>, <b.a2>, <b.a3> }\n"
            "}\n"
        )
        graph, entry = get_bt_graph(model)
        with self.assertRaises(ValueError) as caught:
            gen_python_code(gen_json(graph, entry))
        self.assertIn("SuccessOnOne", str(caught.exception))

    @unittest.skipUnless(HAVE_PY_TREES, "py_trees is not installed")
    def test_the_generated_tree_ticks(self):
        namespace = {}
        # running the generated module is the check
        exec(gen_python_code(_ir("warehouse")), namespace)  # noqa: S102

        board = py_trees.blackboard.Client(name="test")
        for flag in namespace["FLAG_IRI"]:
            board.register_key(key=flag, access=py_trees.common.Access.WRITE)
            board.set(flag, True)

        class Stub(py_trees.behaviour.Behaviour):
            def update(self):
                return py_trees.common.Status.SUCCESS

        behaviours = {n: (lambda n=n: Stub(n)) for n in namespace["ACTION_IRI"]}
        root = namespace["warehouse_order"](behaviours)
        py_trees.trees.BehaviourTree(root).tick()
        self.assertEqual(root.status, py_trees.common.Status.SUCCESS)


if __name__ == "__main__":
    unittest.main()
