# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Tests for the FSM graphviz target."""

import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from coord_dsl.generators.dot import fsm_dot, write_dot
from coord_dsl.rdf.fsm import get_fsm_graph
from coord_dsl.registration import fsm_metamodel


class FsmDotTest(unittest.TestCase):
    def _dot(self, source):
        model = fsm_metamodel().model_from_str(source)
        graph, _, fsm_ref = get_fsm_graph(model)
        return fsm_dot(graph, fsm_ref)

    def test_draws_states_and_the_reactions_that_join_them(self):
        dot = self._dot(
            'ns g = "https://example.test/"\n'
            "evt loop (ns=g) events { evt GRASP, evt DONE, evt NOTIFY }\n"
            "fsm (ns=g) gripper {\n"
            "  states { IDLE, GRASPING, GRASPED }\n"
            "  evt loop: <events>\n"
            "  start: <IDLE>\n"
            "  end:   <GRASPED>\n"
            "  transitions {\n"
            "    START { from: <IDLE>, to: <GRASPING> },\n"
            "    STOP  { from: <GRASPING>, to: <GRASPED> }\n"
            "  }\n"
            "  reactions {\n"
            "    ON_GRASP { when: <events.GRASP>, do: <START> },\n"
            "    ON_DONE  { when: <events.DONE>, do: <STOP>, fires { <events.NOTIFY> } }\n"
            "  }\n"
            "}\n"
        )
        self.assertTrue(dot.startswith('digraph "gripper" {'))
        self.assertIn(
            '"https://example.test/IDLE" -> "https://example.test/GRASPING"'
            ' [label="GRASP"];',
            dot,
        )
        self.assertIn('[label="DONE\\nfires NOTIFY"];', dot)
        self.assertIn('"__entry__" -> "https://example.test/IDLE";', dot)
        self.assertIn(
            '"https://example.test/GRASPED" [label="GRASPED", peripheries=2', dot
        )

    def test_transition_without_a_reaction_is_drawn_dead(self):
        dot = self._dot(
            'ns g = "https://example.test/"\n'
            "evt loop (ns=g) events { evt E }\n"
            "fsm (ns=g) m {\n"
            "  states { A, B, C }\n"
            "  evt loop: <events>\n"
            "  start: <A>\n"
            "  end:   <C>\n"
            "  transitions {\n"
            "    LIVE  { from: <A>, to: <B> },\n"
            "    NEVER { from: <B>, to: <C> }\n"
            "  }\n"
            "  reactions { ON_E { when: <events.E>, do: <LIVE> } }\n"
            "}\n"
        )
        self.assertIn('[label="NEVER", style=dashed', dot)


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
