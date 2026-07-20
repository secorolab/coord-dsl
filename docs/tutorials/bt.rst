Tutorial: Behaviour Tree
========================

A behaviour tree composes leaf behaviours with composites and decorators into a
reactive control policy. This tutorial models one, generates it, and runs it —
with a full **C++** section (BehaviorTree.CPP_) and a full **Python** section
(py_trees_).

Modelling
---------

A ``.btree`` first **declares the leaf behaviours** it uses — ``action`` or
``condition`` nodes with typed ports (``in`` / ``out`` / ``inout``) — then builds
the tree from those leaves, composites, decorators and sub-trees.

Declare leaves one per line with ``node action foo``, or group them in a
``nodes { … }`` block. The two forms are equivalent and can be mixed in one
file, as below.

.. literalinclude:: ../../examples/models/bt/warehouse_pick/fetch_and_place.btree
   :language: text
   :caption: examples/models/bt/warehouse_pick/fetch_and_place.btree (excerpt)
   :lines: 1-51

The vocabulary maps onto BehaviorTree.CPP v4 constructs:

* **Composites** — ``sequence``, ``sequence-with-memory``, ``reactive-sequence``,
  ``fallback`` / ``selector``, ``reactive-fallback``, ``parallel``,
  ``parallel-all``, ``if-then-else``, ``while-do-else``, ``switch``,
  ``try-catch``.
* **Decorators** — ``inverter``, ``retry``, ``timeout``, ``repeat``, ``run-once``,
  ``force-success`` / ``force-failure``, ``keep-running``, ``delay``,
  ``precondition``, ``loop`` …
* **Ports** — bound to a blackboard key ``{key}``, a literal, or a quantity with
  units (``0.5 m/s``, ``5000 ms``).
