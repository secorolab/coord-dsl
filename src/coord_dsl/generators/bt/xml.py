# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Generate BehaviorTree.CPP v4 XML from the behaviour-tree RDF graph."""

from xml.etree.ElementTree import Element, SubElement, indent, tostring

import math

from rdflib import Namespace, RDF
from rdf_utils.namespace import NS_MM_QUDT_UNIT
from rdf_utils.models.vocab import URI_QUDT_PRED_UNIT, URI_QUDT_PRED_VALUE

from coord_dsl.generators.bt.graph import URI_MM_BT

NS_BT = Namespace(URI_MM_BT)

# BT.CPP built-in ports carry a fixed unit in the number (no unit attached); a
# quantity authored in any other unit of the same kind is converted to this one.
EXPECTED_UNIT = {
    ("Timeout", "msec"): NS_MM_QUDT_UNIT["MilliSEC"],
    ("Delay", "delay_msec"): NS_MM_QUDT_UNIT["MilliSEC"],
    ("Sleep", "msec"): NS_MM_QUDT_UNIT["MilliSEC"],
}

# Multiplier from each unit to its quantity kind's SI base unit.
UNIT_SI = {
    NS_MM_QUDT_UNIT["MilliSEC"]: 1e-3,
    NS_MM_QUDT_UNIT["SEC"]: 1.0,
    NS_MM_QUDT_UNIT["M"]: 1.0,
    NS_MM_QUDT_UNIT["CentiM"]: 1e-2,
    NS_MM_QUDT_UNIT["MilliM"]: 1e-3,
    NS_MM_QUDT_UNIT["M-PER-SEC"]: 1.0,
    NS_MM_QUDT_UNIT["CentiM-PER-SEC"]: 1e-2,
    NS_MM_QUDT_UNIT["RAD"]: 1.0,
    NS_MM_QUDT_UNIT["DEG"]: math.pi / 180.0,
    NS_MM_QUDT_UNIT["RAD-PER-SEC"]: 1.0,
    NS_MM_QUDT_UNIT["DEG-PER-SEC"]: math.pi / 180.0,
    NS_MM_QUDT_UNIT["HZ"]: 1.0,
    NS_MM_QUDT_UNIT["N"]: 1.0,
    NS_MM_QUDT_UNIT["N-M"]: 1.0,
    NS_MM_QUDT_UNIT["KiloGM"]: 1.0,
    NS_MM_QUDT_UNIT["GM"]: 1e-3,
}

COMPOSITE_TAG = {
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
}

DECORATOR_TAG = {
    "inverter": "Inverter",
    "force-success": "ForceSuccess",
    "force-failure": "ForceFailure",
    "repeat": "Repeat",
    "retry": "RetryUntilSuccessful",
    "keep-running": "KeepRunningUntilFailure",
    "delay": "Delay",
    "timeout": "Timeout",
    "run-once": "RunOnce",
    "precondition": "Precondition",
    "loop": "LoopString",
}

BUILTIN_TAG = {
    "script": "Script",
    "set_blackboard": "SetBlackboard",
    "sleep": "Sleep",
    "always_success": "AlwaysSuccess",
    "always_failure": "AlwaysFailure",
}

GUARD_ATTR = {
    "skip-if": "_skipIf",
    "failure-if": "_failureIf",
    "success-if": "_successIf",
    "while": "_while",
    "on-success": "_onSuccess",
    "on-failure": "_onFailure",
    "on-halted": "_onHalted",
    "post": "_post",
}

PORT_TAG = {"in": "input_port", "out": "output_port", "inout": "inout_port"}


def _pascal(kebab):
    return "".join(p.capitalize() for p in kebab.replace("_", "-").split("-"))


def _fmt_num(v):
    return str(int(v)) if float(v) == int(v) else repr(v)


def _convert(value, from_unit, to_unit):
    if to_unit is None or from_unit == to_unit:
        return value
    return value * UNIT_SI[from_unit] / UNIT_SI[to_unit]


def _scalar(value):
    v = value.toPython()
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else repr(v)
    return str(v)


def _add_bindings(g, node, el):
    for pn in g.objects(node, NS_BT.port):
        name = g.value(pn, NS_BT["port-name"]).toPython()
        bb = g.value(pn, NS_BT["blackboard-key"])
        qty = g.value(pn, URI_QUDT_PRED_VALUE)
        if bb is not None:
            el.set(name, "{" + bb.toPython() + "}")
        elif qty is not None:
            value = _convert(qty.toPython(), g.value(pn, URI_QUDT_PRED_UNIT), EXPECTED_UNIT.get((el.tag, name)))
            el.set(name, _fmt_num(value))
        else:
            el.set(name, _scalar(g.value(pn, NS_BT["port-value"])))


def _add_common(g, node, el):
    name = g.value(node, NS_BT["instance-name"])
    if name is not None:
        el.set("name", name.toPython())
    for gn in g.objects(node, NS_BT.guard):
        kind = g.value(gn, NS_BT["guard-kind"]).toPython()
        el.set(GUARD_ATTR[kind], g.value(gn, NS_BT["guard-script"]).toPython())


