import json
from typing import List
from dataclasses import dataclass, field
from textx import generator
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, XSD, URIRef
from rdf_utils.uri import URL_SECORO_MM
from rdf_utils.naming import get_valid_var_name
from coord_dsl.generators.classes import *


def get_fsm_graph(model) -> tuple[Graph, dict]:
    fsm: FSM = getattr(model, "fsm", None)
    assert fsm is not None, "Model does not contain an FSM definition"

    URI_MM_FSM = f"{URL_SECORO_MM}/behaviour/fsm#"
    URI_MM_EL  = f"{URL_SECORO_MM}/behaviour/event_loop#"

    NS_FSM = Namespace(URI_MM_FSM)
    NS_EL  = Namespace(URI_MM_EL)

    g = Graph()
    g.bind("fsm", NS_FSM)
    g.bind("el", NS_EL)

    print(f"FSM: {fsm.name}, URI: {fsm.uri}")

    NS_MODEL = Namespace(fsm.namespace)
    URI_MODEL = fsm.uri
    g.bind(fsm.ns_prefix, NS_MODEL)

    g.add((URI_MODEL, RDF.type, NS_FSM.FSM))
    g.add((URI_MODEL, NS_FSM.name, Literal(fsm.name)))
    if fsm.description is not None:
        g.add((URI_MODEL, NS_FSM.description, Literal(fsm.description)))

    g.add((URI_MODEL, NS_FSM["start-state"], URIRef(fsm.start_state.uri)))
    g.add((URI_MODEL, NS_FSM["end-state"], URIRef(fsm.end_state.uri)))
    g.add((URI_MODEL, NS_FSM["current-state"], URIRef(fsm.start_state.uri)))

    for state in fsm.states:
        g.add((URIRef(state.uri), RDF.type, NS_FSM.State))
        g.add((URI_MODEL, NS_FSM.states, URIRef(state.uri)))

    for event in fsm.events:
        g.add((URIRef(event.uri), RDF.type, NS_EL.Event))
        g.add((URI_MODEL, NS_FSM.events, URIRef(event.uri)))

    for transition in fsm.transitions:
        g.add((URIRef(transition.uri), RDF.type, NS_FSM.Transition))
        g.add((URI_MODEL, NS_FSM.transitions, URIRef(transition.uri)))

        from_state = transition.from_state.uri
        to_state = transition.to_state.uri

        g.add((URIRef(transition.uri), NS_FSM["transition-from"], URIRef(from_state)))
        g.add((URIRef(transition.uri), NS_FSM["transition-to"], URIRef(to_state)))

    for reaction in fsm.reactions:
        g.add((URIRef(reaction.uri), RDF.type, NS_FSM.Reaction))
        g.add((URI_MODEL, NS_FSM.reactions, URIRef(reaction.uri)))

        when = reaction.when.uri
        do = reaction.do.uri
        fires = [f.event.uri for f in reaction.fires if f.event is not None]

        g.add((URIRef(reaction.uri), NS_FSM["when-event"], URIRef(when)))
        g.add((URIRef(reaction.uri), NS_FSM["do-transition"], URIRef(do)))
        for event_uri in fires:
            g.add((URIRef(reaction.uri), NS_FSM["fires-events"], URIRef(event_uri)))

    # jsonld context
    context = {
        "fsm": URI_MM_FSM,
        "el": URI_MM_EL,
        fsm.ns_prefix: NS_MODEL,
    }
    return g, context

def local_name(uri: str) -> str:
    if "#" in uri:
        return uri.split("#")[-1]
    return uri.rstrip("/").split("/")[-1]

def gen_json(g: Graph) -> dict:
    URI_MM_FSM = f"{URL_SECORO_MM}/behaviour/fsm#"
    NS_FSM = Namespace(URI_MM_FSM)

    fsm_uri = g.value(None, RDF.type, NS_FSM.FSM).toPython()
    fsm_ref = URIRef(fsm_uri)

    name = str(g.value(fsm_ref, NS_FSM.name))
    description_node = g.value(fsm_ref, NS_FSM.description)
    description = str(description_node) if description_node is not None else None

    start_state = get_valid_var_name(local_name(g.value(fsm_ref, NS_FSM["start-state"]).toPython()))
    end_state   = get_valid_var_name(local_name(g.value(fsm_ref, NS_FSM["end-state"]).toPython()))

    states = []
    state_uris = {}
    for _, _, state_uri in g.triples((fsm_ref, NS_FSM.states, None)):
        uri_s = state_uri.toPython()
        ident = get_valid_var_name(local_name(uri_s))
        states.append(ident)
        state_uris[ident] = uri_s

    events = []
    event_uris = {}
    for _, _, event_uri in g.triples((fsm_ref, NS_FSM.events, None)):
        uri_s = event_uri.toPython()
        ident = get_valid_var_name(local_name(uri_s))
        events.append(ident)
        event_uris[ident] = uri_s

    transitions_table = []
    for _, _, tr_uri in g.triples((fsm_ref, NS_FSM.transitions, None)):
        uri_s = tr_uri.toPython()
        from_state = get_valid_var_name(local_name(g.value(tr_uri, NS_FSM["transition-from"]).toPython()))
        to_state   = get_valid_var_name(local_name(g.value(tr_uri, NS_FSM["transition-to"]).toPython()))
        transitions_table.append({
            "id":         get_valid_var_name(local_name(uri_s)),
            "uri":        uri_s,
            "from_state": from_state,
            "to_state":   to_state,
        })

    reactions_table = []
    for _, _, rx_uri in g.triples((fsm_ref, NS_FSM.reactions, None)):
        uri_s = rx_uri.toPython()
        when_event    = get_valid_var_name(local_name(g.value(rx_uri, NS_FSM["when-event"]).toPython()))
        do_transition = get_valid_var_name(local_name(g.value(rx_uri, NS_FSM["do-transition"]).toPython()))
        fires = [
            get_valid_var_name(local_name(ev_uri.toPython()))
            for _, _, ev_uri in g.triples((rx_uri, NS_FSM["fires-events"], None))
        ]
        reactions_table.append({
            "id":            get_valid_var_name(local_name(uri_s)),
            "uri":           uri_s,
            "when_event":    when_event,
            "do_transition": do_transition,
            "fires_events":  fires,
            "num_fires":     len(fires),
        })

    result = {
        "name":        name,
        "description": description,
        "start_state": start_state,
        "end_state":   end_state,
        "states":      states,
        "state_uris":  state_uris,
        "events":      events,
        "event_uris":  event_uris,
        "transitions_table": transitions_table,
        "reactions_table":   reactions_table,
    }

    return result


def gen_cpp_header(ir: dict):
    """Generates a .hpp file with the FSM datastructures"""

    print(f"Generating C code for FSM: {ir['name']}")

    # get module path
    module_path = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(module_path / "templates"))
    template = env.get_template("fsm.hpp.jinja2")

    output = template.render(
        {
            "data": ir,
        }
    )

    return output

def gen_python_code(ir: dict):
    """Generates a .py file with the FSM datastructures"""

    print(f"Generating Python code for FSM: {ir['name']}")

    # get module path
    module_path = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(module_path / "templates"))
    template = env.get_template("fsm.py.jinja2")

    output = template.render(
        {
            "data": ir,
        }
    )

    return output

