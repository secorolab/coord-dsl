# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""textX registration and generators for finite-state-machine models."""

from importlib.resources import files
from pathlib import Path

from textx import GeneratorDesc, LanguageDesc, metamodel_from_file
from textx.scoping import providers as scoping_providers

from coord_dsl.generators.common import clang_format_file
from coord_dsl.generators.fsm.classes import Event, FSM, FiredEvent, Reaction, State, Transition
from coord_dsl.generators.fsm.graph import gen_cpp_header, gen_json, gen_python_code, get_fsm_graph


GRAMMAR_PATH = str(files("coord_dsl.metamodels").joinpath("fsm.tx"))
SUPPORTED_GRAPH_FORMATS = {"ttl": "ttl", "xml": "xml", "json-ld": "json"}


def fsm_metamodel():
    mm = metamodel_from_file(
        GRAMMAR_PATH,
        classes=[State, Event, Transition, FiredEvent, Reaction, FSM],
    )
    mm.register_scope_providers({"*.*": scoping_providers.FQNImportURI()})
    return mm


fsm_lang = LanguageDesc(
    name="coord_dsl_fsm",
    pattern="*.fsm",
    description="Finite State Machine DSL",
    metamodel=fsm_metamodel,
)


def graph_gen_console(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, output_path, overwrite, debug
    g, context, _ = get_fsm_graph(model)
    format = kwargs.get("format", "json-ld")
    if format not in SUPPORTED_GRAPH_FORMATS:
        raise ValueError(f"Unsupported graph format {format!r}, supported formats are: {SUPPORTED_GRAPH_FORMATS}")
    print(50 * "-")
    print(g.serialize(format=format, indent=2, context=context, auto_compact="autocompact" in kwargs))


def graph_gen_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug
    g, context, _ = get_fsm_graph(model)
    format = kwargs.get("format", "json-ld")
    if format not in SUPPORTED_GRAPH_FORMATS:
        raise ValueError(f"Unsupported graph format {format!r}, supported formats are: {SUPPORTED_GRAPH_FORMATS}")
    if not output_path:
        output_path = Path(model._tx_filename).parent / f"{model.fsm.name}.{SUPPORTED_GRAPH_FORMATS[format]}"
    with open(output_path, "w") as f:
        f.write(g.serialize(format=format, indent=2, context=context, auto_compact="autocompact" in kwargs))
    print(f"FSM graph generated at {output_path}")


def gen_cpp(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug, kwargs
    g, _, fsm_ref = get_fsm_graph(model)
    rendered = gen_cpp_header(gen_json(g, fsm_ref))
    output_path = output_path or Path(model._tx_filename).parent / f"{model.fsm.name}.hpp"
    with open(output_path, "w") as f:
        f.write(rendered)
    clang_format_file(output_path)
    print(f"FSM C code generated at {output_path}")


def gen_python(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug, kwargs
    g, _, fsm_ref = get_fsm_graph(model)
    rendered = gen_python_code(gen_json(g, fsm_ref))
    output_path = output_path or Path(model._tx_filename).parent / f"{model.fsm.name}.py"
    with open(output_path, "w") as f:
        f.write(rendered)
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
