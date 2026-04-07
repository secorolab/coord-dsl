import json
from dataclasses import dataclass, field
from textx import generator
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, XSD, URIRef
from rdf_utils.uri import URL_SECORO_MM
from coord_dsl.generators.classes import *


def get_fsm_graph(model: FSM) -> Graph:
    print(f"Generating FSM graph for {model.name}")

    assert model.namespace is not None and model.namespace.uri != "", (
        "Namespace is required for Graph generation"
    )

    URI_MM_FSM = f"{URL_SECORO_MM}/behaviour/fsm#"
    URI_MM_EL  = f"{URL_SECORO_MM}/behaviour/event_loop#"

    NS_FSM = Namespace(URI_MM_FSM)
    NS_EL  = Namespace(URI_MM_EL)
    NS_MODEL = Namespace(model.namespace.uri)

    g = Graph()
    g.bind("fsm", NS_FSM)
    g.bind("el", NS_EL)
    g.bind(model.name, NS_MODEL)

    g.add((URIRef(model.uri), RDF.type, NS_FSM.FSM))
    g.add((URIRef(model.uri), NS_FSM.name, Literal(model.name)))
    if model.description is not None:
        g.add((URIRef(model.uri), NS_FSM.description, Literal(model.description)))

    g.add((URIRef(model.uri), NS_FSM["start-state"], URIRef(model.start_state.uri)))
    g.add((URIRef(model.uri), NS_FSM["end-state"], URIRef(model.end_state.uri)))
    g.add((URIRef(model.uri), NS_FSM["current-state"], URIRef(model.start_state.uri)))

    for state in model.states:
        g.add((URIRef(state.uri), RDF.type, NS_FSM.State))
        g.add((URIRef(model.uri), NS_FSM.states, URIRef(state.uri)))

    for event in model.events:
        g.add((URIRef(event.uri), RDF.type, NS_EL.Event))
        g.add((URIRef(model.uri), NS_FSM.events, URIRef(event.uri)))

    for transition in model.transitions:
        g.add((URIRef(transition.uri), RDF.type, NS_FSM.Transition))
        g.add((URIRef(model.uri), NS_FSM.transitions, URIRef(transition.uri)))

        from_state = transition.from_state.uri
        to_state = transition.to_state.uri

        g.add((URIRef(transition.uri), NS_FSM["transition-from"], URIRef(from_state)))
        g.add((URIRef(transition.uri), NS_FSM["transition-to"], URIRef(to_state)))

    for reaction in model.reactions:
        g.add((URIRef(reaction.uri), RDF.type, NS_FSM.Reaction))
        g.add((URIRef(model.uri), NS_FSM.reactions, URIRef(reaction.uri)))

        when = reaction.when.uri
        do = reaction.do.uri
        fires = [f.event.uri for f in reaction.fires if f.event is not None]

        g.add((URIRef(reaction.uri), NS_FSM["when-event"], URIRef(when)))
        g.add((URIRef(reaction.uri), NS_FSM["do-transition"], URIRef(do)))
        for event_uri in fires:
            g.add((URIRef(reaction.uri), NS_FSM["fires-events"], URIRef(event_uri)))

    return g



