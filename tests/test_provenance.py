# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Tests for the PROV-O document generators write beside their artifacts."""

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.models.vocab import URI_PROV_EXT_TYPE_TRANSFORMATION
from rdf_utils.namespace import URL_MM_PROV_EXT_SHACL, URL_MM_PROV_SHACL
from rdflib import Graph, URIRef
from rdflib.namespace import PROV, RDF, SDO

from coord_dsl.generators.provenance import (
    AGENT,
    CDPROV,
    DOCUMENT_NAME,
    _installed_package,
    record,
    source_paths,
)
from coord_dsl.registration import fsm_metamodel, gen_cpp, gen_python

MODEL = (
    Path(__file__).resolve().parents[1] / "examples" / "models" / "fsm" / "example.fsm"
)
PYTHON_GENERATION = CDPROV["activity/python_generation/ex_fsm.py"]
SHAPES = {URL_MM_PROV_SHACL: "turtle", URL_MM_PROV_EXT_SHACL: "turtle"}


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.model = fsm_metamodel().model_from_file(str(MODEL))
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def document(self) -> Graph:
        return Graph().parse(self.directory / DOCUMENT_NAME, format="json-ld")

    def test_generation_is_a_transformation_of_the_model_by_the_package(self):
        gen_python(None, self.model, self.directory / "ex_fsm.py", False, False)
        graph = self.document()

        self.assertIn(
            (PYTHON_GENERATION, RDF.type, URI_PROV_EXT_TYPE_TRANSFORMATION), graph
        )
        sources = set(graph.objects(PYTHON_GENERATION, PROV.used))
        self.assertEqual(len(sources), 1)
        source = sources.pop()
        self.assertEqual(source, URIRef(MODEL.as_uri()))
        self.assertEqual(graph.value(source, PROV.atLocation), source)
        self.assertIn(
            (
                CDPROV["entity/generated/ex_fsm.py"],
                PROV.wasGeneratedBy,
                PYTHON_GENERATION,
            ),
            graph,
        )
        self.assertIn((PYTHON_GENERATION, PROV.wasAssociatedWith, AGENT), graph)
        self.assertEqual(str(graph.value(AGENT, SDO.name)), "coord-dsl")
        self.assertLess(
            graph.value(PYTHON_GENERATION, PROV.startedAtTime),
            graph.value(PYTHON_GENERATION, PROV.endedAtTime),
        )
        check_shacl_constraints(graph, SHAPES)

    def test_targets_accumulate_and_a_rerun_restates_only_its_own_file(self):
        gen_python(None, self.model, self.directory / "ex_fsm.py", False, False)
        gen_cpp(None, self.model, self.directory / "ex_fsm.hpp", False, False)
        first = self.document().value(PYTHON_GENERATION, PROV.endedAtTime)
        gen_python(None, self.model, self.directory / "ex_fsm.py", False, False)
        graph = self.document()

        self.assertEqual(
            set(graph.subjects(RDF.type, URI_PROV_EXT_TYPE_TRANSFORMATION)),
            {PYTHON_GENERATION, CDPROV["activity/cpp_generation/ex_fsm.hpp"]},
        )
        self.assertGreater(graph.value(PYTHON_GENERATION, PROV.endedAtTime), first)
        self.assertEqual(len(list(graph.objects(AGENT, SDO.softwareVersion))), 1)
        self.assertEqual(
            len(list(graph.subjects(PROV.atLocation, URIRef(MODEL.as_uri())))), 1
        )
        check_shacl_constraints(graph, SHAPES)

    def test_a_tool_records_a_file_it_wrote(self):
        started = datetime.now(timezone.utc)
        header = self.directory / "ex_fsm.hpp"
        header.write_text("// header\n")
        self.assertEqual(
            record(self.model, "cpp", header, started), self.directory / DOCUMENT_NAME
        )
        self.assertIn(
            (
                CDPROV["entity/generated/ex_fsm.hpp"],
                PROV.wasGeneratedBy,
                CDPROV["activity/cpp_generation/ex_fsm.hpp"],
            ),
            self.document(),
        )

    def test_source_paths_resolve_to_the_fsm_model(self):
        self.assertEqual(source_paths(self.model), [MODEL.resolve()])

    def test_sources_with_the_same_name_remain_distinct(self):
        first = self.directory / "a" / "shared.fsm"
        second = self.directory / "b" / "shared.fsm"
        first.parent.mkdir()
        second.parent.mkdir()
        first.touch()
        second.touch()
        imported = [
            SimpleNamespace(_tx_filename=str(first), imports=[]),
            SimpleNamespace(_tx_filename=str(second), imports=[]),
        ]
        model = SimpleNamespace(
            _tx_filename=None,
            imports=[SimpleNamespace(_tx_loaded_models=imported)],
        )
        artifact = self.directory / "generated.py"
        artifact.touch()

        record(model, "python", artifact, datetime.now(timezone.utc))
        graph = self.document()
        activity = CDPROV["activity/python_generation/generated.py"]
        sources = set(graph.objects(activity, PROV.used))

        self.assertEqual(sources, {URIRef(first.as_uri()), URIRef(second.as_uri())})
        self.assertEqual(
            {str(graph.value(source, PROV.atLocation)) for source in sources},
            {first.as_uri(), second.as_uri()},
        )

    def test_installed_package_reads_vcs_and_local_install_revisions(self):
        vcs = SimpleNamespace(
            version="1.2.3",
            read_text=lambda _: (
                '{"url": "https://example.test/repo", '
                '"vcs_info": {"commit_id": "abc123", "vcs": "git"}}'
            ),
        )
        with patch("coord_dsl.generators.provenance.distribution", return_value=vcs):
            self.assertEqual(_installed_package(), ("1.2.3", "abc123"))

        source_root = Path(__file__).resolve().parents[1]
        local = SimpleNamespace(
            version="1.2.3",
            read_text=lambda _: (
                f'{{"url": "{source_root.as_uri()}", "dir_info": {{"editable": true}}}}'
            ),
        )
        with (
            patch("coord_dsl.generators.provenance.distribution", return_value=local),
            patch(
                "coord_dsl.generators.provenance._git_revision",
                return_value="def456-dirty",
            ),
        ):
            self.assertEqual(_installed_package(), ("1.2.3", "def456-dirty"))

    def test_installed_package_ignores_an_unrelated_editable_install(self):
        package = SimpleNamespace(
            version="1.2.3",
            read_text=lambda _: (
                '{"url": "file:///an/unrelated/checkout", '
                '"dir_info": {"editable": true}}'
            ),
        )
        with patch(
            "coord_dsl.generators.provenance.distribution", return_value=package
        ):
            self.assertEqual(_installed_package(), (None, None))

    def test_installed_package_without_source_revision_keeps_the_version(self):
        package = SimpleNamespace(version="1.2.3", read_text=lambda _: None)
        with patch(
            "coord_dsl.generators.provenance.distribution", return_value=package
        ):
            self.assertEqual(_installed_package(), ("1.2.3", None))


if __name__ == "__main__":
    unittest.main()
