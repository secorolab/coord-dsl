# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Render a model as graphviz: an FSM's state machine, a BT's node tree.

Both read the same RDF graph the code generators render from, so a picture can
never drift from what is generated.

A BT is drawn the way it runs: each sub-tree instance is expanded where it is
used, so every edge is short and the tree reads top-down (a sub-tree used twice
is drawn twice, as it executes twice). The FSMs a tree coordinates are drawn
beside it, so a ``send``/``await`` node sits next to the machine it drives.
"""

from rdflib import Namespace, RDF
from rdflib.namespace import split_uri
from rdf_utils.namespace import URL_SECORO_MM

# Built here rather than imported from the graph modules: those import each other
# (a BT loads the FSMs it coordinates), and joining that cycle would break it.
NS_BT = Namespace(f"{URL_SECORO_MM}/behaviour/behaviour-tree#")
NS_FSM = Namespace(f"{URL_SECORO_MM}/behaviour/fsm#")

FORMATS = ("png", "svg", "pdf")

_HEADER = [
    "  compound=true;",
    '  graph [fontname="Helvetica", fontsize=11];',
    '  node [fontname="Helvetica", fontsize=10, shape=box, style="rounded,filled", fillcolor="#ffffff"];',
    '  edge [fontname="Helvetica", fontsize=9, color="#5f6368"];',
]


def _esc(text) -> str:
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


def _local(uri) -> str:
    return split_uri(uri)[1]


def _ident(text) -> str:
    return "".join(c if c.isalnum() else "_" for c in str(text))


# --------------------------------------------------------------------------- FSM


def _fsm_body(g, fsm_ref, indent, entry=True, awaited=(), colour=None):
    """The states and the reactions that join them, as dot lines."""
    start = g.value(fsm_ref, NS_FSM["start-state"])
    end = g.value(fsm_ref, NS_FSM["end-state"])
    lines = []

    if entry:
        lines.append(f'{indent}"__entry__" [shape=point, width=0.12, '
                     'fillcolor="#202124", color="#202124"];')
        lines.append(f'{indent}"__entry__" -> "{_esc(start)}";')
    for state in sorted(g.objects(fsm_ref, NS_FSM.states), key=str):
        attrs = [f'label="{_esc(_local(state))}"']
        if state == end:
            attrs.append('peripheries=2, fillcolor="#e6f4ea"')
        elif state == start:
            attrs.append('fillcolor="#e8f0fe"')
        if state in awaited:
            # a state the tree waits for: the coordination seam, worth picking out
            attrs.append(f'color="{colour}", penwidth=2')
        lines.append(f'{indent}"{_esc(state)}" [{", ".join(attrs)}];')

    # A transition only ever fires through a reaction, so reactions carry the label;
    # one the model never reacts to is still drawn, greyed out, because it is dead.
    reacted = set()
    for reaction in sorted(g.objects(fsm_ref, NS_FSM.reactions), key=str):
        transition = g.value(reaction, NS_FSM["do-transition"])
        reacted.add(transition)
        label = [_local(g.value(reaction, NS_FSM["when-event"]))]
        fires = sorted(_local(e) for e in g.objects(reaction, NS_FSM["fires-events"]))
        if fires:
            label.append("fires " + ", ".join(fires))
        lines.append(
            f'{indent}"{_esc(g.value(transition, NS_FSM["transition-from"]))}"'
            f' -> "{_esc(g.value(transition, NS_FSM["transition-to"]))}"'
            f' [label="{"\\n".join(_esc(line) for line in label)}"];'
        )
    for transition in sorted(g.objects(fsm_ref, NS_FSM.transitions), key=str):
        if transition not in reacted:
            lines.append(
                f'{indent}"{_esc(g.value(transition, NS_FSM["transition-from"]))}"'
                f' -> "{_esc(g.value(transition, NS_FSM["transition-to"]))}"'
                f' [label="{_esc(_local(transition))}", style=dashed, color="#9aa0a6",'
                ' fontcolor="#9aa0a6"];'
            )
    return lines


def fsm_dot(g, fsm_ref) -> str:
    """States as nodes, one edge per reaction: what fires it, and what it fires."""
    lines = [f'digraph "{_esc(g.value(fsm_ref, NS_FSM.name))}" {{', "  rankdir=LR;"] + _HEADER
    lines += _fsm_body(g, fsm_ref, "  ")
    lines.append("}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------- BT

_STYLE = {
    "composite": 'shape=box, style="filled", fillcolor="#e8f0fe"',
    "decorator": 'shape=box, style="rounded,filled", fillcolor="#fef7e0"',
    "leaf": 'shape=box, style="rounded,filled", fillcolor="#ffffff"',
    "fsm": 'shape=box, style="filled", fillcolor="#e6f4ea"',
}

# One colour per coordinated FSM. A `send`/`await` node and the machine it drives are
# drawn in the same colour rather than joined by a line: the tree and the machines sit
# far apart on the page, and long edges across it are what make these unreadable.
_FSM_COLOURS = ("#188038", "#1967d2", "#a142f4", "#e37400", "#c5221f")


def _children(g, node):
    kids = [(int(g.value(c, NS_BT["child-index"])), c) for c in g.objects(node, NS_BT["has-child"])]
    return [c for _, c in sorted(kids)]


def _guard_lines(g, node):
    return [
        f'[{g.value(gn, NS_BT["guard-kind"])}: {g.value(gn, NS_BT["guard-script"])}]'
        for gn in sorted(g.objects(node, NS_BT.guard), key=str)
    ]


def _bt_label(g, node):
    """The node's label and style, by what kind of node it is."""
    types = set(g.objects(node, RDF.type))
    name = g.value(node, NS_BT["instance-name"])
    if NS_BT.Decorator in types:
        kind, head = "decorator", str(g.value(node, NS_BT["decorator-kind"]))
    elif NS_BT.FSMEvent in types:
        kind = "fsm"
        instance = g.value(node, NS_BT["on-fsm-instance"])
        head = (f'send {g.value(instance, NS_BT["instance-name"])}.'
                f'{_local(g.value(node, NS_BT["of-event"]))}')
    elif NS_BT.Leaf in types:
        kind = "leaf"
        head = str(g.value(g.value(node, NS_BT["of-behaviour"]), NS_BT["behaviour-name"]))
    else:
        kind, head = "composite", str(g.value(node, NS_BT["node-kind"]))

    label = [head] if name is None or str(name) == head else [str(name), head]
    if kind == "fsm":
        label.append(f'await {g.value(node, NS_BT["await-kind"])} '
                     f'{_local(g.value(node, NS_BT["await-target"]))}')
        fail = g.value(node, NS_BT["fail-target"])
        if fail is not None:
            label.append(f"on-fail {_local(fail)}")
    label += _guard_lines(g, node)
    return "\\n".join(_esc(line) for line in label), _STYLE[kind]


