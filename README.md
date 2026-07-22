# coord-dsl

A [textX](https://textx.github.io/textX/) DSL for event-driven finite state
machines, with Python, C++, RDF, and graphviz generators.

## Installation

```bash
pip install -e .
```

## Model

The FSM design follows Prof. Herman Bruyninckx's
[Composable and Explainable Systems of Systems](https://robmosys.pages.gitlab.kuleuven.be/composable-and-explainable-systems-of-systems.pdf):
events represent observable changes, states represent stateful behaviours,
transitions connect states, and event reactions select transitions and may
produce further events. The generated machine is intended to run one step per
control-loop iteration; event production and consumption use the bundled event
loop.

FSM models use the `.fsm` extension. They declare states, events, transitions,
and ordered reactions. References to declarations are enclosed in angle
brackets.

```text
ns ex = "https://example.com/fsm/"

fsm (ns=ex) example_fsm {
    description: "Example FSM"
    states { S_START, S_RUNNING, S_EXIT }
    events { E_START, E_STOP }
    start: <S_START>
    end: <S_EXIT>
    transitions {
        T_START { from: <S_START>, to: <S_RUNNING> },
        T_STOP  { from: <S_RUNNING>, to: <S_EXIT> }
    }
    reactions {
        R_START { when: <E_START>, do: <T_START> },
        R_STOP  { when: <E_STOP>, do: <T_STOP> }
    }
}
```

Reactions are ordered: each step applies the first reaction whose event is
present and whose transition starts at the current state. A namespace gives
the FSM and each of its parts a stable URI.

## Generation

```bash
textx generate example.fsm --target cpp -o model.hpp
textx generate example.fsm --target python -o model.py
textx generate example.fsm --target graph --format json-ld --autocompact
textx generate example.fsm --target console --format ttl
textx generate example.fsm --target dot --format png
```

Available targets:

- `cpp`: C++ header for the [coord2b](https://github.com/rosym-project/coord2b) runtime.
- `python`: Python module for the bundled `coord_dsl` runtime.
- `graph` / `console`: RDF in JSON-LD, Turtle, or XML.
- `dot` / `dot-console`: graphviz source or a PNG, SVG, or PDF rendering.

Generated code includes `FSM_URI` and URI tables for states, events,
transitions, and reactions. File generators also update a
`provenance.ld.json` document beside their output.

See [examples/models/fsm](examples/models/fsm/) for a complete model and Python
and C++ controllers.
