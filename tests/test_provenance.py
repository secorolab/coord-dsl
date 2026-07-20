# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Tests for the PROV-O document generators write beside their artifacts."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from coord_dsl.generators.bt.registration import bt_metamodel, gen_bt_cpp_file, gen_bt_xml_file
from coord_dsl.generators.fsm.registration import fsm_metamodel, gen_python
from coord_dsl.generators.provenance import DOCUMENT_NAME, source_paths


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate the coord-dsl project root")


MODELS = _repo_root() / "examples" / "models"


class ProvenanceTest(unittest.TestCase):
    def _graph(self, directory):
        document = json.loads((Path(directory) / DOCUMENT_NAME).read_text())
        return {node["@id"]: node for node in document["@graph"]}

    def test_records_sources_artifact_and_agent(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "py_pick" / "py_pick.btree"))
        with TemporaryDirectory() as directory:
            gen_bt_xml_file(None, model, Path(directory) / "py_pick.xml", False, False)
            nodes = self._graph(directory)

        activity = nodes["cdprov:activity/xml_generation/py_pick"]
        artifact = nodes["cdprov:entity/generated/py_pick.xml"]

        self.assertEqual(artifact["wasGeneratedBy"], activity["@id"])
        self.assertEqual(activity["wasAssociatedWith"], "cdprov:agent/coord_dsl")
        self.assertIn("prov:SoftwareAgent", nodes["cdprov:agent/coord_dsl"]["@type"])
        # the FSMs the tree coordinates are sources too, not just the .btree
        self.assertEqual(
            set(activity["used"]),
            {"cdprov:entity/source/py_pick.btree",
             "cdprov:entity/source/right_arm.fsm",
             "cdprov:entity/source/gripper.fsm"},
        )
        for used in activity["used"]:
            self.assertTrue(nodes[used]["atLocation"].startswith("file://"))

    def test_targets_accumulate_into_one_document(self):
        """Each target is a separate CLI run, so the document has to be added to
        rather than replaced."""
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "py_pick" / "py_pick.btree"))
        with TemporaryDirectory() as directory:
            gen_bt_xml_file(None, model, Path(directory) / "py_pick.xml", False, False)
            gen_bt_cpp_file(None, model, Path(directory) / "py_pick.hpp", False, False)
            nodes = self._graph(directory)

        self.assertIn("cdprov:entity/generated/py_pick.xml", nodes)
        self.assertIn("cdprov:entity/generated/py_pick.hpp", nodes)
        self.assertIn("cdprov:activity/xml_generation/py_pick", nodes)
        self.assertIn("cdprov:activity/cpp_generation/py_pick", nodes)

    def test_fsm_generation_is_recorded_too(self):
        model = fsm_metamodel().model_from_file(str(MODELS / "bt" / "fsms" / "gripper.fsm"))
        with TemporaryDirectory() as directory:
            gen_python(None, model, Path(directory) / "gripper.py", False, False)
            nodes = self._graph(directory)

        self.assertEqual(
            nodes["cdprov:entity/generated/gripper.py"]["wasGeneratedBy"],
            "cdprov:activity/python_generation/gripper",
        )

    def test_document_is_valid_prov_rdf(self):
        from rdflib import Graph, Namespace

        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "py_pick" / "py_pick.btree"))
        with TemporaryDirectory() as directory:
            gen_bt_xml_file(None, model, Path(directory) / "py_pick.xml", False, False)
            graph = Graph().parse(str(Path(directory) / DOCUMENT_NAME), format="json-ld")

        prov = Namespace("http://www.w3.org/ns/prov#")
        self.assertTrue(list(graph.triples((None, prov.wasGeneratedBy, None))))
        self.assertTrue(list(graph.triples((None, prov.wasAssociatedWith, None))))
        self.assertTrue(list(graph.triples((None, prov.used, None))))

    def test_source_paths_resolve_to_real_files(self):
        model = bt_metamodel().model_from_file(str(MODELS / "bt" / "py_pick" / "py_pick.btree"))

        paths = source_paths(model)
        self.assertTrue(all(path.is_file() for path in paths), paths)
        self.assertEqual(len(paths), len(set(paths)))


if __name__ == "__main__":
    unittest.main()
