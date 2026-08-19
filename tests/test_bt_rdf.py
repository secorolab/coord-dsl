# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
"""Tests for the behaviour-tree RDF graph."""

import unittest
import urllib.error
import urllib.request
from pathlib import Path

from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.models.vocab import URI_EL_PRED_REF_FLG, URI_EL_TYPE_FLG
from rdf_utils.resolver import install_resolver
from rdflib import RDF, Literal
from rdflib.collection import Collection
from rdflib.namespace import XSD

from coord_dsl.rdf.bt import URL_BT_SHACL, get_bt_graph
from coord_dsl.rdf.vocab import (
    URI_BT_PRED_CHILDREN,
    URI_BT_PRED_MEMORY,
    URI_BT_PRED_OF_ACTION,
    URI_BT_PRED_ROOT,
    URI_BT_PRED_SUCCESS_THRESHOLD,
    URI_BT_TYPE_ACTION,
    URI_BT_TYPE_CONDITION,
    URI_BT_TYPE_PARALLEL,
    URI_BT_TYPE_SEQUENCE,
    URI_BT_TYPE_TREE,
)
from coord_dsl.registration import bt_metamodel

MODEL = Path(__file__).parents[1] / "examples/models/bt/pick.btree"


def _shapes_published() -> bool:
    """The shapes ship with the metamodel; skip until that release is live."""
    install_resolver()
    try:
        urllib.request.urlopen(URL_BT_SHACL, timeout=15).close()
    except (urllib.error.URLError, OSError):
        return False
    return True


def _graph(source=None):
    mm = bt_metamodel()
    model = mm.model_from_str(source) if source else mm.model_from_file(str(MODEL))
    return get_bt_graph(model)


class BtRdfTest(unittest.TestCase):
    @unittest.skipUnless(_shapes_published(), f"{URL_BT_SHACL} is not published yet")
    def test_example_conforms_to_shacl(self):
        graph, _ = _graph()
        self.assertTrue(check_shacl_constraints(graph, {URL_BT_SHACL: "ttl"}))

    def test_entry_tree_is_the_last_declared(self):
        graph, entry = _graph()
        # both trees are in the graph; the entry is the one nothing else pulls in
        self.assertEqual(len(list(graph.subjects(RDF.type, URI_BT_TYPE_TREE))), 2)
        self.assertTrue(str(entry).endswith("/pick"))

    def test_a_tree_has_exactly_one_root(self):
        graph, entry = _graph()
        self.assertIn((entry, RDF.type, URI_BT_TYPE_TREE), graph)
        self.assertEqual(len(list(graph.objects(entry, URI_BT_PRED_ROOT))), 1)

    def test_sibling_order_is_the_list_order(self):
        graph, entry = _graph()
        root = graph.value(entry, URI_BT_PRED_ROOT)
        children = list(Collection(graph, graph.value(root, URI_BT_PRED_CHILDREN)))
        self.assertEqual(
            [graph.value(child, RDF.type) for child in children],
            [URI_BT_TYPE_TREE, URI_BT_TYPE_ACTION, URI_BT_TYPE_PARALLEL],
        )

    def test_memory_is_stated_and_defaults_to_reactive(self):
        graph, _ = _graph(
            'ns g = "https://example.test/"\n'
            "btree (ns=g) t {\n"
            "  sequence {\n"
            "    selector (memory=true) { subtree <t> }\n"
            "  }\n"
            "}\n"
        )
        sequence = next(graph.subjects(RDF.type, URI_BT_TYPE_SEQUENCE))
        self.assertEqual(graph.value(sequence, URI_BT_PRED_MEMORY), Literal(False))
        self.assertEqual(
            sorted(bool(m) for m in graph.objects(None, URI_BT_PRED_MEMORY)),
            [False, True],
        )

    def test_parallel_carries_its_success_threshold(self):
        graph, _ = _graph()
        parallel = next(graph.subjects(RDF.type, URI_BT_TYPE_PARALLEL))
        self.assertEqual(
            graph.value(parallel, URI_BT_PRED_SUCCESS_THRESHOLD),
            Literal(2, datatype=XSD.positiveInteger),
        )

    def test_leaves_have_no_children_and_name_what_they_run(self):
        graph, _ = _graph()
        for leaf_type in (URI_BT_TYPE_ACTION, URI_BT_TYPE_CONDITION):
            leaves = list(graph.subjects(RDF.type, leaf_type))
            self.assertTrue(leaves, leaf_type)
            for leaf in leaves:
                self.assertEqual(list(graph.objects(leaf, URI_BT_PRED_CHILDREN)), [])
        for action in graph.subjects(RDF.type, URI_BT_TYPE_ACTION):
            self.assertIsNotNone(graph.value(action, URI_BT_PRED_OF_ACTION))

    def test_a_condition_checks_a_flag(self):
        graph, _ = _graph()
        conditions = list(graph.subjects(RDF.type, URI_BT_TYPE_CONDITION))
        self.assertTrue(conditions)
        for condition in conditions:
            flag = graph.value(condition, URI_EL_PRED_REF_FLG)
            self.assertIn((flag, RDF.type, URI_EL_TYPE_FLG), graph)


if __name__ == "__main__":
    unittest.main()
