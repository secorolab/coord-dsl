# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Render an FSM's RDF graph as graphviz."""

from rdflib import Namespace
from rdflib.namespace import split_uri
from rdf_utils.namespace import URL_SECORO_MM

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


def _fsm_body(g, fsm_ref, indent, entry=True, awaited=(), colour=None):
    """The states and the reactions that join them, as dot lines."""
    start = g.value(fsm_ref, NS_FSM["start-state"])
    end = g.value(fsm_ref, NS_FSM["end-state"])
    lines = []

    if entry:
        lines.append(
            f'{indent}"__entry__" [shape=point, width=0.12, '
            'fillcolor="#202124", color="#202124"];'
        )
        lines.append(f'{indent}"__entry__" -> "{_esc(start)}";')
    for state in sorted(g.objects(fsm_ref, NS_FSM.states), key=str):
        attrs = [f'label="{_esc(_local(state))}"']
        if state == end:
            attrs.append('peripheries=2, fillcolor="#e6f4ea"')
        elif state == start:
            attrs.append('fillcolor="#e8f0fe"')
        if state in awaited:
            attrs.append(f'color="{colour}", penwidth=2')
        lines.append(f'{indent}"{_esc(state)}" [{", ".join(attrs)}];')

    reacted = set()
    for reaction in sorted(g.objects(fsm_ref, NS_FSM.reactions), key=str):
        transition = g.value(reaction, NS_FSM["do-transition"])
        reacted.add(transition)
        label = [_local(g.value(reaction, NS_FSM["when-event"]))]
        fires = sorted(_local(e) for e in g.objects(reaction, NS_FSM["fires-events"]))
        if fires:
            label.append("fires " + ", ".join(fires))
        text = "\\n".join(_esc(line) for line in label)
        lines.append(
            f'{indent}"{_esc(g.value(transition, NS_FSM["transition-from"]))}"'
            f' -> "{_esc(g.value(transition, NS_FSM["transition-to"]))}"'
            f' [label="{text}"];'
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
