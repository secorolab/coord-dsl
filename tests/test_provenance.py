# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Tests for the PROV-O document generators write beside their artifacts."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rdflib import Graph, Namespace
from rdflib.namespace import PROV, RDF

from coord_dsl.generators.bt.registration import bt_metamodel, gen_bt_cpp_file, gen_bt_xml_file
from coord_dsl.generators.fsm.registration import fsm_metamodel, gen_python
from coord_dsl.generators.provenance import DOCUMENT_NAME, source_paths

CDPROV = Namespace("https://secorolab.github.io/coord-dsl/provenance/")


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate the coord-dsl project root")


MODELS = _repo_root() / "examples" / "models"


class ProvenanceTest(unittest.TestCase):
    def _graph(self, directory):
        return Graph().parse(Path(directory) / DOCUMENT_NAME, format="json-ld")

    def test_records_sources_artifact_and_agent(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "py_pick" / "py_pick.btree"))
        with TemporaryDirectory() as directory:
            gen_bt_xml_file(None, model, Path(directory) / "py_pick.xml", False, False)
            graph = self._graph(directory)

        activity = CDPROV["activity/xml_generation/py_pick"]
        artifact = CDPROV["entity/generated/py_pick.xml"]

        self.assertIn((artifact, PROV.wasGeneratedBy, activity), graph)
        self.assertIn((activity, PROV.wasAssociatedWith, CDPROV["agent/coord_dsl"]), graph)
        self.assertIn((CDPROV["agent/coord_dsl"], RDF.type, PROV.SoftwareAgent), graph)
        # the FSMs the tree coordinates are sources too, not just the .btree
        self.assertEqual(
            set(graph.objects(activity, PROV.used)),
            {CDPROV["entity/source/py_pick.btree"],
             CDPROV["entity/source/right_arm.fsm"],
             CDPROV["entity/source/gripper.fsm"]},
        )
        for used in graph.objects(activity, PROV.used):
            self.assertTrue(str(graph.value(used, PROV.atLocation)).startswith("file://"))

    def test_targets_accumulate_into_one_document(self):
        """Each target is a separate CLI run, so the document has to be added to
        rather than replaced."""
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "py_pick" / "py_pick.btree"))
        with TemporaryDirectory() as directory:
            gen_bt_xml_file(None, model, Path(directory) / "py_pick.xml", False, False)
            gen_bt_cpp_file(None, model, Path(directory) / "py_pick.hpp", False, False)
            graph = self._graph(directory)

        for subject in (
            CDPROV["entity/generated/py_pick.xml"],
            CDPROV["entity/generated/py_pick.hpp"],
            CDPROV["activity/xml_generation/py_pick"],
            CDPROV["activity/cpp_generation/py_pick"],
        ):
            self.assertIn((subject, None, None), graph)

    def test_fsm_generation_is_recorded_too(self):
        model = fsm_metamodel().model_from_file(str(MODELS / "bt" / "fsms" / "gripper.fsm"))
        with TemporaryDirectory() as directory:
            gen_python(None, model, Path(directory) / "gripper.py", False, False)
            graph = self._graph(directory)

        self.assertIn(
            (
                CDPROV["entity/generated/gripper.py"],
                PROV.wasGeneratedBy,
                CDPROV["activity/python_generation/gripper"],
            ),
            graph,
        )

    def test_document_is_valid_prov_rdf(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "py_pick" / "py_pick.btree"))
        with TemporaryDirectory() as directory:
            gen_bt_xml_file(None, model, Path(directory) / "py_pick.xml", False, False)
            graph = Graph().parse(str(Path(directory) / DOCUMENT_NAME), format="json-ld")

        self.assertTrue(list(graph.triples((None, PROV.wasGeneratedBy, None))))
        self.assertTrue(list(graph.triples((None, PROV.wasAssociatedWith, None))))
        self.assertTrue(list(graph.triples((None, PROV.used, None))))

    def test_source_paths_resolve_to_real_files(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "py_pick" / "py_pick.btree"))

        paths = source_paths(model)
        self.assertTrue(all(path.is_file() for path in paths), paths)
        self.assertEqual(len(paths), len(set(paths)))


if __name__ == "__main__":
    unittest.main()
