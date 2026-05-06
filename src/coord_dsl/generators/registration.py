from typing import Protocol, cast
from pathlib import Path
from textx import GeneratorDesc, LanguageDesc, metamodel_from_file  # pyright: ignore[reportMissingTypeStubs,reportUnknownVariableType]
from textx.scoping import providers as scoping_providers  # pyright: ignore[reportMissingTypeStubs]

from coord_dsl.generators.classes import (
    State,
    Event,
    Transition,
    FiredEvent,
    Reaction,
    FSM,
)
from coord_dsl.generators.fsm_graph import (
    gen_cpp_header,
    get_fsm_graph,
    gen_json,
    gen_python_code,
)
from importlib.resources import files

GRAMMAR_PATH = str(files("coord_dsl.metamodels").joinpath("fsm.tx"))

__SUPPORTED_GRAPH_FORMATS = {"ttl": "ttl", "xml": "xml", "json-ld": "json"}


class ScopeProviderRegistrar(Protocol):
    def register_scope_providers(self, sp: object) -> None: ...


class ModelWithFSM(Protocol):
    fsm: FSM
    _tx_filename: str


class SerializableGraph(Protocol):
    def serialize(
        self,
        *,
        format: str,
        indent: int,
        context: dict[str, str | object],
        auto_compact: bool,
    ) -> str: ...


def serialize_graph(
    graph: SerializableGraph,
    *,
    context: dict[str, str | object],
    format_name: str,
    auto_compact: bool,
) -> str:
    return graph.serialize(
        format=format_name,
        indent=2,
        context=context,
        auto_compact=auto_compact,
    )


def fsm_metamodel() -> ScopeProviderRegistrar:
    mm = cast(
        ScopeProviderRegistrar,
        metamodel_from_file(
            GRAMMAR_PATH,
            classes=[
                State,
                Event,
                Transition,
                FiredEvent,
                Reaction,
                FSM,
            ],
        ),
    )
    mm.register_scope_providers(
        {
            "*.*": scoping_providers.FQNImportURI(),
        }
    )
    return mm


fsm_lang = LanguageDesc(
    name="coord_dsl_fsm",
    pattern="*.fsm",
    description="Finite State Machine DSL",
    metamodel=fsm_metamodel,
)


def graph_gen_console(
    metamodel: object,
    model: ModelWithFSM,
    output_path: str | None,
    overwrite: bool,
    debug: bool,
    **kwargs: object,
) -> None:
    del metamodel, output_path, overwrite, debug

    g, context, _ = get_fsm_graph(model)

    auto_compact = "autocompact" in kwargs
    format_name = kwargs.get("format", "json-ld")
    assert isinstance(format_name, str), "Graph format must be a string"
    if format_name not in __SUPPORTED_GRAPH_FORMATS:
        raise ValueError(
            f"Unsupported graph format '{format_name}', supported formats are: {__SUPPORTED_GRAPH_FORMATS}"
        )

    serialized = serialize_graph(
        g,
        context=context,
        format_name=format_name,
        auto_compact=auto_compact,
    )

    print(50 * "-")
    print(serialized)


def graph_gen_file(
    metamodel: object,
    model: ModelWithFSM,
    output_path: str | None,
    overwrite: bool,
    debug: bool,
    **kwargs: object,
) -> None:
    del metamodel, overwrite, debug

    g, context, _ = get_fsm_graph(model)

    auto_compact = "autocompact" in kwargs
    format_name = kwargs.get("format", "json-ld")
    assert isinstance(format_name, str), "Graph format must be a string"
    if format_name not in __SUPPORTED_GRAPH_FORMATS:
        raise ValueError(
            f"Unsupported graph format '{format_name}', supported formats are: {__SUPPORTED_GRAPH_FORMATS}"
        )

    serialized = serialize_graph(
        g,
        context=context,
        format_name=format_name,
        auto_compact=auto_compact,
    )

    if not output_path:
        model_path = Path(model._tx_filename).parent  # pyright: ignore[reportPrivateUsage]
        file_format = __SUPPORTED_GRAPH_FORMATS[format_name]
        output_path = f"{model_path}/{model.fsm.name}.{file_format}"

    with open(output_path, "w") as f:
        f.write(serialized)
    print(f"FSM graph generated at {output_path}")


def gen_cpp(
    metamodel: object,
    model: ModelWithFSM,
    output_path: str | None,
    overwrite: bool,
    debug: bool,
    **kwargs: object,
) -> None:
    del metamodel, overwrite, debug, kwargs

    g, _, fsm_ref = get_fsm_graph(model)

    ir = gen_json(g, fsm_ref)

    rendered = gen_cpp_header(ir)

    if not output_path:
        model_path = Path(model._tx_filename).parent  # pyright: ignore[reportPrivateUsage]
        output_path = f"{model_path}/{ir['name']}.hpp"

    with open(output_path, "w") as f:
        f.write(rendered)
    print(f"FSM C code generated at {output_path}")


def gen_python(
    metamodel: object,
    model: ModelWithFSM,
    output_path: str | None,
    overwrite: bool,
    debug: bool,
    **kwargs: object,
) -> None:
    del metamodel, overwrite, debug, kwargs

    g, _, fsm_ref = get_fsm_graph(model)

    ir = gen_json(g, fsm_ref)

    rendered = gen_python_code(ir)

    if not output_path:
        model_path = Path(model._tx_filename).parent  # pyright: ignore[reportPrivateUsage]
        output_path = f"{model_path}/{ir['name']}.py"

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
