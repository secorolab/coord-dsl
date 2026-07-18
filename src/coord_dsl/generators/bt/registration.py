# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""textX registration and generators for behaviour-tree models."""

from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from textx import GeneratorDesc, LanguageDesc, metamodel_from_file
from textx.scoping import providers as scoping_providers

from rdf_utils.naming import get_valid_var_name
from coord_dsl.generators.common import clang_format_file
from coord_dsl.generators.bt.classes import (
    BehaviourDecl,
    BehaviourTree,
    BlackboardRef,
    CompositeNode,
    DecoratorNode,
    EventName,
    FSMDecl,
    FSMEventNode,
    LeafNode,
    MainBehaviourTree,
    NodeGuard,
    NodeGuards,
    Port,
    PortDecl,
    Quantity,
    SubTreeNode,
)
from coord_dsl.generators.bt.graph import get_bt_graph
from coord_dsl.generators.bt.xml import BUILTIN_TAG, evented_behaviours, gen_bt_xml
from coord_dsl.generators.fsm.registration import fsm_metamodel


GRAMMAR_PATH = str(files("coord_dsl.metamodels").joinpath("bt.tx"))
BT_CLASSES = [
    BehaviourDecl,
    FSMDecl,
    PortDecl,
    BehaviourTree,
    MainBehaviourTree,
    CompositeNode,
    DecoratorNode,
    SubTreeNode,
    FSMEventNode,
    LeafNode,
    NodeGuards,
    NodeGuard,
    Port,
    Quantity,
    BlackboardRef,
    EventName,
]


def bt_metamodel():
    mm = metamodel_from_file(GRAMMAR_PATH, classes=BT_CLASSES, autokwd=True)
    mm.register_scope_providers({"*.*": scoping_providers.FQNImportURI()})
    return mm


bt_lang = LanguageDesc(
    name="bt",
    pattern="*.btree",
    description="Behaviour Tree DSL",
    metamodel=bt_metamodel,
)


def _output_name(model, ext):
    return Path(model._tx_filename).parent / f"{model.main_tree.name}.{ext}"


def gen_bt_graph_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug, kwargs
    g, context, _ = get_bt_graph(model)
    output_path = output_path or _output_name(model, "json")
    with open(output_path, "w") as f:
        f.write(g.serialize(format="json-ld", context=context, auto_compact=True, indent=2))
    print(f"BT JSON-LD generated at {output_path}")


def gen_bt_xml_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug, kwargs
    g, _, root_ref = get_bt_graph(model)
    output_path = output_path or _output_name(model, "xml")
    with open(output_path, "w") as f:
        f.write(gen_bt_xml(g, root_ref))
    print(f"BT XML generated at {output_path}")


def gen_bt_cpp_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    """Generate the runtime contract and BT.CPP registrations for a BT model."""
    del metamodel, overwrite, debug, kwargs
    graph, _, _ = get_bt_graph(model)
    template_dir = Path(__file__).parents[2] / "templates"
    template = Environment(
        loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True
    ).get_template("bt.hpp.jinja2")
    name = get_valid_var_name(model.main_tree.name)
    evented = evented_behaviours(graph)
    behaviours = []
    methods = set()
    for behaviour in model.behaviours:
        if behaviour.name in BUILTIN_TAG:
            continue
        method = f"on_{get_valid_var_name(behaviour.name)}"
        if method in methods:
            raise ValueError(f"C++ runtime method collision: {method!r}")
        methods.add(method)
        ports = [{"name": port.name, "direction": port.direction} for port in behaviour.ports]
        if behaviour.name in evented:
            ports.extend(
                {"name": event, "direction": "in"}
                for event in ("start_event", "end_event")
                if event not in {port["name"] for port in ports}
            )
        behaviours.append(
            {
                "name": behaviour.name,
                "kind": behaviour.kind,
                "method": method,
                "ports": ports,
            }
        )
    fsm_instances = []
    for fsm in model.fsms:
        path = (Path(model._tx_filename).parent / fsm.source).resolve()
        fsm_model = fsm_metamodel().model_from_file(path)
        var = get_valid_var_name(fsm.name)
        fsm_instances.append(
            {
                "name": fsm.name,
                "var": var,
                "member": f"fsm_{var}_",
                "namespace": fsm_model.fsm.name.lower(),
                "header": f"{fsm_model.fsm.name}.hpp",
                "events": [
                    {"name": event.name, "enum": get_valid_var_name(event.name).upper()}
                    for event in fsm_model.fsm.events
                ],
                "states": [
                    {"name": state.name, "enum": get_valid_var_name(state.name).upper()}
                    for state in fsm_model.fsm.states
                ],
            }
        )
    rendered = template.render(
        guard=f"{name.upper()}_BT_HPP",
        namespace=name,
        runtime_class=f"{name.title().replace('_', '')}Runtime",
        behaviours=behaviours,
        fsm_instances=fsm_instances,
    )
    output_path = output_path or _output_name(model, "hpp")
    with open(output_path, "w") as f:
        f.write(rendered)
    clang_format_file(output_path)
    print(f"BT C++ header generated at {output_path}")


bt_graph_gen = GeneratorDesc(
    language="bt",
    target="jsonld",
    description="Generates the behaviour-tree JSON-LD graph",
    generator=gen_bt_graph_file,
)
bt_xml_gen = GeneratorDesc(
    language="bt",
    target="xml",
    description="Generates BehaviorTree.CPP v4 XML from the BT graph",
    generator=gen_bt_xml_file,
)
bt_cpp_gen = GeneratorDesc(
    language="bt",
    target="cpp",
    description="Generates a BehaviorTree.CPP runtime contract and registrations",
    generator=gen_bt_cpp_file,
)
