# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""textX registration and generators for coordination models."""

from importlib.resources import files
from pathlib import Path

from textx import GeneratorDesc, LanguageDesc, metamodel_from_file
from textx.scoping import providers as scoping_providers

from coord_dsl.classes.bt import BehaviourDecl, BehaviourSet, BehaviourTree
from coord_dsl.classes.event_loop import Event, EventLoop, EventRef, Flag
from coord_dsl.classes.fsm import FSM, Reaction, State, Transition
from coord_dsl.generators.dot import FORMATS, fsm_dot, write_dot
from coord_dsl.generators.bt import gen_dot as gen_bt_dot
from coord_dsl.generators.bt import gen_json as gen_bt_json
from coord_dsl.generators.bt import gen_python_code as gen_bt_python_code
from coord_dsl.generators.bt import gen_xml as gen_bt_xml
from coord_dsl.generators.fsm import gen_cpp_header, gen_json, gen_python_code
from coord_dsl.generators.provenance import record
from coord_dsl.rdf.bt import get_bt_graph
from coord_dsl.rdf.fsm import get_fsm_graph


GRAMMAR_PATH = str(files("coord_dsl.metamodels").joinpath("fsm.tx"))
BT_GRAMMAR_PATH = str(files("coord_dsl.metamodels").joinpath("bt.tx"))
SUPPORTED_GRAPH_FORMATS = {"ttl": "ttl", "xml": "xml", "json-ld": "ld.json"}


def fsm_metamodel():
    mm = metamodel_from_file(
        GRAMMAR_PATH,
        classes=[EventLoop, Event, Flag, EventRef, State, Transition, Reaction, FSM],
    )
    mm.register_scope_providers({"*.*": scoping_providers.FQNImportURI()})
    return mm


fsm_lang = LanguageDesc(
    name="coord_dsl_fsm",
    pattern="*.fsm",
    description="Finite State Machine DSL",
    metamodel=fsm_metamodel,
)


def bt_metamodel():
    mm = metamodel_from_file(
        BT_GRAMMAR_PATH,
        classes=[EventLoop, Event, Flag, BehaviourSet, BehaviourDecl, BehaviourTree],
    )
    mm.register_scope_providers({"*.*": scoping_providers.FQNImportURI()})
    return mm


bt_lang = LanguageDesc(
    name="coord_dsl_bt",
    pattern="*.btree",
    description="Behaviour Tree DSL",
    metamodel=bt_metamodel,
)


def bt_graph_gen_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug
    g, _ = get_bt_graph(model)
    format = kwargs.get("format", "json-ld")
    if format not in SUPPORTED_GRAPH_FORMATS:
        raise ValueError(
            f"Unsupported graph format {format!r}, supported formats are: {SUPPORTED_GRAPH_FORMATS}"
        )
    if not output_path:
        output_path = (
            Path(model._tx_filename).parent
            / f"{model.trees[-1].name}.{SUPPORTED_GRAPH_FORMATS[format]}"
        )
    with open(output_path, "w") as f:
        f.write(
            g.serialize(
                format=format,
                indent=2,
                auto_compact="autocompact" in kwargs,
            )
        )
    record(model, "graph", output_path)
    print(f"BT graph generated at {output_path}")


