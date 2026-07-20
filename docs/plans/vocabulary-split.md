# Plan: split the BT vocabulary into core / coordination / dialect

Status: **not started**

## Motivation

Every BT term the graph emits currently lives in one namespace:

```
bt: = https://secorolab.github.io/metamodels/behaviour/behaviour-tree#
```

That namespace mixes three unrelated authorities:

1. **Behaviour-tree theory** — `Sequence`, `Fallback`, `Parallel`, `Action`,
   `Condition`, the tick/status model.
2. **coord-dsl's own contribution** — FSM coordination (`send`/`await`/`on-fail`,
   `start-event`/`end-event`). This is the thesis, and it is currently
   indistinguishable from borrowed vocabulary.
3. **BehaviorTree.CPP's dialect** — guards (`_skipIf`/`_while`/`_onHalted`, its
   4.x scripting language), `autoremap`, the extra composites, the decorator
   catalogue.

Tier 3 outnumbers tier 1 roughly three to one. A reader of the graph cannot tell
which is which, and neither can a non-BT.CPP backend: the py_trees generator
rejects guards, `SKIPPED` and four composites, all tier 3, but nothing in the
vocabulary marks them as optional.

`df:` (dataflow / ports) is already a separate namespace. This plan applies the
same treatment to the rest.

## Non-goals

This is **provenance labelling, not a semantic layering**. Explicitly out of
scope, and previously considered and rejected:

- No "core subset must be independently executable" rule. Nothing consumes a
  filtered graph; every generator reads all of it. Execution is unchanged.
- No core supertypes for dialect classes (`btcpp:TryCatch` needs no
  `bt:Composite` parent).
- No `semantics-altering` flags on guards.
- No restructuring of `ReactiveSequence` into a `memory` property on
  `bt:Sequence`.
- No behavioural change of any kind. Generated XML, C++, Python and dot output
  must be byte-identical before and after, except where the model IRI itself is
  embedded.

If any of the above turns out to be wanted later, it is a separate plan.

## Target namespaces

| Prefix   | IRI                                                | Authority |
|----------|----------------------------------------------------|-----------|
| `bt:`    | `{URL_SECORO_MM}/behaviour/behaviour-tree#`         | BT theory |
| `coord:` | `{URL_SECORO_MM}/behaviour/coordination#`           | coord-dsl |
| `btcpp:` | `{URL_SECORO_MM}/behaviour/bt-cpp#`                 | BehaviorTree.CPP 4.x |
| `df:`    | `{URL_SECORO_MM}/behaviour/dataflow#`               | unchanged |
| `el:`    | `{URL_SECORO_MM}/behaviour/event_loop#`             | unchanged |

## Term assignment

Source of truth for the current set: `src/coord_dsl/generators/bt/graph.py`.

### `bt:` — core (unchanged IRI, reduced membership)

Classes: `BehaviourTree`, `Leaf`, `Action`, `Condition`, `SubTree`, `Sequence`,
`Fallback`, `Parallel`.

Properties: `root`, `has-child`, `child-index`, `of-behaviour`, `of-tree`,
`behaviour-tree-name`, `behaviour-name`, `instance-name`, `is-main`, `node-kind`.

### `coord:` — coord-dsl's coordination layer

Classes: `FSMEvent`, `FSMInstance`.

Properties: `of-fsm`, `on-fsm-instance`, `of-event`, `await-kind`,
`await-target`, `fail-kind`, `fail-target`, `start-event`, `end-event`.

### `btcpp:` — BehaviorTree.CPP dialect

Classes: `Decorator`, `SequenceWithMemory`, `ReactiveSequence`,
`ReactiveFallback`, `ParallelAll`, `IfThenElse`, `WhileDoElse`, `Switch`,
`TryCatch`.

Properties: `guard`, `guard-kind`, `guard-script`, `auto-remap`,
`decorator-kind`.

### Two terms needing a decision before implementing