def _await_state(g, fsm_ref, node):
    """The state a ``send``/``await`` node is waiting to see.

    A state target is that state. An *event* target is not a node in the drawing --
    it labels a transition -- so it resolves to the state the reaction it fires
    moves the machine to, which is what the node is waiting for in practice.
    """
    target = g.value(node, NS_BT["await-target"])
    if str(g.value(node, NS_BT["await-kind"])) == "state":
        return target
    for reaction in g.objects(fsm_ref, NS_FSM.reactions):
        if g.value(reaction, NS_FSM["when-event"]) == target:
            return g.value(g.value(reaction, NS_FSM["do-transition"]), NS_FSM["transition-to"])
    return g.value(fsm_ref, NS_FSM["start-state"])


def _bt_nodes(g, node, lines, depth, path, awaited, colours, expanding):
    """Draw a node and its children, returning the dot id of the node itself.

    ``path`` namespaces the ids so an expanded sub-tree instance never collides
    with another instance of the same tree.
    """
    pad = "  " * depth
    nid = f"{path}{node}"

    if NS_BT.SubTree in set(g.objects(node, RDF.type)):
        tree = g.value(node, NS_BT["of-tree"])
        tree_name = g.value(tree, NS_BT["behaviour-tree-name"])
        if tree in expanding:
            lines.append(f'{pad}"{_esc(nid)}" [label="subtree {_esc(tree_name)} (recursive)",'
                         ' shape=box3d, style="filled", fillcolor="#fce8e6"];')
            return nid
        instance = g.value(node, NS_BT["instance-name"]) or tree_name
        head = f"subtree {tree_name} as {instance}"
        if g.value(node, NS_BT["auto-remap"]):
            head += " (autoremap)"
        lines.append(f'{pad}subgraph "cluster_{_ident(nid)}" {{')
        lines.append(f'{pad}  label="{_esc(head)}";')
        lines.append(f'{pad}  style=rounded; color="#1a73e8"; fontcolor="#1a73e8"; fontsize=10;')
        # Keyed by this node, not by the instance name: two unnamed instances of one
        # tree share a name, and sharing ids would collapse them into one drawing.
        inner = _bt_nodes(g, g.value(tree, NS_BT.root), lines, depth + 1,
                          f"{nid}/", awaited, colours, expanding + (tree,))
        lines.append(f"{pad}}}")
        return inner

    label, style = _bt_label(g, node)
    if NS_BT.FSMEvent in set(g.objects(node, RDF.type)):
        fsm_ref = g.value(g.value(node, NS_BT["on-fsm-instance"]), NS_BT["of-fsm"])
        style += f', color="{colours(fsm_ref)}", penwidth=2'
    lines.append(f'{pad}"{_esc(nid)}" [label="{label}", {style}];')
    if NS_BT.FSMEvent in set(g.objects(node, RDF.type)):
        fsm_ref = g.value(g.value(node, NS_BT["on-fsm-instance"]), NS_BT["of-fsm"])
        awaited.append((nid, fsm_ref, _local(g.value(node, NS_BT["of-event"])),
                        _await_state(g, fsm_ref, node)))
    for child in _children(g, node):
        cid = _bt_nodes(g, child, lines, depth, path, awaited, colours, expanding)
        lines.append(f'{pad}"{_esc(nid)}" -> "{_esc(cid)}";')
    return nid


