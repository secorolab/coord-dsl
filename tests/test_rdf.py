# SPDX-License-Identifier: MPL-2.0
"""Tests for the FSM RDF graph."""

import unittest
from pathlib import Path

from rdflib import Graph
from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.models.event_loop import EventLoopModel
from rdf_utils.resolver import install_resolver

from coord_dsl.rdf.event_loop import URL_EVT_LOOP_SHACL, add_event_loop
from coord_dsl.rdf.fsm import URL_FSM_SHACL, get_fsm_graph
from coord_dsl.registration import fsm_metamodel


MODEL = Path(__file__).parents[1] / "examples/models/fsm/example.fsm"


class FsmRdfTest(unittest.TestCase):
    def test_event_loop_conforms_to_shacl(self):
        install_resolver()
        model = fsm_metamodel().model_from_file(MODEL)
        graph = Graph()
        add_event_loop(graph, model.fsm.event_loop)

        self.assertTrue(
            check_shacl_constraints(
                graph,
                {URL_EVT_LOOP_SHACL: "ttl"},
            )
        )

    def test_example_conforms_to_fsm_and_event_loop_shacl(self):
        install_resolver()
        model = fsm_metamodel().model_from_file(MODEL)
        graph, _ = get_fsm_graph(model)
        event_loop = EventLoopModel(model.fsm.event_loop.uri, graph)
        self.assertEqual(len(event_loop.event_reactions), len(model.fsm.reactions))

        self.assertTrue(
            check_shacl_constraints(
                graph,
                {
                    URL_EVT_LOOP_SHACL: "ttl",
                    URL_FSM_SHACL: "ttl",
                },
            )
        )


if __name__ == "__main__":
    unittest.main()
