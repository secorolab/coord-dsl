# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdf_utils.namespace import URL_SECORO_MM

from coord_dsl.classes.fsm import FSM


def get_fsm_graph(model) -> tuple[Graph, dict, URIRef]:
    fsm = getattr(model, "fsm", None)
    assert isinstance(fsm, FSM), "Model does not contain an FSM definition"

    uri_fsm = f"{URL_SECORO_MM}/behaviour/fsm#"
    uri_event_loop = f"{URL_SECORO_MM}/behaviour/event_loop#"
    ns_fsm = Namespace(uri_fsm)
    ns_event_loop = Namespace(uri_event_loop)

    graph = Graph()
    graph.bind("fsm", ns_fsm)
    graph.bind("el", ns_event_loop)

    ns_model = Namespace(fsm.namespace)
    graph.bind(fsm.ns_prefix, ns_model)

    assert fsm.uri is not None, "FSM must have a URI"

    graph.add((fsm.uri, RDF.type, ns_fsm.FSM))
    graph.add((fsm.uri, ns_fsm.name, Literal(fsm.name)))
    if fsm.description:
        graph.add((fsm.uri, ns_fsm.description, Literal(fsm.description)))

    graph.add((fsm.uri, ns_fsm["start-state"], URIRef(fsm.start_state.uri)))
    graph.add((fsm.uri, ns_fsm["end-state"], URIRef(fsm.end_state.uri)))
    graph.add((fsm.uri, ns_fsm["current-state"], URIRef(fsm.start_state.uri)))

    for state in fsm.states:
        graph.add((URIRef(state.uri), RDF.type, ns_fsm.State))
        graph.add((fsm.uri, ns_fsm.states, URIRef(state.uri)))

    for event in fsm.events:
        graph.add((URIRef(event.uri), RDF.type, ns_event_loop.Event))
        graph.add((fsm.uri, ns_fsm.events, URIRef(event.uri)))

    for transition in fsm.transitions:
        graph.add((URIRef(transition.uri), RDF.type, ns_fsm.Transition))
        graph.add((fsm.uri, ns_fsm.transitions, URIRef(transition.uri)))
        graph.add(
            (URIRef(transition.uri), ns_fsm["transition-from"], URIRef(transition.from_state.uri))
        )
        graph.add(
            (URIRef(transition.uri), ns_fsm["transition-to"], URIRef(transition.to_state.uri))
        )

    for reaction in fsm.reactions:
        graph.add((URIRef(reaction.uri), RDF.type, ns_fsm.Reaction))
        graph.add((fsm.uri, ns_fsm.reactions, URIRef(reaction.uri)))
        graph.add((URIRef(reaction.uri), ns_fsm["when-event"], URIRef(reaction.when.uri)))
        graph.add((URIRef(reaction.uri), ns_fsm["do-transition"], URIRef(reaction.do.uri)))
        for fired_event in reaction.fired_events:
            graph.add(
                (URIRef(reaction.uri), ns_fsm["fires-events"], URIRef(fired_event.uri))
            )

    context = {"fsm": uri_fsm, "el": uri_event_loop, fsm.ns_prefix: ns_model}
    return graph, context, fsm.uri