def bt_dot(g, root_ref) -> str:
    """The main tree with its sub-trees expanded in place, beside the FSMs it drives."""
    name = g.value(root_ref, NS_BT["behaviour-tree-name"])
    lines = [f'digraph "{_esc(name)}" {{', "  rankdir=TB;"] + _HEADER
    awaited = []
    tree_lines = []
    _bt_nodes(g, g.value(root_ref, NS_BT.root), tree_lines, 2, "", awaited, lambda _: "#5f6368", ())

    # Machines in the order the tree first drives one, so the links between the two
    # do not cross each other on the way over.
    order = list(dict.fromkeys(fsm for _, fsm, _, _ in awaited))
    colour_of = {fsm: _FSM_COLOURS[i % len(_FSM_COLOURS)] for i, fsm in enumerate(order)}
    lines.append(f'  subgraph "cluster_{_ident(name)}" {{')
    lines.append(f'    label="{_esc(name)}";')
    lines.append('    style=rounded; color="#9aa0a6"; fontsize=11; labeljust="l";')
    awaited.clear()
    _bt_nodes(g, g.value(root_ref, NS_BT.root), lines, 2, "", awaited, colour_of.get, ())
    lines.append("  }")

    # The machines the tree coordinates, drawn beside it. A node and its machine share
    # a colour, and the states the tree waits for are outlined in it.
    for fsm_ref in order:
        colour = colour_of[fsm_ref]
        lines.append(f'  subgraph "cluster_fsm_{_ident(_local(fsm_ref))}" {{')
        lines.append(f'    label="FSM {_esc(g.value(fsm_ref, NS_FSM.name))}";')
        lines.append(f'    style=rounded; color="{colour}"; fontcolor="{colour}"; fontsize=10;')
        lines += _fsm_body(g, fsm_ref, "    ", entry=False, colour=colour,
                           awaited={state for _, fsm, _, state in awaited if fsm == fsm_ref})
        lines.append("  }")

    # What the seam actually is: the node dispatches an event into the machine and
    # blocks until it reaches a state, so the link is drawn to that state and says
    # which event it sent to get there.
    # The seam, drawn short: each node drops into the machine it drives (the arrow is
    # clipped at the cluster, so it never has to reach across the drawing) and says what
    # it sends and what it waits for. Where it ends up is outlined inside the machine.
    for nid, fsm_ref, event, state in awaited:
        colour = colour_of[fsm_ref]
        lines.append(
            f'  "{_esc(nid)}" -> "{_esc(g.value(fsm_ref, NS_FSM["start-state"]))}"'
            f' [lhead="cluster_fsm_{_ident(_local(fsm_ref))}",'
            f' label="sends {_esc(event)}\\nawaits {_esc(_local(state))}",'
            f' style=dashed, color="{colour}", fontcolor="{colour}"];'
        )
    lines.append("}")
    return "\n".join(lines) + "\n"