* **Sub-trees** — ``subtree <t> as inst (port: {key})``. Keys the caller does
  not bind are private to the instance; add ``autoremap`` after the instance
  name (BT.CPP's ``_autoremap``) to share the caller's keys by name instead.
* **Guards** — scripted pre/post conditions on any node:
  ``[skip-if: ...]``, ``[failure-if: ...]``, ``[while: ...]``,
  ``[on-success: ...]`` and friends.

Generate
--------

.. code-block:: bash

   textx generate fetch_and_place.btree --target xml     # structure (.xml)
   textx generate fetch_and_place.btree --target cpp     # C++ runtime contract (.hpp)
   textx generate fetch_and_place.btree --target jsonld  # RDF graph (.json)
   textx generate fetch_and_place.btree --target dot --format png   # a picture of the tree

This model is a BT.CPP **vocabulary showcase**, so ``--target python`` rejects
it: it uses ``switch``, ``if-then-else``, ``while-do-else`` and the scripting
builtins, none of which have py_trees equivalents (see
:doc:`../pytrees_vs_btcpp`). Its sub-trees are fine — those the ``python``
target expands per instance. The FSM-coordination trees in :doc:`bt_and_fsm`
generate for both runtimes.

The tree **structure** is emitted differently per runtime: BehaviorTree.CPP loads
an ``.xml`` at run time, while py_trees builds the tree in Python code
(``create_tree``). Both targets also emit a **runtime contract** — an abstract
class with one hook per declared leaf.

Model IRIs in the generated code
''''''''''''''''''''''''''''''''

Both runtimes carry the model's IRIs, as the FSM targets do
(:ref:`fsm-iri-tables`), so a running tree can be joined back to the RDF graph:

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - Symbol
     - Names
   * - ``TREE_URIS``
     - every behaviour tree, main tree first
   * - ``NODE_URIS``
     - every node, in model order, with its kind
   * - ``BEHAVIOUR_URIS``
     - every declared ``action`` / ``condition``
   * - ``FSM_URIS``
     - the FSM each declared instance runs (joins to that FSM's ``FSM_URI``)

Those tables say what *exists*. To identify the node that is **ticking** — names
repeat, so ``holding`` alone is ambiguous — each node also carries its own IRI:

.. code-block:: python

   def on_holding(self, node):
       print(node.model_uri)     # .../warehouse_pick-root-5-0

.. code-block:: cpp

   BT::NodeStatus on_holding(BT::TreeNode& node) override {
     std::cout << warehouse_pick::model_uri(node);   // same IRI
   }

Naming a node makes its IRI stable
``````````````````````````````````

A node's IRI is its **position** in the tree — ``…-root-1-0`` — so inserting a
sibling above it renumbers it and everything after it. That is fine for joining a
run to the model that ran (an archived run carries its own source), but it means
an IRI is not a durable key across edits.

Naming a node with ``as`` makes it one: the name replaces the index, so the IRI
survives reordering.

.. code-block:: text

   subtree <perceive> as find (target: {target_object})   # .../warehouse_pick-root-find
   holding (object: {target_object})                      # .../warehouse_pick-root-5-0

Names only have to be unique **among siblings** — the parent's IRI scopes them —
and two siblings sharing one is an error, since the name is the node's identity.
Name the nodes you intend to reference from outside the model; leave the rest
positional.

In C++ the IRI travels as a ``model_uri`` port, so it is available on generated
leaves and ``send``/``await`` nodes; BehaviorTree.CPP's own composites and
decorators carry none, since it rejects any attribute a node type does not
declare. ``model_uri`` is therefore a **reserved port name** — declaring a port
with it is an error. In Python every node carries the attribute, sub-trees
included.

Running in C++
--------------

The ``cpp`` target produces a header with:

* an abstract ``…Runtime`` class — one pure-virtual ``on_<behaviour>`` per leaf,
* ``register_nodes(factory, runtime)`` — wires each leaf to its hook,
* ``create_tree(factory, xml_path, blackboard)`` — loads the ``.xml``.

Subclass the runtime, implement each leaf (read ports, return a ``NodeStatus``),
register, load, and tick. The engine owns the loop:

.. literalinclude:: ../../examples/models/bt/warehouse_pick/warehouse_pick_main.cpp
   :language: cpp
   :caption: warehouse_pick_main.cpp — a leaf implementation
   :lines: 48-56

.. literalinclude:: ../../examples/models/bt/warehouse_pick/warehouse_pick_main.cpp
   :language: cpp
   :caption: warehouse_pick_main.cpp — register, load, tick
   :lines: 137-163

Because ``create_tree`` loads the ``.xml`` at run time, ship it next to the
binary (the example ``CMakeLists.txt`` copies it into the build directory):

.. code-block:: bash

   cmake -S . -B build && cmake --build build --target warehouse_pick_bt
   ./build/warehouse_pick_bt

Running in Python
-----------------

The ``python`` target produces a py_trees_ module with the same shape:

* a ``…Runtime`` class — one ``on_<behaviour>`` hook per leaf (return a
  ``py_trees.common.Status``),
* ``create_tree(runtime)`` — builds and returns the tree's root ``Behaviour``.

Subclass the runtime, implement the leaves, build the tree, and tick it with
py_trees' own machinery:

.. code-block:: python

   import py_trees
   from fetch_and_place import FetchAndPlaceRuntime, create_tree

   class Runtime(FetchAndPlaceRuntime):
       def on_move_to(self, node) -> py_trees.common.Status:
           goal = node.ports["goal"]           # ports are resolved onto the node
           ...
           return py_trees.common.Status.SUCCESS

   root = create_tree(Runtime())
   root.tick_once()                             # or py_trees.trees.BehaviourTree(root)

Construct mapping and limitations
'''''''''''''''''''''''''''''''''

The Python target covers the coordination core; the C++/XML backend remains the
complete one. Mappings:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - coord-dsl
     - py_trees
   * - ``sequence`` / ``sequence-with-memory``
     - ``Sequence(memory=True)``
   * - ``reactive-sequence``
     - ``Sequence(memory=False)``
   * - ``fallback`` / ``selector``
     - ``Selector(memory=True)``
   * - ``reactive-fallback``
     - ``Selector(memory=False)``
   * - ``parallel`` / ``parallel-all``
     - ``Parallel(SuccessOnOne / SuccessOnAll)``
   * - ``inverter`` / ``force-success`` / ``force-failure``
     - ``Inverter`` / ``FailureIsSuccess`` / ``SuccessIsFailure``
   * - ``keep-running`` / ``run-once``
     - ``SuccessIsRunning`` / ``OneShot``
   * - ``retry`` / ``repeat`` / ``timeout``
     - ``Retry`` / ``Repeat`` / ``Timeout``
   * - ``subtree`` (with or without ``autoremap``)
     - expanded per instance, keys resolved at generation time
   * - ``send/await`` (FSM coordination)
     - a generated ``_FSMEvent`` behaviour — see :doc:`bt_and_fsm`
   * - ``[failure-if]`` / ``[success-if]`` / ``[on-success]`` / ``[on-failure]`` / ``[post]``
     - a generated ``_Guarded`` decorator; scripts are translated to
       blackboard expressions at generation time

.. note::

   Constructs without a clean py_trees analogue — ``[skip-if]`` / ``[while]``
   / ``[on-halted]`` guards, ``if-then-else`` / ``while-do-else`` /
   ``switch`` / ``try-catch``, ``delay`` / ``loop`` / ``precondition``, and
   scripted builtins — raise ``NotImplementedError`` at generation time. The supported guard
   subset and the reasoning behind each gap are in
   :ref:`pytrees-vs-btcpp`.

Relationship to py_trees' XML parser
''''''''''''''''''''''''''''''''''''

The ``python`` target emits **bespoke** py_trees code and passes leaf ports as a
plain dict — it is *not* a faithful projection of the ``xml`` target, and the
composite mappings above are approximations.

py_trees ships an *experimental* BehaviorTree.CPP-compatible XML parser
(``py_trees.parsers.behaviour_tree_xml``) that could, in principle, load the very
``.xml`` we already generate and wire ports to the blackboard via its typed
`ports <https://py-trees.readthedocs.io/en/devel/ports.html>`_ system —
collapsing Python and C++ onto one structural artifact. That is the intended
convergence path, but it is not adopted here yet because:

* the parser is marked experimental, and py_trees' public ports API is not in a
  stable release;
* the custom ``FSMEvent`` and ``_Guarded`` nodes and FSM instances would need
  registering with the parser's node registry.

Until those settle, treat the Python target as a subset; the C++/XML backend
remains the complete one.

.. _BehaviorTree.CPP: https://www.behaviortree.dev/
.. _py_trees: https://py-trees.readthedocs.io/
