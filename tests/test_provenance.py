# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Tests for the PROV-O document the generators write beside artifacts."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rdflib import Graph, Namespace
from rdflib.namespace import PROV, RDF

from coord_dsl.generators.provenance import DOCUMENT_NAME, source_paths
from coord_dsl.registration import (
    bt_metamodel,
    fsm_metamodel,
    gen_bt_xml_file,
    gen_python,
)

CDPROV = Namespace("https://secorolab.github.io/coord-dsl/provenance/")
MODELS = Path(__file__).resolve().parents[1] / "examples" / "models"
MODEL = MODELS / "fsm" / "example.fsm"
BT_MODEL = MODELS / "bt" / "coordinated_pick.btree"


class ProvenanceTest(unittest.TestCase):
    def test_fsm_generation_records_source_artifact_and_agent(self):
        model = fsm_metamodel().model_from_file(str(MODEL))
        with TemporaryDirectory() as directory:
            gen_python(None, model, Path(directory) / "ex_fsm.py", False, False)
            graph = Graph().parse(Path(directory) / DOCUMENT_NAME, format="json-ld")

        activity = CDPROV["activity/python_generation/example"]
        artifact = CDPROV["entity/generated/ex_fsm.py"]
        self.assertIn((artifact, PROV.wasGeneratedBy, activity), graph)
        self.assertIn(
            (activity, PROV.wasAssociatedWith, CDPROV["agent/coord_dsl"]), graph
        )
        self.assertIn((CDPROV["agent/coord_dsl"], RDF.type, PROV.SoftwareAgent), graph)
        self.assertEqual(
            set(graph.objects(activity, PROV.used)),
            {CDPROV["entity/source/example.fsm"]},
        )

    def test_bt_generation_records_the_imported_state_machine(self):
        model = bt_metamodel().model_from_file(str(BT_MODEL))
        with TemporaryDirectory() as directory:
            artifact = Path(directory) / "coordinated_pick.xml"
            gen_bt_xml_file(None, model, artifact, True, False)
            graph = Graph().parse(Path(directory) / DOCUMENT_NAME, format="json-ld")

        activity = CDPROV["activity/xml_generation/coordinated_pick"]
        self.assertIn(
            (
                CDPROV["entity/generated/coordinated_pick.xml"],
                PROV.wasGeneratedBy,
                activity,
            ),
            graph,
        )
        # the tree is generated from the machine's model as much as from its own
        self.assertEqual(
            set(graph.objects(activity, PROV.used)),
            {
                CDPROV["entity/source/coordinated_pick.btree"],
                CDPROV["entity/source/pick_coordination.fsm"],
            },
        )

    def test_source_paths_resolve_to_the_fsm_model(self):
        model = fsm_metamodel().model_from_file(str(MODEL))
        self.assertEqual(source_paths(model), [MODEL.resolve()])


if __name__ == "__main__":
    unittest.main()
