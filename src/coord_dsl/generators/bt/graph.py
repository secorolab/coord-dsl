# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Build the behaviour-tree RDF graph (JSON-LD primary artifact) from a parsed .btree model."""

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD
from pathlib import Path
from rdf_utils.namespace import URL_SECORO_MM, NS_MM_QUDT, NS_MM_QUDT_QTY, NS_MM_QUDT_UNIT
from rdf_utils.models.vocab import (
    URI_QUDT_TYPE_QUANTITY,
    URI_QUDT_PRED_QUANTITY_KIND,
    URI_QUDT_PRED_UNIT,
    URI_QUDT_PRED_VALUE,
    URI_QUDT_QK_ANGLE,
    URI_QUDT_QK_ANG_VEL,
    URI_QUDT_QK_FORCE,
    URI_QUDT_QK_FREQ,
    URI_QUDT_QK_LENGTH,
    URI_QUDT_QK_MASS,
    URI_QUDT_QK_TORQUE,
    URI_QUDT_UNIT_CM,
    URI_QUDT_UNIT_DEG,
    URI_QUDT_UNIT_G,
    URI_QUDT_UNIT_KG,
    URI_QUDT_UNIT_M,
    URI_QUDT_UNIT_MM,
    URI_QUDT_UNIT_RAD,
)
from coord_dsl.generators.bt.classes import (
    CompositeNode,
    DecoratorNode,
    FSMEventNode,
    SubTreeNode,
)
from coord_dsl.generators.fsm.graph import get_fsm_graph
from coord_dsl.generators.fsm.registration import fsm_metamodel

URI_MM_BT = f"{URL_SECORO_MM}/coordination/behaviour-tree#"
URI_MM_EL = f"{URL_SECORO_MM}/behaviour/event_loop#"

URI_QUDT_QK_TIME = NS_MM_QUDT_QTY["Time"]
URI_QUDT_QK_SPEED = NS_MM_QUDT_QTY["Speed"]

# DSL unit spelling -> (qudt unit, qudt quantity kind)
UNIT_MAP = {
    "ms": (NS_MM_QUDT_UNIT["MilliSEC"], URI_QUDT_QK_TIME),
    "s": (NS_MM_QUDT_UNIT["SEC"], URI_QUDT_QK_TIME),
    "m": (URI_QUDT_UNIT_M, URI_QUDT_QK_LENGTH),
    "cm": (URI_QUDT_UNIT_CM, URI_QUDT_QK_LENGTH),
    "mm": (URI_QUDT_UNIT_MM, URI_QUDT_QK_LENGTH),
    "m/s": (NS_MM_QUDT_UNIT["M-PER-SEC"], URI_QUDT_QK_SPEED),
    "cm/s": (NS_MM_QUDT_UNIT["CentiM-PER-SEC"], URI_QUDT_QK_SPEED),
    "rad": (URI_QUDT_UNIT_RAD, URI_QUDT_QK_ANGLE),
    "deg": (URI_QUDT_UNIT_DEG, URI_QUDT_QK_ANGLE),
    "rad/s": (NS_MM_QUDT_UNIT["RAD-PER-SEC"], URI_QUDT_QK_ANG_VEL),
    "deg/s": (NS_MM_QUDT_UNIT["DEG-PER-SEC"], URI_QUDT_QK_ANG_VEL),
    "Hz": (NS_MM_QUDT_UNIT["HZ"], URI_QUDT_QK_FREQ),
    "N": (NS_MM_QUDT_UNIT["N"], URI_QUDT_QK_FORCE),
    "Nm": (NS_MM_QUDT_UNIT["N-M"], URI_QUDT_QK_TORQUE),
    "kg": (URI_QUDT_UNIT_KG, URI_QUDT_QK_MASS),
    "g": (URI_QUDT_UNIT_G, URI_QUDT_QK_MASS),
}

COMPOSITE_CLASS = {
    "sequence": "Sequence",
    "sequence-with-memory": "SequenceWithMemory",
    "reactive-sequence": "ReactiveSequence",
    "fallback": "Fallback",
    "reactive-fallback": "ReactiveFallback",
    "selector": "Fallback",
    "parallel": "Parallel",
    "parallel-all": "ParallelAll",
    "if-then-else": "IfThenElse",
    "while-do-else": "WhileDoElse",
    "switch": "Switch",
}


def _event(e):
    return f"{e.ns.name}:{e.event}" if e.ns is not None else e.standalone