def gen_bt_python(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug, kwargs
    g, entry = get_bt_graph(model)
    rendered = gen_bt_python_code(gen_bt_json(g, entry))
    output_path = (
        output_path or Path(model._tx_filename).parent / f"{model.trees[-1].name}.py"
    )
    with open(output_path, "w") as f:
        f.write(rendered)
    record(model, "python", output_path)
    print(f"BT py_trees code generated at {output_path}")


def gen_bt_xml_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug, kwargs
    g, entry = get_bt_graph(model)
    rendered = gen_bt_xml(gen_bt_json(g, entry))
    output_path = (
        output_path or Path(model._tx_filename).parent / f"{model.trees[-1].name}.xml"
    )
    with open(output_path, "w") as f:
        f.write(rendered)
    record(model, "xml", output_path)
    print(f"BT BehaviorTree.CPP XML generated at {output_path}")


def gen_bt_dot_console(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, output_path, overwrite, debug, kwargs
    g, entry = get_bt_graph(model)
    print(gen_bt_dot(gen_bt_json(g, entry), g), end="")


def gen_bt_dot_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, debug
    img_format = kwargs.get("format", "dot")
    if img_format not in ("dot",) + FORMATS:
        raise ValueError(
            f"unhandled format {img_format!r} for the behaviour tree, try {['dot', *FORMATS]}"
        )
    g, entry = get_bt_graph(model)
    output_path = (
        output_path
        or Path(model._tx_filename).parent / f"{model.trees[-1].name}.{img_format}"
    )
    if Path(output_path).exists() and not overwrite:
        print(f"not overwriting existing file '{output_path}'")
        return
    write_dot(gen_bt_dot(gen_bt_json(g, entry), g), output_path, img_format)
    record(model, "dot", output_path)
    print(f"BT drawn at {output_path}")


bt_dot_gen = GeneratorDesc(
    language="coord_dsl_bt",
    target="dot",
    description="Draws the behaviour tree with graphviz",
    generator=gen_bt_dot_file,
)
bt_dot_console_gen = GeneratorDesc(
    language="coord_dsl_bt",
    target="dot_console",
    description="Prints the behaviour tree's graphviz source",
    generator=gen_bt_dot_console,
)
bt_python_gen = GeneratorDesc(
    language="coord_dsl_bt",
    target="python",
    description="Generates a Python module building the tree with py_trees",
    generator=gen_bt_python,
)
bt_xml_gen = GeneratorDesc(
    language="coord_dsl_bt",
    target="xml",
    description="Generates a BehaviorTree.CPP v4 XML file",
    generator=gen_bt_xml_file,
)
bt_file_gen = GeneratorDesc(
    language="coord_dsl_bt",
    target="graph",
    description="Generates a file with the behaviour tree graph in RDF format",
    generator=bt_graph_gen_file,
)


def graph_gen_console(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, output_path, overwrite, debug
    g, _ = get_fsm_graph(model)
    format = kwargs.get("format", "json-ld")
    if format not in SUPPORTED_GRAPH_FORMATS:
        raise ValueError(
            f"Unsupported graph format {format!r}, supported formats are: {SUPPORTED_GRAPH_FORMATS}"
        )
    print(50 * "-")
    print(
        g.serialize(
            format=format,
            indent=2,
            auto_compact="autocompact" in kwargs,
        )
    )


def graph_gen_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug
    g, _ = get_fsm_graph(model)
    format = kwargs.get("format", "json-ld")
    if format not in SUPPORTED_GRAPH_FORMATS:
        raise ValueError(
            f"Unsupported graph format {format!r}, supported formats are: {SUPPORTED_GRAPH_FORMATS}"
        )
    if not output_path:
        output_path = (
            Path(model._tx_filename).parent
            / f"{model.fsm.name}.{SUPPORTED_GRAPH_FORMATS[format]}"
        )
    with open(output_path, "w") as f:
        f.write(
            g.serialize(
                format=format,
                indent=2,
                auto_compact="autocompact" in kwargs,
            )
        )
    record(model, "graph", output_path)
    print(f"FSM graph generated at {output_path}")


def gen_fsm_dot_console(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, output_path, overwrite, debug, kwargs
    g, fsm_ref = get_fsm_graph(model)
    print(fsm_dot(g, fsm_ref), end="")


def gen_fsm_dot_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, debug
    img_format = kwargs.get("format", "dot")
    if img_format not in ("dot",) + FORMATS:
        raise ValueError(
            f"unhandled format {img_format!r} for the state-machine graph, try {['dot', *FORMATS]}"
        )
    g, fsm_ref = get_fsm_graph(model)
    output_path = (
        output_path
        or Path(model._tx_filename).parent / f"{model.fsm.name}.{img_format}"
    )
    if Path(output_path).exists() and not overwrite:
        print(f"not overwriting existing file '{output_path}'")
        return
    write_dot(fsm_dot(g, fsm_ref), output_path, img_format)
    record(model, "dot", output_path)
    print(f"FSM graph drawn at {output_path}")


def gen_cpp(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug, kwargs
    g, fsm_ref = get_fsm_graph(model)
    rendered = gen_cpp_header(gen_json(g, fsm_ref))
    output_path = (
        output_path or Path(model._tx_filename).parent / f"{model.fsm.name}.hpp"
    )
    with open(output_path, "w") as f:
        f.write(rendered)
    record(model, "cpp", output_path)
    print(f"FSM C code generated at {output_path}")


def gen_python(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug, kwargs
    g, fsm_ref = get_fsm_graph(model)
    rendered = gen_python_code(gen_json(g, fsm_ref))
    output_path = (
        output_path or Path(model._tx_filename).parent / f"{model.fsm.name}.py"
    )
    with open(output_path, "w") as f:
        f.write(rendered)
    record(model, "python", output_path)
    print(f"FSM Python code generated at {output_path}")


fsm_console_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="console",
    description="Prints the loaded model to console",
    generator=graph_gen_console,
)
fsm_file_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="graph",
    description="Generates a file with the FSM graph in RDF format",
    generator=graph_gen_file,
)
fsm_dot_console_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="dot-console",
    description="Print the state machine as a graphviz graph",
    generator=gen_fsm_dot_console,
)
fsm_dot_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="dot",
    description="Draw the state machine: states joined by the reactions that fire them."
    " Formats: dot (default), png, svg, pdf",
    generator=gen_fsm_dot_file,
)
fsm_cpp_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="cpp",
    description="Generates C++ code for the FSM",
    generator=gen_cpp,
)
fsm_python_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="python",
    description="Generates Python code for the FSM",
    generator=gen_python,
)
