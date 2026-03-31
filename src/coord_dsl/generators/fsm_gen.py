import json
from dataclasses import dataclass, field
from textx import generator
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, XSD
from rdf_utils.uri import URL_SECORO_MM


__GRAPH_FORMAT_EXT = {"json-ld": "json", "ttl": "ttl", "xml": "xml"}


@dataclass
class FSMData:
    name: str = ""
    ns: str = ""
    ns_uri: str = ""
    description: str = ""
    states: list = field(default_factory=list)
    start_state: str = ""
    current_state: str = ""
    end_state: str = ""
    events: list = field(default_factory=list)
    transitions: list = field(default_factory=list)
    reactions: list = field(default_factory=list)
    transitions_table: dict = field(default_factory=dict)
    reactions_table: dict = field(default_factory=dict)

    def to_json(self):
        return json.dumps(
            {
                "name": self.name,
                "description": self.description,
                "states": self.states,
                "start_state": self.start_state,
                "current_state": self.current_state,
                "end_state": self.end_state,
                "events": self.events,
                "transitions": self.transitions,
                "reactions": self.reactions,
                "transitions_table": self.transitions_table,
                "reactions_table": self.reactions_table,
            },
            indent=4,
        )


def parse_fsm(model):
    fsm = FSMData()

    fsm.name = model.name.local
    fsm.description = model.description

    fsm.states = [state.name for state in model.states]

    fsm.start_state = model.start_state.name
    fsm.current_state = model.current_state.name
    fsm.end_state = model.end_state.name

    fsm.events = [event.name for event in model.events]

    for transition in model.transitions:
        fsm.transitions.append(transition.name)
        fsm.transitions_table[transition.name] = {
            "from": transition.from_state.name,
            "to": transition.to_state.name,
        }

    for reaction in model.reactions:
        fsm.reactions.append(reaction.name)
        fsm.reactions_table[reaction.name] = {
            "when": reaction.when.name,
            "do": reaction.do.name,
            "num_fires": len(reaction.fires),
            "fires": [event.name for event in reaction.fires]
            if len(reaction.fires) > 0
            else None,
        }

    return fsm


def get_fsm_graph(fsm: FSMData, **kwargs):
    g = Graph()

    URI_MM_FSM = f"{URL_SECORO_MM}/behaviour/fsm#"
    URI_MM_EL = f"{URL_SECORO_MM}/behaviour/event_loop#"

    NS_FSM = Namespace(URI_MM_FSM)
    NS_EL = Namespace(URI_MM_EL)

    URI_M_FSM = f"{fsm.ns_uri}#"
    NS_M_FSM = Namespace(URI_M_FSM)

    g.bind("fsm", NS_FSM)
    g.bind("el", NS_EL)
    g.bind(fsm.ns, NS_M_FSM)

    name = fsm.name

    g.add((NS_M_FSM[name], RDF.type, NS_FSM.FSM))
    g.add((NS_M_FSM[name], NS_FSM.name, Literal(name)))
    g.add((NS_M_FSM[name], NS_FSM.description, Literal(fsm.description)))

    g.add((NS_M_FSM[name], NS_FSM["start-state"], NS_M_FSM[fsm.start_state]))
    g.add((NS_M_FSM[name], NS_FSM["end-state"], NS_M_FSM[fsm.end_state]))
    g.add((NS_M_FSM[name], NS_FSM["current-state"], NS_M_FSM[fsm.current_state]))

    for state in fsm.states:
        g.add((NS_M_FSM[state], RDF.type, NS_FSM.State))
        g.add((NS_M_FSM[name], NS_FSM.states, NS_M_FSM[state]))

    for event in fsm.events:
        g.add((NS_M_FSM[event], RDF.type, NS_EL.Event))
        g.add((NS_M_FSM[name], NS_FSM.events, NS_M_FSM[event]))

    for transition in fsm.transitions:
        g.add((NS_M_FSM[transition], RDF.type, NS_FSM.Transition))
        g.add((NS_M_FSM[name], NS_FSM.transitions, NS_M_FSM[transition]))

        from_state = fsm.transitions_table[transition]["from"]
        to_state = fsm.transitions_table[transition]["to"]

        g.add((NS_M_FSM[transition], NS_FSM["transition-from"], NS_M_FSM[from_state]))
        g.add((NS_M_FSM[transition], NS_FSM["transition-to"], NS_M_FSM[to_state]))

    for reaction in fsm.reactions:
        g.add((NS_M_FSM[reaction], RDF.type, NS_FSM.Reaction))
        g.add((NS_M_FSM[name], NS_FSM.reactions, NS_M_FSM[reaction]))

        when = fsm.reactions_table[reaction]["when"]
        do = fsm.reactions_table[reaction]["do"]
        fires = fsm.reactions_table[reaction]["fires"]

        g.add((NS_M_FSM[reaction], NS_FSM["when-event"], NS_M_FSM[when]))
        g.add((NS_M_FSM[reaction], NS_FSM["do-transition"], NS_M_FSM[do]))
        if fires is not None:
            for event in fires:
                g.add((NS_M_FSM[reaction], NS_FSM["fires-events"], NS_M_FSM[event]))

    context = {"fsm": URI_MM_FSM, "el": URI_MM_EL, "xsd": str(XSD), fsm.ns: URI_M_FSM}

    return g, context


