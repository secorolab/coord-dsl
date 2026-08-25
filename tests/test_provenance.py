# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Tests for the PROV-O document FSM generators write beside artifacts."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rdflib import Graph, Namespace
from rdflib.namespace import DCTERMS, PROV, RDF

from coord_dsl.generators.provenance import DOCUMENT_NAME, source_paths
from coord_dsl.registration import fsm_metamodel, gen_python

CDPROV = Namespace("https://secorolab.github.io/coord-dsl/provenance/")
# Agents and files are shared with motion-spec-dsl's document; only activities stay local.
MSPROV = Namespace("https://secorolab.github.io/motion-spec/provenance/")
MS_PROV = Namespace("https://secorolab.github.io/metamodels/motion-spec/prov#")
MODEL = Path(__file__).resolve().parents[1] / "examples" / "models" / "fsm" / "example.fsm"


class ProvenanceTest(unittest.TestCase):
    def test_fsm_generation_records_source_artifact_and_agent(self):
        model = fsm_metamodel().model_from_file(str(MODEL))
        with TemporaryDirectory() as directory:
            gen_python(None, model, Path(directory) / "ex_fsm.py", False, False)
            graph = Graph().parse(Path(directory) / DOCUMENT_NAME, format="json-ld")

        activity = CDPROV["activity/python_generation/example"]
        artifact = MSPROV["entity/generated/ex_fsm.py"]
        self.assertIn((artifact, PROV.wasGeneratedBy, activity), graph)
        self.assertIn((activity, RDF.type, MS_PROV.SpecCompilation), graph)
        self.assertIn((activity, PROV.wasAssociatedWith, MSPROV["agent/coord_dsl"]), graph)
        self.assertIn((MSPROV["agent/coord_dsl"], RDF.type, PROV.SoftwareAgent), graph)
        self.assertEqual(
            set(graph.objects(activity, PROV.used)),
            {MSPROV["entity/source/example.fsm"]},
        )

    def test_cdprov_mints_no_vocabulary(self):
        """The tool version is dcterms:hasVersion; cdprov names only this run's own instances."""
        model = fsm_metamodel().model_from_file(str(MODEL))
        with TemporaryDirectory() as directory:
            gen_python(None, model, Path(directory) / "ex_fsm.py", False, False)
            graph = Graph().parse(Path(directory) / DOCUMENT_NAME, format="json-ld")

        self.assertNotIn(CDPROV.version, set(graph.predicates()))
        minted = {str(term)[len(CDPROV) :] for term in graph.all_nodes() if CDPROV in term}
        minted |= {str(p)[len(CDPROV) :] for p in graph.predicates() if CDPROV in p}
        self.assertTrue(all("/" in local for local in minted), minted)
        versions = set(graph.objects(MSPROV["agent/coord_dsl"], DCTERMS.hasVersion))
        self.assertTrue(len(versions) <= 1)

    def test_source_paths_resolve_to_the_fsm_model(self):
        model = fsm_metamodel().model_from_file(str(MODEL))
        self.assertEqual(source_paths(model), [MODEL.resolve()])


if __name__ == "__main__":
    unittest.main()
