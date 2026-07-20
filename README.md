# coord-dsl

Domain-Specific Languages (DSLs) for modelling the *coordination* of (robot)
behaviours, together with code generators that turn a model into runnable
artifacts.

Full documentation, including tutorials with runnable examples, lives at
**<https://secorolab.github.io/coord-dsl/>**.

## Languages

Both are [textX](https://textx.github.io/textX/) languages, and both execute
in **Python or C++**:

* **FSM** (`.fsm`) — *event-driven* finite state machines built from `states`,
  `events`, `transitions` and `reactions`, following the design in
  Prof. Herman Bruyninckx's
  [online book](https://robmosys.pages.gitlab.kuleuven.be/composable-and-explainable-systems-of-systems.pdf).
  An FSM is stepped from a control loop; event production and consumption are
  handled by a small event-loop runtime.
* **BT** (`.btree`) — behaviour trees built from composites, decorators,
  declared action/condition leaves, scripted guards (e.g. `[failure-if: ...]`,
  `[on-success: ...]`) and **FSM-coordination** nodes (`send`/`await`) that
  dispatch events to FSMs and wait for them to finish.

## Generation targets

Models are generated with `textx generate` — see the
[walkthrough](https://secorolab.github.io/coord-dsl/walkthrough.html) for the
exact commands.

| Language | Target | Artifact |
|---|---|---|
| FSM | `cpp` | Self-contained state machine + step function for the [coord2b](https://github.com/rosym-project/coord2b) runtime |
| FSM | `python` | The same, for the bundled `coord_dsl` runtime |
| FSM | `graph` / `console` | RDF graph (JSON-LD, Turtle or XML) |
| FSM | `dot` / `dot-console` | State-machine drawing (dot, png, svg, pdf) |
| BT | `xml` | [BehaviorTree.CPP](https://www.behaviortree.dev/) v4 tree structure |
| BT | `cpp` | Runtime contract + node registrations (BehaviorTree.CPP) |
| BT | `python` | [py_trees](https://py-trees.readthedocs.io/) tree + runtime contract |
| BT | `jsonld` | RDF graph — the canonical form |
| BT | `dot` / `dot-console` | Tree drawing (dot, png, svg, pdf) |

Alongside each artifact a generator writes a PROV-O `provenance.jsonld`
recording the source models, the artifact and the tool. Generated code also
carries the model's IRIs, so a running machine or tree can be joined back to its
graph — see
[Concepts](https://secorolab.github.io/coord-dsl/concepts.html).

The BT `python` target covers the coordination core; constructs without a
py_trees analogue are rejected at generation time rather than emulated, so trees
using them generate for `xml`/`cpp` only —
[the differences and why](https://secorolab.github.io/coord-dsl/pytrees_vs_btcpp.html).

## Installation

Install as a Python package with `pip install coord_dsl` (or `pip install -e .`
from a checkout). Executing generated **C++** additionally needs
[coord2b](https://github.com/rosym-project/coord2b) for FSMs and
[BehaviorTree.CPP](https://www.behaviortree.dev/) v4 for behaviour trees; the
Python runtimes ship with this package. Details:
[installation guide](https://secorolab.github.io/coord-dsl/installation.html).

## Examples

[`examples/models/fsm`](examples/models/fsm/) and
[`examples/models/bt`](examples/models/bt/) contain complete models with C++ and
Python demo programs — including trees that run identically in both languages
(`py_pick`, `arm_handover`, `dual_arm`, `async_pick`). Generated code is not
checked in; run `textx generate` first. The
[tutorials](https://secorolab.github.io/coord-dsl/tutorials/fsm.html) walk
through them step by step.