@generator("fsm", "graph")
def fsm_graph_gen(metamodel, model, output_path, overwrite, debug, **kwargs):
    """Generates a .jsonld file with the FSM datastructures"""

    assert model.name.ns is not None and model.name.ns != "", (
        "Namespace is required for Graph generation"
    )

    print(f"Generating JSON-LD for FSM: {model.name}")

    fsm = parse_fsm(model)
    fsm.ns = model.name.ns.name
    fsm.ns_uri = model.name.ns.uri

    g, context = get_fsm_graph(fsm, **kwargs)

    g_format = kwargs.get("format", "json-ld")

    assert g_format in __GRAPH_FORMAT_EXT, (
        f"Unsupported graph format '{g_format}', supported formats are: {list(__GRAPH_FORMAT_EXT.keys())}"
    )

    if not output_path:
        model_path = Path(model._tx_filename).parent
        output_path = f"{model_path}/{fsm.name}.fsm.{__GRAPH_FORMAT_EXT[g_format]}"

    ser_kwargs = {
        "destination": output_path,
        "format": g_format,
        "indent": 4,
        "context": context,
    }

    if "nocompact" in kwargs:
        ser_kwargs["auto_compact"] = False
    else:
        ser_kwargs["auto_compact"] = True

    g.serialize(**ser_kwargs)
    print(f"FSM JSON-LD generated at {output_path}")


@generator("fsm", "console")
def fsm_console_gen(metamodel, model, output_path, overwrite, debug, **kwargs):
    """Prints the FSM datastructures to the console"""
    print(f"Generating FSM: {model.name}")

    g_format = kwargs.get("format", "json")

    if g_format != "json":
        assert g_format in __GRAPH_FORMAT_EXT, (
            f"Unsupported graph format '{g_format}', supported formats are: {list(__GRAPH_FORMAT_EXT.keys())}"
        )

    fsm = parse_fsm(model)
    if g_format == "json":
        print(fsm.to_json())
    else:
        assert model.name.ns is not None and model.name.ns != "", (
            "Namespace is required for Graph generation"
        )
        fsm.ns = model.name.ns.name
        fsm.ns_uri = model.name.ns.uri
        g, context = get_fsm_graph(fsm, **kwargs)
        print(
            g.serialize(
                format=g_format,
                indent=4,
                context=context,
                auto_compact=not kwargs.get("nocompact", False),
            )
        )


@generator("fsm", "cpp")
def fsm_cpp_gen(metamodel, model, output_path, overwrite, debug, **kwargs):
    """Generates a .hpp file with the FSM datastructures"""

    print(f"Generating C code for FSM: {model.name}")

    # get module path
    module_path = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(module_path / "templates"))
    template = env.get_template("fsm.hpp.jinja2")

    fsm = parse_fsm(model)

    fsm_name = model.name

    output = template.render(
        {
            "data": fsm,
        }
    )

    if not output_path:
        model_path = Path(model._tx_filename).parent
        output_path = f"{model_path}/{fsm_name}.fsm.hpp"

    with open(output_path, "w") as f:
        f.write(output)
    print(f"FSM C code generated at {output_path}")


@generator("fsm", "py")
def fsm_py_gen(metamodel, model, output_path, overwrite, debug, **kwargs):
    """Generates a .py file with the FSM datastructures"""

    print(f"Generating Python code for FSM: {model.name}")

    # get module path
    module_path = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(module_path / "templates"))
    template = env.get_template("fsm.py.jinja2")

    fsm = parse_fsm(model)

    fsm_name = model.name

    output = template.render(
        {
            "data": fsm,
        }
    )

    if not output_path:
        model_path = Path(model._tx_filename).parent
        output_path = f"{model_path}/fsm_{fsm_name}.py"

    with open(output_path, "w") as f:
        f.write(output)
    print(f"FSM C code generated at {output_path}")


@generator("fsm", "json")
def fsm_json_gen(metamodel, model, output_path, overwrite, debug, **kwargs):
    """Generates a .json file with the FSM datastructures"""

    print(f"Generating JSON for FSM: {model.name}")

    fsm = parse_fsm(model)

    if not output_path:
        model_path = Path(model._tx_filename).parent
        output_path = f"{model_path}/{model.name}.fsm.json"

    with open(output_path, "w") as f:
        f.write(fsm.to_json())
    print(f"FSM JSON generated at {output_path}")
