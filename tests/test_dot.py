# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Tests for the graphviz targets: an FSM's state machine, a BT's node tree."""

import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from coord_dsl.generators.bt.graph import get_bt_graph
from coord_dsl.generators.bt.registration import bt_metamodel
from coord_dsl.generators.common import write_dot
from coord_dsl.generators.dot import bt_dot, fsm_dot
from coord_dsl.generators.fsm.graph import get_fsm_graph
from coord_dsl.generators.fsm.registration import fsm_metamodel


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate the coord-dsl project root")


MODELS = _repo_root() / "examples" / "models"


class FsmDotTest(unittest.TestCase):
    def _dot(self, source):
        model = fsm_metamodel().model_from_str(source)
        graph, _, fsm_ref = get_fsm_graph(model)
        return fsm_dot(graph, fsm_ref)

    def test_draws_states_and_the_reactions_that_join_them(self):
        dot = self._dot(
            'ns g = "https://example.test/"\n'
            "fsm (ns=g) gripper {\n"
            "  states { IDLE, GRASPING, GRASPED }\n"
            "  events { GRASP, DONE, NOTIFY }\n"
            "  start: <IDLE>\n"
            "  end:   <GRASPED>\n"
            "  transitions {\n"
            "    START { from: <IDLE>, to: <GRASPING> },\n"
            "    STOP  { from: <GRASPING>, to: <GRASPED> }\n"
            "  }\n"
            "  reactions {\n"
            "    ON_GRASP { when: <GRASP>, do: <START> },\n"
            "    ON_DONE  { when: <DONE>, do: <STOP>, fires { <NOTIFY> } }\n"
            "  }\n"
            "}\n"
        )
        self.assertTrue(dot.startswith('digraph "gripper" {'))
        # an edge per reaction, labelled by the event that fires it
        self.assertIn('"https://example.test/IDLE" -> "https://example.test/GRASPING"'
                      ' [label="GRASP"];', dot)
        self.assertIn('[label="DONE\\nfires NOTIFY"];', dot)
        # the start state is entered from a point, the end state is doubled
        self.assertIn('"__entry__" -> "https://example.test/IDLE";', dot)
        self.assertIn('"https://example.test/GRASPED" [label="GRASPED", peripheries=2', dot)

    def test_transition_without_a_reaction_is_drawn_dead(self):
        dot = self._dot(
            'ns g = "https://example.test/"\n'
            "fsm (ns=g) m {\n"
            "  states { A, B, C }\n"
            "  events { E }\n"
            "  start: <A>\n"
            "  end:   <C>\n"
            "  transitions {\n"
            "    LIVE  { from: <A>, to: <B> },\n"
            "    NEVER { from: <B>, to: <C> }\n"
            "  }\n"
            "  reactions { ON_E { when: <E>, do: <LIVE> } }\n"
            "}\n"
        )
        self.assertIn('[label="NEVER", style=dashed', dot)


class BtDotTest(unittest.TestCase):
    def _dot(self, path):
        model = bt_metamodel().model_from_file(str(path))
        graph, _, root_ref = get_bt_graph(model)
        return bt_dot(graph, root_ref)

    def test_expands_each_subtree_instance_in_place(self):
        dot = self._dot(MODELS / "bt" / "warehouse_pick" / "fetch_and_place.btree")

        # main + perceive + grasp + navigate twice: the model runs navigate twice, so
        # both instances are drawn rather than sharing one picture
        self.assertEqual(dot.count("subgraph "), 5)
        self.assertIn('label="warehouse_pick";', dot)
        self.assertEqual(dot.count('label="subtree navigate as navigate";'), 2)
        self.assertIn('label="subtree grasp as grasp (autoremap)";', dot)
        # guards ride along in the node label
        self.assertIn("[skip-if: aborted == true]", dot)

    def test_subtree_instances_do_not_share_node_ids(self):
        dot = self._dot(MODELS / "bt" / "warehouse_pick" / "fetch_and_place.btree")
        drawn = [line.split('"')[1] for line in dot.splitlines() if "[label=" in line]

        self.assertEqual(len(drawn), len(set(drawn)), "two nodes share a dot id")

    def test_draws_the_fsms_a_tree_coordinates(self):
        dot = self._dot(MODELS / "bt" / "py_pick" / "py_pick.btree")

        self.assertIn("send right_arm.PICK\\nawait state PICKED", dot)
        self.assertIn("on-fail FAULT", dot)
        # each coordinated FSM is drawn beside the tree ...
        self.assertIn('label="FSM right_arm";', dot)
        self.assertIn('label="FSM gripper";', dot)

        # ... each node drops into the machine it drives, saying what it sends and what
        # it waits for; the arrow stops at the cluster so it never crosses the drawing
        self.assertIn('label="sends PICK\\nawaits PICKED", style=dashed', dot)
        self.assertIn('label="sends GRASP\\nawaits GRASPED", style=dashed', dot)
        self.assertEqual(dot.count('lhead="cluster_fsm_'), 2)

        # node, machine and awaited state share a colour
        def colour_of(needle):
            line = next(line for line in dot.splitlines() if needle in line)
            return line.split('color="')[-1].split('"')[0]

        right_arm = colour_of("send right_arm.PICK")
        gripper = colour_of("send gripper.GRASP")
        self.assertNotEqual(right_arm, gripper)
        self.assertEqual(colour_of('"PICKED"'), right_arm)
        self.assertEqual(colour_of('"GRASPED"'), gripper)
        self.assertIn(f'label="FSM right_arm";\n    style=rounded; color="{right_arm}"', dot)


class WriteDotTest(unittest.TestCase):
    def test_writes_source_and_renders_an_image(self):
        source = 'digraph g {\n  "a" -> "b";\n}\n'
        with TemporaryDirectory() as directory:
            plain = Path(directory) / "g.dot"
            write_dot(source, plain, "dot")
            self.assertEqual(plain.read_text(), source)

            if shutil.which("dot") is None:
                self.skipTest("graphviz is not installed")
            image = Path(directory) / "g.png"
            write_dot(source, image, "png")
            self.assertTrue(image.stat().st_size > 0)
            self.assertEqual(image.read_bytes()[:4], b"\x89PNG")


if __name__ == "__main__":
    unittest.main()
