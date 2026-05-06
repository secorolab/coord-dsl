from collections.abc import Mapping
from jinja2 import Environment, FileSystemLoader
from os.path import basename
from pathlib import Path
from typing import cast
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from rdf_utils.uri import URL_SECORO_MM
from rdf_utils.naming import get_valid_var_name
from coord_dsl.generators.classes import FSM


def get_fsm_graph(model: object) -> tuple[Graph, dict[str, str | Namespace], URIRef]:
    fsm = getattr(model, "fsm", None)
    assert isinstance(fsm, FSM), "Model does not contain an FSM definition"

    URI_MM_FSM = f"{URL_SECORO_MM}/behaviour/fsm#"
    URI_MM_EL = f"{URL_SECORO_MM}/behaviour/event_loop#"

    NS_FSM = Namespace(URI_MM_FSM)
    NS_EL = Namespace(URI_MM_EL)

    g = Graph()
    g.bind("fsm", NS_FSM)
    g.bind("el", NS_EL)

    fsm_name = cast(str | None, getattr(fsm, "name", None))
    assert fsm_name is not None, "FSM is missing a name"
    print(f"FSM: {fsm_name}, URI: {fsm.uri}")

    NS_MODEL = Namespace(fsm.namespace)
    g.bind(fsm.ns_prefix, NS_MODEL)

    g.add((fsm.uri, RDF.type, NS_FSM.FSM))
    g.add((fsm.uri, NS_FSM.name, Literal(fsm_name)))
    if fsm.description is not None:
        g.add((fsm.uri, NS_FSM.description, Literal(fsm.description)))

    g.add((fsm.uri, NS_FSM["start-state"], URIRef(fsm.start_state.uri)))
    g.add((fsm.uri, NS_FSM["end-state"], URIRef(fsm.end_state.uri)))
    g.add((fsm.uri, NS_FSM["current-state"], URIRef(fsm.start_state.uri)))

    for state in fsm.states:
        g.add((URIRef(state.uri), RDF.type, NS_FSM.State))
        g.add((fsm.uri, NS_FSM.states, URIRef(state.uri)))

    for event in fsm.events:
        g.add((URIRef(event.uri), RDF.type, NS_EL.Event))
        g.add((fsm.uri, NS_FSM.events, URIRef(event.uri)))

    for transition in fsm.transitions:
        g.add((URIRef(transition.uri), RDF.type, NS_FSM.Transition))
        g.add((fsm.uri, NS_FSM.transitions, URIRef(transition.uri)))

        from_state = transition.from_state.uri
        to_state = transition.to_state.uri

        g.add((URIRef(transition.uri), NS_FSM["transition-from"], URIRef(from_state)))
        g.add((URIRef(transition.uri), NS_FSM["transition-to"], URIRef(to_state)))

    for reaction in fsm.reactions:
        g.add((URIRef(reaction.uri), RDF.type, NS_FSM.Reaction))
        g.add((fsm.uri, NS_FSM.reactions, URIRef(reaction.uri)))

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
    return g, context, fsm.uri


def iri_basename(uri: str) -> str:
    return basename(uri.replace("#", "/").rstrip("/"))


def gen_json(g: Graph, fsm_ref: URIRef) -> dict[str, object]:
    URI_MM_FSM = f"{URL_SECORO_MM}/behaviour/fsm#"
    NS_FSM = Namespace(URI_MM_FSM)

    name = str(g.value(fsm_ref, NS_FSM.name))
    description_node = g.value(fsm_ref, NS_FSM.description)
    description = str(description_node) if description_node is not None else None

    start_state_node = g.value(fsm_ref, NS_FSM["start-state"])
    assert start_state_node is not None, "FSM graph missing start state"
    start_state = get_valid_var_name(iri_basename(str(start_state_node))).upper()

    end_state_node = g.value(fsm_ref, NS_FSM["end-state"])
    assert end_state_node is not None, "FSM graph missing end state"
    end_state = get_valid_var_name(iri_basename(str(end_state_node))).upper()

    states: list[str] = []
    state_uris: dict[str, str] = {}
    for _, _, state_uri in g.triples((fsm_ref, NS_FSM.states, None)):
        uri_s = str(state_uri)
        ident = get_valid_var_name(iri_basename(uri_s)).upper()
        states.append(ident)
        state_uris[ident] = uri_s

    events: list[str] = []
    event_uris: dict[str, str] = {}
    for _, _, event_uri in g.triples((fsm_ref, NS_FSM.events, None)):
        uri_s = str(event_uri)
        ident = get_valid_var_name(iri_basename(uri_s)).upper()
        events.append(ident)
        event_uris[ident] = uri_s

    transitions_table: list[dict[str, str]] = []
    for _, _, tr_uri in g.triples((fsm_ref, NS_FSM.transitions, None)):
        uri_s = str(tr_uri)
        from_state_node = g.value(tr_uri, NS_FSM["transition-from"])
        assert from_state_node is not None, "FSM graph missing transition source"
        assert isinstance(from_state_node, URIRef), (
            "FSM transition source must be a URIRef"
        )
        from_state = get_valid_var_name(iri_basename(str(from_state_node))).upper()

        to_state_node = g.value(tr_uri, NS_FSM["transition-to"])
        assert to_state_node is not None, "FSM graph missing transition target"
        assert isinstance(to_state_node, URIRef), (
            "FSM transition target must be a URIRef"
        )
        to_state = get_valid_var_name(iri_basename(str(to_state_node))).upper()
        transitions_table.append(
            {
                "id": get_valid_var_name(iri_basename(uri_s)).upper(),
                "uri": uri_s,
                "from_state": from_state,
                "to_state": to_state,
            }
        )

    reactions_table: list[dict[str, str | int | list[str]]] = []
    for _, _, rx_uri in g.triples((fsm_ref, NS_FSM.reactions, None)):
        uri_s = str(rx_uri)
        when_event_node = g.value(rx_uri, NS_FSM["when-event"])
        assert when_event_node is not None, "FSM graph missing reaction trigger"
        assert isinstance(when_event_node, URIRef), (
            "FSM reaction trigger must be a URIRef"
        )
        when_event = get_valid_var_name(iri_basename(str(when_event_node))).upper()

        do_transition_node = g.value(rx_uri, NS_FSM["do-transition"])
        assert do_transition_node is not None, "FSM graph missing reaction transition"
        assert isinstance(do_transition_node, URIRef), (
            "FSM reaction transition must be a URIRef"
        )
        do_transition = get_valid_var_name(
            iri_basename(str(do_transition_node))
        ).upper()
        fires = [
            get_valid_var_name(iri_basename(str(ev_uri))).upper()
            for _, _, ev_uri in g.triples((rx_uri, NS_FSM["fires-events"], None))
        ]
        reactions_table.append(
            {
                "id": get_valid_var_name(iri_basename(uri_s)).upper(),
                "uri": uri_s,
                "when_event": when_event,
                "do_transition": do_transition,
                "fires_events": fires,
                "num_fires": len(fires),
            }
        )

    result: dict[str, object] = {
        "name": name,
        "description": description,
        "start_state": start_state,
        "end_state": end_state,
        "states": states,
        "state_uris": state_uris,
        "events": events,
        "event_uris": event_uris,
        "transitions_table": transitions_table,
        "reactions_table": reactions_table,
    }

    return result


def gen_cpp_header(ir: Mapping[str, object]) -> str:
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


def gen_python_code(ir: Mapping[str, object]) -> str:
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
