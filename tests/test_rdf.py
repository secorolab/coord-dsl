# SPDX-License-Identifier: MPL-2.0
"""Tests for the FSM RDF graph."""

import unittest
from pathlib import Path

from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.namespace import URL_SECORO_MM
from rdf_utils.resolver import install_resolver

from coord_dsl.rdf.fsm import get_fsm_graph
from coord_dsl.registration import fsm_metamodel


MODEL = Path(__file__).parents[1] / "examples/models/fsm/example.fsm"


class FsmRdfTest(unittest.TestCase):
    def test_example_conforms_to_fsm_and_event_loop_shacl(self):
        install_resolver()
        model = fsm_metamodel().model_from_file(MODEL)
        graph, _ = get_fsm_graph(model)

        self.assertTrue(
            check_shacl_constraints(
                graph,
                {
                    f"{URL_SECORO_MM}/behaviour/fsm.shacl.ttl": "ttl",
                    f"{URL_SECORO_MM}/behaviour/event_loop.shacl.ttl": "ttl",
                },
            )
        )


if __name__ == "__main__":
    unittest.main()
