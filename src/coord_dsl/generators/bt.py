# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
"""Backend-agnostic IR for behaviour trees, and the py_trees and BT.CPP targets."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rdf_utils.models.vocab import URI_EL_PRED_REF_FLG
from rdf_utils.naming import get_valid_var_name
from rdflib import RDF, Graph, URIRef
from rdflib.collection import Collection

from coord_dsl.generators.fsm import local_name
from coord_dsl.rdf.vocab import (
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

COMPOSITE_KIND = {
    URI_BT_TYPE_SEQUENCE: "sequence",
    URI_BT_TYPE_SELECTOR: "selector",
    URI_BT_TYPE_PARALLEL: "parallel",
}


def _ident(uri: URIRef) -> str:
    return get_valid_var_name(local_name(uri.toPython()))


def gen_json(g: Graph, entry_ref: URIRef) -> dict:
    """Read the graph into the IR both targets render from."""
    assert isinstance(entry_ref, URIRef)

    actions: dict[str, str] = {}
    flags: dict[str, str] = {}
    machines: dict[str, str] = {}

    def read_node(uri: URIRef) -> dict:
        node_type = g.value(uri, RDF.type)
        assert node_type is not None, f"node {uri} has no type"

        if node_type == URI_BT_TYPE_TREE:
            return {"kind": "subtree", "uri": uri.toPython(), "tree": _ident(uri)}

        if node_type == URI_FSM_TYPE_FSM:
            machines[_ident(uri)] = uri.toPython()
            return {
                "kind": "state_machine",
                "uri": uri.toPython(),
                "fsm": _ident(uri),
            }

        if node_type == URI_BT_TYPE_ACTION:
            action = g.value(uri, URI_BT_PRED_OF_ACTION)
            assert action is not None, f"action node {uri} names no action"
            actions[_ident(action)] = action.toPython()
            return {
                "kind": "action",
                "name": _ident(uri),
                "uri": uri.toPython(),
                "action": _ident(action),
            }

        if node_type == URI_BT_TYPE_CONDITION:
            flag = g.value(uri, URI_EL_PRED_REF_FLG)
            assert flag is not None, f"condition node {uri} checks no flag"
            flags[_ident(flag)] = flag.toPython()
            return {
                "kind": "condition",
                "name": _ident(uri),
                "uri": uri.toPython(),
                "flag": _ident(flag),
            }

        kind = COMPOSITE_KIND.get(node_type)
        assert kind is not None, f"unhandled node type {node_type} on {uri}"

        head = g.value(uri, URI_BT_PRED_CHILDREN)
        assert head is not None, f"composite {uri} has no children"
        node = {
            "kind": kind,
            "name": _ident(uri),
            "uri": uri.toPython(),
            "children": [read_node(child) for child in Collection(g, head)],
        }
        if kind == "parallel":
            threshold = g.value(uri, URI_BT_PRED_SUCCESS_THRESHOLD)
            assert threshold is not None, f"parallel {uri} has no success threshold"
            node["threshold"] = int(threshold)
            # the book fails a parallel once N - M + 1 children have failed
            node["failure_threshold"] = len(node["children"]) - int(threshold) + 1
        else:
            memory = g.value(uri, URI_BT_PRED_MEMORY)
            assert memory is not None, f"composite {uri} does not state its memory"
            node["memory"] = bool(memory.toPython())
        return node

    trees = []
    for tree_uri in g.subjects(RDF.type, URI_BT_TYPE_TREE):
        root = g.value(tree_uri, URI_BT_PRED_ROOT)
        assert root is not None, f"tree {tree_uri} has no root"
        trees.append(
            {
                "name": _ident(tree_uri),
                "uri": tree_uri.toPython(),
                "root": read_node(root),
            }
        )
    trees.sort(key=lambda tree: tree["name"])

    return {
        "entry": _ident(entry_ref),
        "trees": trees,
        "actions": [{"name": n, "uri": u} for n, u in sorted(actions.items())],
        "flags": [{"name": n, "uri": u} for n, u in sorted(flags.items())],
        "state_machines": [{"name": n, "uri": u} for n, u in sorted(machines.items())],
    }


def _render(template_name: str, ir: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent.parent / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    return env.get_template(template_name).render(data=ir)


def gen_python_code(ir: dict) -> str:
    """Generates a .py file building the tree with py_trees."""
    notes: list[str] = []
    for tree in ir["trees"]:
        _check_py_trees_parallel(tree["root"], notes)
    for note in notes:
        print(f"  note: {note}")
    print(f"Generating py_trees code for behaviour tree: {ir['entry']}")
    return _render("bt.py.jinja2", dict(ir, notes=notes))


def gen_dot(ir: dict) -> str:
    """Generates graphviz source, one cluster per tree."""
    roots = {tree["name"]: _node_id(tree["root"]) for tree in ir["trees"]}
    print(f"Drawing behaviour tree: {ir['entry']}")
    return _render("bt.dot.jinja2", dict(ir, roots=roots))


def _node_id(node: dict) -> str:
    """A subtree and a state machine are drawn as the thing they name."""
    if node["kind"] == "subtree":
        return node["tree"]
    if node["kind"] == "state_machine":
        return f"fsm__{node['fsm']}"
    return node["name"]


def gen_xml(ir: dict) -> str:
    """Generates a BehaviorTree.CPP v4 XML file."""
    print(f"Generating BehaviorTree.CPP XML for behaviour tree: {ir['entry']}")
    return _render("bt.xml.jinja2", ir)


def _check_py_trees_parallel(node: dict, notes: list) -> None:
    """py_trees has SuccessOnOne and SuccessOnAll, so only M of 1 and N map."""
    if node["kind"] == "parallel":
        count = len(node["children"])
        threshold = node["threshold"]
        if threshold not in (1, count):
            raise ValueError(
                f"py_trees cannot express a success threshold of {threshold} out of "
                f"{count} children on '{node['name']}', only 1 (SuccessOnOne) or "
                f"{count} (SuccessOnAll)"
            )
        if threshold == 1 and count > 1:
            # py_trees fails a Parallel on its first failing child, any policy
            notes.append(
                f"'{node['name']}' fails on its first failing child under py_trees, "
                f"where the model fails it after {node['failure_threshold']}"
            )
    for child in node.get("children", ()):
        _check_py_trees_parallel(child, notes)
