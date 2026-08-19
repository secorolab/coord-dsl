# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
"""RDF generation for behaviour trees."""

from rdf_utils.models.vocab import URI_EL_PRED_REF_FLG, URI_EL_TYPE_FLG
from rdf_utils.namespace import NS_MM_EL, URL_SECORO_MM
from rdflib import RDF, BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import XSD

from coord_dsl.classes.bt import BehaviourTree
from coord_dsl.rdf.event_loop import add_event_loop
from coord_dsl.rdf.vocab import (
    NS_MM_BT,
    NS_MM_FSM,
    URI_BT_PRED_CHILDREN,
    URI_BT_PRED_MEMORY,
    URI_BT_PRED_OF_ACTION,
    URI_BT_PRED_ROOT,
    URI_BT_PRED_SUCCESS_THRESHOLD,
    URI_BT_TYPE_ACTION,
    URI_BT_TYPE_CONDITION,
    URI_BT_TYPE_PARALLEL,
    URI_BT_TYPE_SELECTOR,
    URI_BT_TYPE_SEQUENCE,
    URI_BT_TYPE_TREE,
    URI_FSM_TYPE_FSM,
)

URL_BT_SHACL = f"{URL_SECORO_MM}/behaviour/behaviour-tree.shacl.ttl"


def _is_fsm(target) -> bool:
    return target.__class__.__name__ == "FSM"


def get_bt_graph(model) -> tuple[Graph, URIRef]:
    """Build the tree graph; the entry tree is the last one declared."""
    trees = getattr(model, "trees", [])
    assert trees, "Model does not contain a behaviour tree"

    graph = Graph()
    graph.bind("bt", NS_MM_BT)
    graph.bind("el", NS_MM_EL)
    graph.bind("fsm", NS_MM_FSM)
    for behaviour_set in model.behaviour_sets:
        graph.bind(behaviour_set.ns_prefix, behaviour_set.namespace)
    for tree in trees:
        graph.bind(tree.ns_prefix, tree.namespace)

    tree_uri = {tree: tree.uri for tree in trees}

    def add_children(node_uri, children):
        """List order is tick order."""
        child_uris = []
        for index, child in enumerate(children):
            child_uri = node_ref(child, URIRef(f"{node_uri}-{index}"))
            child_uris.append(child_uri)
        head = BNode()
        Collection(graph, head, child_uris)
        graph.add((node_uri, URI_BT_PRED_CHILDREN, head))

    def node_ref(node, uri):
        """A tree or a state machine sits in the list as itself."""
        if node.__class__.__name__ == "Subtree":
            return tree_uri[node.tree]
        if node.__class__.__name__ == "Leaf" and _is_fsm(node.target):
            graph.add((node.target.uri, RDF.type, URI_FSM_TYPE_FSM))
            graph.bind(node.target.ns_prefix, node.target.namespace)
            return node.target.uri
        visit(node, uri)
        return uri

    def visit(node, uri):
        kind = node.__class__.__name__
        if kind in ("Sequence", "Selector"):
            node_type = (
                URI_BT_TYPE_SEQUENCE if kind == "Sequence" else URI_BT_TYPE_SELECTOR
            )
            graph.add((uri, RDF.type, node_type))
            graph.add((uri, URI_BT_PRED_MEMORY, Literal(bool(node.memory))))
            add_children(uri, node.children)
        elif kind == "Parallel":
            graph.add((uri, RDF.type, URI_BT_TYPE_PARALLEL))
            graph.add(
                (
                    uri,
                    URI_BT_PRED_SUCCESS_THRESHOLD,
                    Literal(node.threshold, datatype=XSD.positiveInteger),
                )
            )
            add_children(uri, node.children)
        elif kind == "Condition":
            graph.add((uri, RDF.type, URI_BT_TYPE_CONDITION))
            graph.add((uri, URI_EL_PRED_REF_FLG, node.flag.uri))
            # the flag may be declared in an imported model
            graph.add((node.flag.uri, RDF.type, URI_EL_TYPE_FLG))
            graph.bind(node.flag.parent.ns_prefix, node.flag.namespace)
        else:
            graph.add((uri, RDF.type, URI_BT_TYPE_ACTION))
            graph.add((uri, URI_BT_PRED_OF_ACTION, node.target.uri))

    for event_loop in model.event_loops:
        add_event_loop(graph, event_loop)

    for tree in trees:
        assert isinstance(tree, BehaviourTree), f"not a behaviour tree: {tree}"
        graph.add((tree.uri, RDF.type, URI_BT_TYPE_TREE))
        root_uri = node_ref(tree.root, URIRef(f"{tree.uri}-root"))
        graph.add((tree.uri, URI_BT_PRED_ROOT, root_uri))

    return graph, trees[-1].uri