def _children(g, node):
    kids = [(int(g.value(c, NS_BT["child-index"])), c) for c in g.objects(node, NS_BT["has-child"])]
    return [c for _, c in sorted(kids)]


def _render(g, node):
    types = set(g.objects(node, RDF.type))
    if NS_BT.Decorator in types:
        kind = str(g.value(node, NS_BT["decorator-kind"]))
        el = Element(DECORATOR_TAG.get(kind, _pascal(kind)))
        _add_bindings(g, node, el)
        _add_common(g, node, el)
        el.append(_render(g, _children(g, node)[0]))
    elif NS_BT.SubTree in types:
        tree = g.value(node, NS_BT["of-tree"])
        el = Element("SubTree", {"ID": str(g.value(tree, NS_BT["behaviour-tree-name"]))})
        _add_bindings(g, node, el)
        _add_common(g, node, el)
    elif NS_BT.FSMEvent in types:
        raise ValueError("FSM nodes are only supported by the BT JSON-LD generator")
    elif NS_BT.Leaf in types:
        beh = g.value(node, NS_BT["of-behaviour"])
        name = str(g.value(beh, NS_BT["behaviour-name"]))
        el = Element(BUILTIN_TAG.get(name, name))
        _add_bindings(g, node, el)
        _add_common(g, node, el)
        for key, attr in (("start-event", "start_event"), ("end-event", "end_event")):
            ev = g.value(node, NS_BT[key])
            if ev is not None:
                el.set(attr, str(ev))
    else:
        kind = str(g.value(node, NS_BT["node-kind"]))
        if kind == "switch":
            ncases = sum(
                1
                for pn in g.objects(node, NS_BT.port)
                if str(g.value(pn, NS_BT["port-name"])).startswith("case_")
            )
            tag = f"Switch{ncases}"
        else:
            tag = COMPOSITE_TAG[kind]
        el = Element(tag)
        _add_bindings(g, node, el)
        _add_common(g, node, el)
        for c in _children(g, node):
            el.append(_render(g, c))
    return el


def evented_behaviours(g):
    """Return leaf behaviour names that require generated event input ports."""
    names = set()
    for node in g.subjects(RDF.type, NS_BT.Leaf):
        if g.value(node, NS_BT["start-event"]) or g.value(node, NS_BT["end-event"]):
            names.add(str(g.value(g.value(node, NS_BT["of-behaviour"]), NS_BT["behaviour-name"])))
    return names


def _port_decls(g, owner, el):
    decls = []
    for pn in g.objects(owner, NS_BT["has-port"]):
        decls.append(
            (str(g.value(pn, NS_BT["port-name"])),
             str(g.value(pn, NS_BT["port-direction"])),
             g.value(pn, NS_BT["port-type"]))
        )
    for name, direction, ptype in sorted(decls):
        attrs = {"name": name}
        if ptype is not None:
            attrs["type"] = str(ptype)
        SubElement(el, PORT_TAG[direction], attrs)


def _tree_nodes_model(g):
    tnm = Element("TreeNodesModel")
    evented = evented_behaviours(g)
    for cls, tag in ((NS_BT.Action, "Action"), (NS_BT.Condition, "Condition")):
        for b in sorted(g.subjects(RDF.type, cls), key=str):
            name = str(g.value(b, NS_BT["behaviour-name"]))
            if name in BUILTIN_TAG:
                continue
            el = SubElement(tnm, tag, {"ID": name})
            _port_decls(g, b, el)
            if name in evented:
                SubElement(el, "input_port", {"name": "start_event"})
                SubElement(el, "input_port", {"name": "end_event"})
    for t in sorted(g.subjects(RDF.type, NS_BT.BehaviourTree), key=str):
        if g.value(t, NS_BT["is-main"]):
            continue
        el = SubElement(tnm, "SubTree", {"ID": str(g.value(t, NS_BT["behaviour-tree-name"]))})
        _port_decls(g, t, el)
    return tnm


def gen_bt_xml(g, root_ref):
    """Return BehaviorTree.CPP v4 XML for the BT graph, with `root_ref` as the main tree."""
    root = Element("root", {"BTCPP_format": "4"})
    main_name = g.value(root_ref, NS_BT["behaviour-tree-name"])
    if main_name is not None:
        root.set("main_tree_to_execute", str(main_name))

    trees = list(g.subjects(RDF.type, NS_BT.BehaviourTree))
    trees.sort(key=lambda t: (not bool(g.value(t, NS_BT["is-main"])), str(g.value(t, NS_BT["behaviour-tree-name"]))))
    for t in trees:
        bt = SubElement(root, "BehaviorTree", {"ID": str(g.value(t, NS_BT["behaviour-tree-name"]))})
        bt.append(_render(g, g.value(t, NS_BT.root)))

    tnm = _tree_nodes_model(g)
    if len(tnm):
        root.append(tnm)
    indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode") + "\n"
