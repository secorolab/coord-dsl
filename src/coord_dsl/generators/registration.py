from textx import GeneratorDesc, LanguageDesc, metamodel_from_file
from textx.scoping import providers as scoping_providers
from coord_dsl.generators.classes import (
    NamespaceDeclare,
    State,
    Event,
    Transition,
    FiredEvent,
    Reaction,
    FSM,
)
from coord_dsl.generators.fsm_graph import get_fsm_graph
from importlib.resources import files

GRAMMAR_PATH = str(files("coord_dsl.metamodels").joinpath("fsm.tx"))

__SUPPORTED_GRAPH_FORMATS = ["ttl", "nt", "xml", "json-ld"]

def fsm_metamodel():
    mm = metamodel_from_file(
        GRAMMAR_PATH,
        classes=[
            NamespaceDeclare,
            State,
            Event,
            Transition,
            FiredEvent,
            Reaction,
            FSM,
        ],
    )
    return mm

def _expand_iris(fsm: FSM) -> None:
    base = fsm.namespace.uri if fsm.namespace else ""
    fsm.uri = base + fsm.name
    for obj in fsm._all_entities():
        obj.uri = base + obj.name

fsm_lang = LanguageDesc(
    name="coord_dsl_fsm",
    pattern="*.fsm",
    description="Finite State Machine DSL",
    metamodel=fsm_metamodel,
)

def graph_gen_console(metamodel, model, output_path, overwrite, debug, **kwargs):
    _expand_iris(model)

    g = get_fsm_graph(model)

    ser_args = {"indent": 2}

    if "autocompact" in kwargs:
        ser_args["auto_compact"] = True
    else:
        ser_args["auto_compact"] = False

    format = kwargs.get("format", "json-ld")
    if format not in __SUPPORTED_GRAPH_FORMATS:
        raise ValueError(f"Unsupported graph format '{format}', supported formats are: {__SUPPORTED_GRAPH_FORMATS}")

    ser_args["format"] = format

    print(g.serialize(**ser_args))


fsm_console_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="console",
    description="Prints the loaded model to console",
    generator=graph_gen_console,
)