# @generator("fsm", "graph")
# def fsm_graph_gen1(metamodel, model, output_path, overwrite, debug, **kwargs):
#     """Generates a .jsonld file with the FSM datastructures"""
#
#     assert model.name.ns is not None and model.name.ns != "", (
#         "Namespace is required for Graph generation"
#     )
#
#     print(f"Generating JSON-LD for FSM: {model.name}")
#
#     fsm = parse_fsm(model)
#     fsm.ns = model.name.ns.name
#     fsm.ns_uri = model.name.ns.uri
#
#     g, context = get_fsm_graph(fsm, **kwargs)
#
#     g_format = kwargs.get("format", "json-ld")
#
#     assert g_format in __GRAPH_FORMAT_EXT, (
#         f"Unsupported graph format '{g_format}', supported formats are: {list(__GRAPH_FORMAT_EXT.keys())}"
#     )
#
#     if not output_path:
#         model_path = Path(model._tx_filename).parent
#         output_path = f"{model_path}/{fsm.name}.fsm.{__GRAPH_FORMAT_EXT[g_format]}"
#
#     ser_kwargs = {
#         "destination": output_path,
#         "format": g_format,
#         "indent": 4,
#         "context": context,
#     }
#
#     if "nocompact" in kwargs:
#         ser_kwargs["auto_compact"] = False
#     else:
#         ser_kwargs["auto_compact"] = True
#
#     g.serialize(**ser_kwargs)
#     print(f"FSM JSON-LD generated at {output_path}")
#
#
# @generator("fsm", "console")
# def fsm_console_gen(metamodel, model, output_path, overwrite, debug, **kwargs):
#     """Prints the FSM datastructures to the console"""
#     print(f"Generating FSM: {model.name}")
#
#     g_format = kwargs.get("format", "json")
#
#     if g_format != "json":
#         assert g_format in __GRAPH_FORMAT_EXT, (
#             f"Unsupported graph format '{g_format}', supported formats are: {list(__GRAPH_FORMAT_EXT.keys())}"
#         )
#
#     fsm = parse_fsm(model)
#     if g_format == "json":
#         print(fsm.to_json())
#     else:
#         assert model.name.ns is not None and model.name.ns != "", (
#             "Namespace is required for Graph generation"
#         )
#         fsm.ns = model.name.ns.name
#         fsm.ns_uri = model.name.ns.uri
#         g, context = get_fsm_graph(fsm, **kwargs)
#         print(
#             g.serialize(
#                 format=g_format,
#                 indent=4,
#                 context=context,
#                 auto_compact=not kwargs.get("nocompact", False),
#             )
#         )
#
#
# @generator("fsm", "cpp")
# def fsm_cpp_gen(metamodel, model, output_path, overwrite, debug, **kwargs):
#     """Generates a .hpp file with the FSM datastructures"""
#
#     print(f"Generating C code for FSM: {model.name}")
#
#     # get module path
#     module_path = Path(__file__).parent.parent
#     env = Environment(loader=FileSystemLoader(module_path / "templates"))
#     template = env.get_template("fsm.hpp.jinja2")
#
#     fsm = parse_fsm(model)
#
#     fsm_name = model.name
#
#     output = template.render(
#         {
#             "data": fsm,
#         }
#     )
#
#     if not output_path:
#         model_path = Path(model._tx_filename).parent
#         output_path = f"{model_path}/{fsm_name}.fsm.hpp"
#
#     with open(output_path, "w") as f:
#         f.write(output)
#     print(f"FSM C code generated at {output_path}")
#
#
# @generator("fsm", "py")
# def fsm_py_gen(metamodel, model, output_path, overwrite, debug, **kwargs):
#     """Generates a .py file with the FSM datastructures"""
#
#     print(f"Generating Python code for FSM: {model.name}")
#
#     # get module path
#     module_path = Path(__file__).parent.parent
#     env = Environment(loader=FileSystemLoader(module_path / "templates"))
#     template = env.get_template("fsm.py.jinja2")
#
#     fsm = parse_fsm(model)
#
#     fsm_name = model.name
#
#     output = template.render(
#         {
#             "data": fsm,
#         }
#     )
#
#     if not output_path:
#         model_path = Path(model._tx_filename).parent
#         output_path = f"{model_path}/fsm_{fsm_name}.py"
#
#     with open(output_path, "w") as f:
#         f.write(output)
#     print(f"FSM C code generated at {output_path}")
#
#
# @generator("fsm", "json")
# def fsm_json_gen(metamodel, model, output_path, overwrite, debug, **kwargs):
#     """Generates a .json file with the FSM datastructures"""
#
#     print(f"Generating JSON for FSM: {model.name}")
#
#     fsm = parse_fsm(model)
#
#     if not output_path:
#         model_path = Path(model._tx_filename).parent
#         output_path = f"{model_path}/{model.name}.fsm.json"
#
#     with open(output_path, "w") as f:
#         f.write(fsm.to_json())
#     print(f"FSM JSON generated at {output_path}")