1. **`bt:node-kind`** — a literal carrying the surface keyword, so a
   `reactive-sequence` node emits `bt:node-kind "reactive-sequence"` while its
   `rdf:type` moves to `btcpp:`. The predicate is core, some of its *values* are
   dialect. Options: (a) leave as-is, the split is on terms not values;
   (b) drop it, since `rdf:type` already encodes the kind and `xml.py:194` is
   its only real consumer. **Recommend (a)** — smallest diff, and `xml.py`
   depends on it.

2. **`bt:instance-name`** — used on core nodes *and* on `coord:FSMInstance`.
   Keep the single `bt:` term shared across namespaces rather than minting
   `coord:instance-name`; a shared generic property is normal RDF practice.

## Work items

### 1. `src/coord_dsl/generators/bt/graph.py`

- Add `URI_MM_COORD` and `URI_MM_BTCPP` beside the existing `URI_MM_*`
  constants (~line 39).
- In `get_bt_graph`, construct `NS_COORD` and `NS_BTCPP` alongside `NS_BT`
  (~line 97) and add both to the prefix-binding loop (~line 108) so they land in
  the JSON-LD `context` dict.
- Split `COMPOSITE_CLASS` (line 66) into the namespace each class belongs to —
  either two dicts, or one dict of `(namespace, localname)` pairs, so
  `visit()`'s `NS_BT[COMPOSITE_CLASS[node.type]]` (line 233) resolves correctly.
- Repoint the emit sites: guards (lines 204–207), `auto-remap` (line 244),
  `Decorator`/`decorator-kind` (239–240), the whole `FSMEventNode` branch
  (271–281), `FSMInstance` (144–147), `start-event`/`end-event` (288–291).

### 2. Consumers

Each reads the same IRIs it writes; repoint identically.

- `src/coord_dsl/generators/bt/xml.py` — guard reads (~line 140), `NS_BT[key]`
  for start/end events (line 190), `node-kind`, FSM event node handling.
- `src/coord_dsl/generators/bt/python.py` — `_guard_wrap` (~line 146), FSM
  event handling. Note this file *rejects* most `btcpp:` terms; once they are
  namespaced the rejection can be stated as "this backend does not implement the
  `btcpp:` vocabulary", which is a better error message than the current
  per-term list.
- `src/coord_dsl/generators/dot.py` — its own `NS_BT` at line 21 plus
  `_guard_lines` (line 127).
- `src/coord_dsl/generators/bt/registration.py` — `NS_BT` at line 43.

### 3. Tests

- `tests/test_bt_graph.py` defines its own `NS_BT` (line 27); add the two new
  namespaces and repoint assertions — guards (line 181), FSM instances/events
  (163–228), and the negative port-vocabulary check (488–493).
- `tests/test_dot.py`, `tests/test_provenance.py` — check for hardcoded IRIs.
- Add one test asserting the partition holds: for every triple in a generated
  graph, no `bt:` term appears in the dialect set and vice versa. This is the
  regression guard that keeps a future term from landing in the wrong namespace.

### 4. Docs

- `docs/concepts.rst` — a short section naming the three authorities and why
  they are separated. This is the point of the exercise; without it the split is
  invisible.
- `docs/pytrees_vs_btcpp.rst` — its gap list is now expressible as "py_trees
  implements `bt:` and `coord:`, not `btcpp:`". Rewrite the framing, keep the
  per-term reasoning.

## Verification

- `pytest` green.
- Regenerate `examples/models/bt/warehouse_pick/` for every target and diff
  against the pre-change output. Expect zero differences in XML, C++, Python and
  dot; the only changes are in the RDF/JSON-LD artifacts, where they should be
  confined to prefix/IRI changes on the terms listed above.
- Spot-check the JSON-LD `@context` contains `coord` and `btcpp`.

## Notes

- No committed `.ttl`/`.jsonld` fixtures exist in the repo (`git ls-files`
  confirms), so there is nothing to migrate — only `build/` output, which is
  regenerated.
- The IRIs are published metamodel URLs under `secorolab.github.io`. Splitting
  them here creates two IRIs that do not resolve until the metamodel repo
  publishes them. Decide whether that matters before merging; it does not affect
  generation.
