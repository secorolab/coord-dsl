# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdf_utils.models.event_loop import (
    URI_EL_PRED_EVT_LOOP,
    URI_EL_PRED_HAS_EVT,
    URI_EL_PRED_REF_EVT,
    URI_EL_TYPE_EVT,
    URI_EL_TYPE_EVT_LOOP,
    URI_EL_TYPE_EVT_REACT,
)
from rdf_utils.namespace import NS_MM_EL, NS_OWL_TIME

from coord_dsl.classes.fsm import FSM
from coord_dsl.rdf.vocab import (
    NS_MM_FSM,
    URI_FSM_PRED_CURRENT_STATE,
    URI_FSM_PRED_DESCRIPTION,
    URI_FSM_PRED_DO_TRANSITION,
    URI_FSM_PRED_END_STATE,
    URI_FSM_PRED_FIRES_EVENTS,
    URI_FSM_PRED_NAME,
    URI_FSM_PRED_REACTIONS,
    URI_FSM_PRED_START_STATE,
    URI_FSM_PRED_STATES,
    URI_FSM_PRED_TRANSITION_FROM,
    URI_FSM_PRED_TRANSITION_TO,
    URI_FSM_PRED_TRANSITIONS,
    URI_FSM_TYPE_FSM,
    URI_FSM_TYPE_REACTION,
    URI_FSM_TYPE_STATE,
    URI_FSM_TYPE_TRANSITION,
)


def get_fsm_graph(model) -> tuple[Graph, dict, URIRef]:
    fsm = getattr(model, "fsm", None)
    assert isinstance(fsm, FSM), "Model does not contain an FSM definition"

    graph = Graph()
    graph.bind("fsm", NS_MM_FSM)
    graph.bind("el", NS_MM_EL)
    graph.bind("time", NS_OWL_TIME)

    ns_model = Namespace(fsm.namespace)
    graph.bind(fsm.ns_prefix, ns_model)

    assert fsm.uri is not None, "FSM must have a URI"

    graph.add((fsm.uri, RDF.type, URI_FSM_TYPE_FSM))
    graph.add((fsm.uri, URI_FSM_PRED_NAME, Literal(fsm.name)))
    if fsm.description:
        graph.add((fsm.uri, URI_FSM_PRED_DESCRIPTION, Literal(fsm.description)))

    graph.add((fsm.uri, URI_FSM_PRED_START_STATE, URIRef(fsm.start_state.uri)))
    graph.add((fsm.uri, URI_FSM_PRED_END_STATE, URIRef(fsm.end_state.uri)))
    graph.add((fsm.uri, URI_FSM_PRED_CURRENT_STATE, URIRef(fsm.start_state.uri)))
    graph.add((fsm.uri, URI_EL_PRED_EVT_LOOP, fsm.event_loop.uri))

    for state in fsm.states:
        graph.add((URIRef(state.uri), RDF.type, URI_FSM_TYPE_STATE))
        graph.add((fsm.uri, URI_FSM_PRED_STATES, URIRef(state.uri)))

    graph.add((fsm.event_loop.uri, RDF.type, URI_EL_TYPE_EVT_LOOP))
    for event in fsm.event_loop.events:
        graph.add((event.uri, RDF.type, URI_EL_TYPE_EVT))
        graph.add((fsm.event_loop.uri, URI_EL_PRED_HAS_EVT, event.uri))

    for transition in fsm.transitions:
        graph.add((URIRef(transition.uri), RDF.type, URI_FSM_TYPE_TRANSITION))
        graph.add((fsm.uri, URI_FSM_PRED_TRANSITIONS, URIRef(transition.uri)))
        graph.add(
            (
                URIRef(transition.uri),
                URI_FSM_PRED_TRANSITION_FROM,
                URIRef(transition.from_state.uri),
            )
        )
        graph.add(
            (
                URIRef(transition.uri),
                URI_FSM_PRED_TRANSITION_TO,
                URIRef(transition.to_state.uri),
            )
        )

    for reaction in fsm.reactions:
        graph.add((URIRef(reaction.uri), RDF.type, URI_FSM_TYPE_REACTION))
        graph.add((URIRef(reaction.uri), RDF.type, URI_EL_TYPE_EVT_REACT))
        graph.add((fsm.uri, URI_FSM_PRED_REACTIONS, URIRef(reaction.uri)))
        graph.add(
            (URIRef(reaction.uri), URI_EL_PRED_REF_EVT, URIRef(reaction.when.uri))
        )
        graph.add(
            (URIRef(reaction.uri), URI_FSM_PRED_DO_TRANSITION, URIRef(reaction.do.uri))
        )
        for fired_event in reaction.fired_events:
            graph.add(
                (
                    URIRef(reaction.uri),
                    URI_FSM_PRED_FIRES_EVENTS,
                    URIRef(fired_event.uri),
                )
            )

    context = {
        "fsm": str(NS_MM_FSM),
        "el": str(NS_MM_EL),
        "time": str(NS_OWL_TIME),
        fsm.ns_prefix: ns_model,
    }
    return graph, context, fsm.uri
