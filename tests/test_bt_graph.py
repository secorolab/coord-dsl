# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Regression tests for behaviour-tree RDF graph validation."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rdflib import Literal, Namespace, RDF, URIRef
from textx.exceptions import TextXSyntaxError

from coord_dsl.generators.bt.graph import URI_MM_BT, URI_MM_DATAFLOW, get_bt_graph
from coord_dsl.generators.bt.registration import (
    bt_metamodel,
    gen_bt_cpp_file,
    gen_bt_python_file,
    gen_bt_xml_file,
)


NS_BT = Namespace(URI_MM_BT)
NS_DF = Namespace(URI_MM_DATAFLOW)


def _repo_root() -> Path:
    """Locate the project root by its pyproject.toml marker, like pytest's rootdir."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate the coord-dsl project root")


MODELS = _repo_root() / "examples" / "models"


def parse(source):
    return bt_metamodel().model_from_str(source)


class BtGraphTest(unittest.TestCase):
    def test_generates_btcpp_header(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "fetch_and_place.btree"))
        with TemporaryDirectory() as directory:
            output = Path(directory) / "warehouse_pick.hpp"
            gen_bt_cpp_file(None, model, output, False, False)
            header = output.read_text()

        self.assertIn("class WarehousePickRuntime", header)
        self.assertIn("virtual BT::NodeStatus on_battery_ok(BT::TreeNode& node) = 0;", header)
        self.assertIn('registerSimpleCondition(\n      "battery_ok"', header)
        self.assertIn("return runtime.on_battery_ok(node);", header)
        self.assertIn('BT::InputPort("min_level")', header)
        self.assertIn('BT::InputPort("start_event")', header)
        self.assertIn("createTreeFromFile", header)
        self.assertNotIn("<BehaviorTree", header)

    def test_loop_uses_btcpp_string_loop(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "fetch_and_place.btree"))
        with TemporaryDirectory() as directory:
            output = Path(directory) / "warehouse_pick.xml"
            gen_bt_xml_file(None, model, output, False, False)
            xml = output.read_text()

        self.assertIn("<LoopString", xml)

    def test_declared_fsm_instances_are_included_in_jsonld(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "dual_arm_fsms.btree"))

        graph, _, _ = get_bt_graph(model)
        fsm_instances = set(graph.subjects(RDF.type, NS_BT.FSMInstance))

        self.assertEqual(
            {str(graph.value(node, NS_BT["of-fsm"])) for node in fsm_instances},
            {
                "https://secorolab.github.io/models/coordination/fsm/left-arm/left_arm",
                "https://secorolab.github.io/models/coordination/fsm/right-arm/right_arm",
            },
        )
        self.assertIn(
            (
                URIRef("https://secorolab.github.io/models/coordination/fsm/left-arm/left_arm"),
                RDF.type,
                Namespace("https://secorolab.github.io/metamodels/behaviour/fsm#").FSM,
            ),
            graph,
        )
        self.assertEqual(
            {str(script) for script in graph.objects(None, NS_BT["guard-script"])},
            {
                "coordination_complete := true",
                "coordination_failed := true",
                "left_arm_failed := true",
                "left_arm_fault == true",
                "right_arm_failed := true",
                "right_arm_fault == true",
            },
        )

    def test_handover_coordinates_fsm_phases(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "arm_handover_fsms.btree"))
        sequence = model.main_tree.root
        self.assertTrue(all(node.fsm is node.await_fsm for node in sequence.children))

        graph, _, _ = get_bt_graph(model)
        fsm_instances = set(graph.subjects(RDF.type, NS_BT.FSMInstance))
        self.assertEqual(len(fsm_instances), 2)
        self.assertEqual(
            {str(graph.value(node, NS_BT["instance-name"])) for node in fsm_instances},
            {"right_arm", "left_arm"},
        )
        event_nodes = set(graph.subjects(RDF.type, NS_BT.FSMEvent))
        self.assertEqual(
            {graph.value(node, NS_BT["on-fsm-instance"]) for node in event_nodes},
            fsm_instances,
        )
        self.assertEqual(
            {str(graph.value(node, NS_BT["of-event"])) for node in event_nodes},
            {
                "https://secorolab.github.io/models/coordination/fsm/right-arm/PICK",
                "https://secorolab.github.io/models/coordination/fsm/right-arm/HANDOVER",
                "https://secorolab.github.io/models/coordination/fsm/left-arm/TAKE_POSE",
                "https://secorolab.github.io/models/coordination/fsm/left-arm/PLACE",
            },
        )
        self.assertEqual(
            {str(graph.value(node, NS_BT["await-target"])) for node in event_nodes},
            {
                "https://secorolab.github.io/models/coordination/fsm/right-arm/PICK_DONE",
                "https://secorolab.github.io/models/coordination/fsm/right-arm/HANDOVER_DONE",
                "https://secorolab.github.io/models/coordination/fsm/left-arm/TAKE_POSE_DONE",
                "https://secorolab.github.io/models/coordination/fsm/left-arm/PLACE_DONE",
            },
        )
        self.assertEqual(
            {str(graph.value(node, NS_BT["await-kind"])) for node in event_nodes}, {"event"}
        )

    def test_fsm_events_render_to_xml_and_cpp(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "arm_handover_fsms.btree"))
        with TemporaryDirectory() as directory:
            xml_out = Path(directory) / "arm_handover.xml"
            hpp_out = Path(directory) / "arm_handover.hpp"
            gen_bt_xml_file(None, model, xml_out, False, False)
            gen_bt_cpp_file(None, model, hpp_out, False, False)
            xml = xml_out.read_text()
            header = hpp_out.read_text()

        self.assertIn('<FSMEvent fsm="right_arm" event="PICK" await="PICK_DONE" await_kind="event" />', xml)
        self.assertIn('#include "left_arm.hpp"', header)
        self.assertIn("class FSMEventNode : public BT::StatefulActionNode", header)
        self.assertIn("virtual void step_left_arm(struct fsm_nbx* fsm) = 0;", header)
        self.assertIn("if (event == \"PICK\") return right_arm::PICK;", header)
        self.assertIn("if (state == \"PICKED\") return right_arm::PICKED;", header)
        self.assertIn('factory.registerNodeType<FSMEventNode>("FSMEvent", &runtime);', header)

    def test_await_state_and_on_fail_render(self):
        source = (
            'ns n = "https://example.test/"\n'
            'fsm arm = "left_arm.fsm"\n'
            "main btree (ns=n) t {\n"
            "  send <arm.TAKE_POSE> await <arm.AT_TAKE_POSE> on-fail <arm.PLACED>\n"
            "}\n"
        )
        model = bt_metamodel().model_from_str(source)
        model._tx_filename = str(MODELS / "bt" / "t.btree")
        with TemporaryDirectory() as directory:
            xml_out = Path(directory) / "t.xml"
            hpp_out = Path(directory) / "t.hpp"
            gen_bt_xml_file(None, model, xml_out, False, False)
            gen_bt_cpp_file(None, model, hpp_out, False, False)
            xml = xml_out.read_text()

        self.assertIn('await="AT_TAKE_POSE"', xml)
        self.assertIn('await_kind="state"', xml)
        self.assertIn('on_fail="PLACED"', xml)
        self.assertIn('on_fail_kind="state"', xml)

    def test_fsm_events_render_to_pytrees(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "py_pick.btree"))
        with TemporaryDirectory() as directory:
            output = Path(directory) / "py_pick.py"
            gen_bt_python_file(None, model, output, False, False)
            module = output.read_text()

        self.assertIn("import right_arm", module)
        self.assertIn("class PyPickRuntime", module)
        self.assertIn("class _FSMEvent(py_trees.behaviour.Behaviour)", module)
        self.assertIn("def step_right_arm(self, fsm):", module)
        self.assertIn("py_trees.composites.Sequence(", module)
        self.assertIn("_FSMEvent('right_arm.PICK', runtime, 'right_arm', 'PICK', 'PICKED', 'state')", module)
        self.assertIn("on_fail='FAULT', on_fail_kind='state'", module)
        # the generated module must be syntactically valid Python
        compile(module, "py_pick.py", "exec")

    def test_pytrees_renders_guards(self):
        # arm_handover uses [on-success]/[on-failure] guards -> _Guarded wrapper
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "arm_handover_fsms.btree"))
        with TemporaryDirectory() as directory:
            output = Path(directory) / "arm_handover.py"
            gen_bt_python_file(None, model, output, False, False)
            module = output.read_text()

        self.assertIn("class _Guarded(py_trees.decorators.Decorator)", module)
        self.assertIn(
            "post=[(py_trees.common.Status.FAILURE, lambda: _bb_set('handover_failed', True)), "
            "(py_trees.common.Status.SUCCESS, lambda: _bb_set('handover_complete', True))]",
            module,
        )
        compile(module, "arm_handover.py", "exec")

    def test_pytrees_translates_precondition_guards(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "dual_arm_fsms.btree"))
        with TemporaryDirectory() as directory:
            output = Path(directory) / "dual_arm.py"
            gen_bt_python_file(None, model, output, False, False)
            module = output.read_text()

        self.assertIn(
            "pre=[(py_trees.common.Status.FAILURE, lambda: _bb_get('left_arm_fault') == True)]",
            module,
        )
        compile(module, "dual_arm.py", "exec")

    def test_pytrees_rejects_unmapped_guards(self):
        # skip-if has no py_trees analogue (no SKIPPED status) -> still rejected
        model = parse(
            """ns n = \"https://example.test/\"\nnode action ping\nmain btree (ns=n) root { sequence { ping [skip-if: \"done == true\"] } }"""
        )
        model._tx_filename = str(MODELS / "bt" / "t.btree")
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(NotImplementedError, "guard 'skip-if'"):
                gen_bt_python_file(None, model, Path(directory) / "x.py", False, False)

    def test_main_tree_is_an_explicit_model_field(self):
        model = parse(
            """ns n = \"https://example.test/\"\nnode action ping\nmain btree (ns=n) root { ping }\nbtree (ns=n) child { subtree <root> }"""
        )

        self.assertEqual(model.main_tree.name, "root")
        self.assertIs(model.trees[0].root.tree, model.main_tree)

    def test_requires_exactly_one_main_tree(self):
        sources = (
            """ns n = \"https://example.test/\"\nnode action ping\nbtree (ns=n) alpha { ping }""",
            """ns n = \"https://example.test/\"\nnode action ping\nmain btree (ns=n) alpha { ping }\nmain btree (ns=n) beta { ping }""",
        )

        for source in sources:
            with self.subTest(source=source), self.assertRaises(TextXSyntaxError):
                parse(source)

    def test_tree_uris_follow_tree_identity_not_name(self):
        model = parse(
            """ns a = \"https://a.test/\"\nns b = \"https://b.test/\"\nnode action ping\nmain btree (ns=a) same { ping }\nbtree (ns=b) same { ping }"""
        )

        graph, _, main = get_bt_graph(model)
        trees = set(graph.subjects(RDF.type, NS_BT.BehaviourTree))

        self.assertEqual(main, Namespace("https://a.test/").same)
        self.assertEqual(trees, {Namespace("https://a.test/").same, Namespace("https://b.test/").same})

    def test_rejects_duplicate_guards_and_ports(self):
        sources = (
            ("guard", """ns n = \"https://example.test/\"\nnode action ping\nmain btree (ns=n) root { sequence [skip-if: \"one\", skip-if: \"two\"] { ping } }"""),
            ("binding", """ns n = \"https://example.test/\"\nnode action ping\nmain btree (ns=n) root { sequence (foo: 1, foo: 2) { ping } }"""),
            ("declaration", """ns n = \"https://example.test/\"\nnode action ping { in foo: string, out foo: string }\nmain btree (ns=n) root { ping }"""),
        )

        for label, source in sources:
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "Duplicate"):
                get_bt_graph(parse(source))

    def test_dataflow_bindings_are_not_tree_concepts(self):
        model = parse(
            'ns n = "https://example.test/"\n'
            'node action ping { in message: string }\n'
            'main btree (ns=n) root { sequence { ping(message: "fixed") ping(message: {shared}) } }'
        )

        graph, _, _ = get_bt_graph(model)
        behaviour = Namespace("https://example.test/")["behaviour-ping"]
        parameter = graph.value(behaviour, NS_DF["has-parameter"])
        arguments = set(graph.objects(None, NS_DF["has-argument"]))

        self.assertIn((parameter, RDF.type, NS_DF.Parameter), graph)
        self.assertEqual(graph.value(parameter, NS_DF.name), Literal("message"))
        self.assertEqual(graph.value(parameter, NS_DF.direction), NS_DF.Input)
        self.assertEqual({graph.value(argument, RDF.value) for argument in arguments}, {Literal("fixed"), None})
        reference = next(
            graph.value(argument, NS_DF.references)
            for argument in arguments
            if graph.value(argument, NS_DF.references)
        )
        self.assertEqual(graph.value(reference, RDF.type), NS_DF.DataReference)
        self.assertEqual(graph.value(reference, NS_DF.name), Literal("shared"))
        self.assertFalse(
            {
                NS_BT["has-port"],
                NS_BT["port"],
                NS_BT["port-name"],
                NS_BT["port-direction"],
                NS_BT["port-type"],
                NS_BT["port-value"],
                NS_BT["blackboard-key"],
            }
            & set(graph.predicates())
        )