def get_bt_graph(model) -> tuple[Graph, dict, URIRef]:
    """Build an RDF graph for a model that declares exactly one entry tree."""
    NS_BT = Namespace(URI_MM_BT)
    NS_EL = Namespace(URI_MM_EL)

    g = Graph()
    context = {}
    # Model prefixes first; metamodel prefixes bound last so they win any collision
    # (e.g. a model that also declares `ns bt`), keeping vocabulary IRIs compactable.
    for nsd in model.namespaces:
        g.bind(nsd.name, Namespace(nsd.uri))
        context[nsd.name] = nsd.uri
    for prefix, ns in (
        ("bt", NS_BT),
        ("el", NS_EL),
        ("qudt", NS_MM_QUDT),
        ("quantitykind", NS_MM_QUDT_QTY),
        ("unit", NS_MM_QUDT_UNIT),
    ):
        g.bind(prefix, ns, override=True)
        context[prefix] = str(ns)

    main_tree = model.main_tree
    trees = [*model.trees, main_tree]
    fsm_models = {}

    def load_fsm(fsm):
        path = (Path(model._tx_filename).parent / fsm.source).resolve()
        if path not in fsm_models:
            fsm_model = fsm_metamodel().model_from_file(path)
            fsm_models[path] = (fsm_model, *get_fsm_graph(fsm_model))
        fsm_model, fsm_graph, fsm_context, ref = fsm_models[path]
        for triple in fsm_graph:
            g.add(triple)
        context.update(fsm_context)
        return fsm_model, ref

    fsm_refs = {fsm: load_fsm(fsm) for fsm in model.fsms}
    fsm_instance_uri = {
        fsm: URIRef(f"{main_tree.ns.uri}{main_tree.name}-fsm-{fsm.name}") for fsm in model.fsms
    }
    for fsm, (_, fsm_ref) in fsm_refs.items():
        instance_uri = fsm_instance_uri[fsm]
        g.add((instance_uri, RDF.type, NS_BT.FSMInstance))
        g.add((instance_uri, NS_BT["instance-name"], Literal(fsm.name)))
        g.add((instance_uri, NS_BT["of-fsm"], fsm_ref))

    def add_port_decl(owner, pd):
        pn = URIRef(f"{owner}-port-{pd.name}")
        g.add((owner, NS_BT["has-port"], pn))
        g.add((pn, RDF.type, NS_BT.PortDeclaration))
        g.add((pn, NS_BT["port-name"], Literal(pd.name)))
        g.add((pn, NS_BT["port-direction"], Literal(pd.direction)))
        if pd.type:
            g.add((pn, NS_BT["port-type"], Literal(pd.type)))

    beh_uri = {}
    for b in model.behaviours:
        uri = URIRef(f"{main_tree.ns.uri}behaviour-{b.name}")
        beh_uri[b.name] = uri
        g.add((uri, RDF.type, NS_BT.Action if b.kind == "action" else NS_BT.Condition))
        g.add((uri, NS_BT["behaviour-name"], Literal(b.name)))
        declared_port_names = set()
        for pd in b.ports:
            if pd.name in declared_port_names:
                raise ValueError(f"Duplicate port declaration {pd.name!r} on {uri}")
            declared_port_names.add(pd.name)
            add_port_decl(uri, pd)

    tree_uri = {tree: URIRef(f"{tree.ns.uri}{tree.name}") for tree in trees}

    def add_bindings(node_uri, node):
        port_names = set()
        for p in getattr(node, "ports", []) or []:
            if p.name in port_names:
                raise ValueError(f"Duplicate port binding {p.name!r} on {node_uri}")
            port_names.add(p.name)
            pn = URIRef(f"{node_uri}-port-{p.name}")
            g.add((node_uri, NS_BT["port"], pn))
            g.add((pn, NS_BT["port-name"], Literal(p.name)))
            if p.blackboard:
                g.add((pn, NS_BT["blackboard-key"], Literal(p.blackboard.key)))
            elif p.quantity is not None:
                unit_uri, qk_uri = UNIT_MAP[p.quantity.unit]
                g.add((pn, RDF.type, URI_QUDT_TYPE_QUANTITY))
                g.add((pn, URI_QUDT_PRED_VALUE, Literal(p.quantity.num, datatype=XSD.double)))
                g.add((pn, URI_QUDT_PRED_UNIT, unit_uri))
                g.add((pn, URI_QUDT_PRED_QUANTITY_KIND, qk_uri))
            else:
                g.add((pn, NS_BT["port-value"], Literal(p.value)))
        guards = getattr(node, "guards", None)
        if guards:
            guard_kinds = set()
            for gd in guards.items:
                if gd.kind in guard_kinds:
                    raise ValueError(f"Duplicate guard kind {gd.kind!r} on {node_uri}")
                guard_kinds.add(gd.kind)
                gn = URIRef(f"{node_uri}-guard-{gd.kind}")
                g.add((node_uri, NS_BT["guard"], gn))
                g.add((gn, NS_BT["guard-kind"], Literal(gd.kind)))
                g.add((gn, NS_BT["guard-script"], Literal(gd.script)))
        if getattr(node, "instance", ""):
            g.add((node_uri, NS_BT["instance-name"], Literal(node.instance)))

    def add_child(parent_uri, index, child):
        cu = URIRef(f"{parent_uri}-{index}")
        g.add((parent_uri, NS_BT["has-child"], cu))
        g.add((cu, NS_BT["child-index"], Literal(index)))
        visit(child, cu)

    def visit(node, uri):
        if isinstance(node, CompositeNode):
            g.add((uri, RDF.type, NS_BT[COMPOSITE_CLASS[node.type]]))
            g.add((uri, NS_BT["node-kind"], Literal(node.type)))
            add_bindings(uri, node)
            for i, c in enumerate(node.children):
                add_child(uri, i, c)
        elif isinstance(node, DecoratorNode):
            g.add((uri, RDF.type, NS_BT.Decorator))
            g.add((uri, NS_BT["decorator-kind"], Literal(node.type)))
            add_bindings(uri, node)
            add_child(uri, 0, node.child)
        elif isinstance(node, SubTreeNode):
            g.add((uri, RDF.type, NS_BT.SubTree))
            g.add((uri, NS_BT["of-tree"], tree_uri[node.tree]))
            add_bindings(uri, node)
        elif isinstance(node, FSMEventNode):
            fsm_model, fsm_ref = fsm_refs[node.fsm]
            if node.await_fsm is not node.fsm:
                raise ValueError("An FSM event must await an event from the FSM it dispatches to")
            event = next((event for event in fsm_model.fsm.events if event.name == node.event), None)
            if event is None:
                raise ValueError(f"FSM {node.fsm.name!r} does not declare event {node.event!r}")
            awaited_event = next(
                (event for event in fsm_model.fsm.events if event.name == node.await_event), None
            )
            if awaited_event is None:
                raise ValueError(f"FSM {node.fsm.name!r} does not declare event {node.await_event!r}")
            if not any(reaction.when is awaited_event for reaction in fsm_model.fsm.reactions):
                raise ValueError(f"FSM {node.fsm.name!r} does not handle event {node.await_event!r}")
            g.add((uri, RDF.type, NS_BT.FSMEvent))
            g.add((uri, NS_BT["on-fsm-instance"], fsm_instance_uri[node.fsm]))
            g.add((uri, NS_BT["of-event"], URIRef(event.uri)))
            g.add((uri, NS_BT["await-event"], URIRef(awaited_event.uri)))
            add_bindings(uri, node)
        else:
            g.add((uri, RDF.type, NS_BT.Leaf))
            g.add((uri, NS_BT["of-behaviour"], beh_uri[node.behaviour.name]))
            add_bindings(uri, node)
            if getattr(node, "start_event", None):
                g.add((uri, NS_BT["start-event"], Literal(_event(node.start_event))))
            if getattr(node, "end_event", None):
                g.add((uri, NS_BT["end-event"], Literal(_event(node.end_event))))

    for t in trees:
        tu = tree_uri[t]
        g.add((tu, RDF.type, NS_BT.BehaviourTree))
        g.add((tu, NS_BT["behaviour-tree-name"], Literal(t.name)))
        if t is main_tree:
            g.add((tu, NS_BT["is-main"], Literal(True)))
        declared_port_names = set()
        for pd in t.params:
            if pd.name in declared_port_names:
                raise ValueError(f"Duplicate port declaration {pd.name!r} on {tu}")
            declared_port_names.add(pd.name)
            add_port_decl(tu, pd)
        ru = URIRef(f"{tu}-root")
        g.add((tu, NS_BT.root, ru))
        visit(t.root, ru)

    return g, context, tree_uri[main_tree]
