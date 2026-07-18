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

.. literalinclude:: ../../examples/models/bt/fetch_and_place.btree
   :language: text
   :caption: examples/models/bt/fetch_and_place.btree (excerpt)
   :lines: 1-48

The vocabulary maps onto BehaviorTree.CPP v4 constructs:

* **Composites** — ``sequence``, ``sequence-with-memory``, ``reactive-sequence``,
  ``fallback`` / ``selector``, ``reactive-fallback``, ``parallel``,
  ``parallel-all``, ``if-then-else``, ``while-do-else``, ``switch``.
* **Decorators** — ``inverter``, ``retry``, ``timeout``, ``repeat``, ``run-once``,
  ``force-success`` / ``force-failure``, ``keep-running``, ``delay``,
  ``precondition``, ``loop`` …
* **Ports** — bound to a blackboard key ``{key}``, a literal, or a quantity with
  units (``0.5 m/s``, ``5000 ms``).
* **Guards** — scripted pre/post conditions on any node:
  ``[skip-if: ...]``, ``[failure-if: ...]``, ``[while: ...]``,
  ``[on-success: ...]`` and friends.

Generate
--------

.. code-block:: bash

   textx generate fetch_and_place.btree --target xml     # structure (.xml)
   textx generate fetch_and_place.btree --target cpp     # C++ runtime contract (.hpp)
   textx generate fetch_and_place.btree --target python  # py_trees module (.py)
   textx generate fetch_and_place.btree --target jsonld  # RDF graph (.json)

The tree **structure** is emitted differently per runtime: BehaviorTree.CPP loads
an ``.xml`` at run time, while py_trees builds the tree in Python code
(``create_tree``). Both targets also emit a **runtime contract** — an abstract
class with one hook per declared leaf.

Running in C++
--------------

The ``cpp`` target produces a header with:

* an abstract ``…Runtime`` class — one pure-virtual ``on_<behaviour>`` per leaf,
* ``register_nodes(factory, runtime)`` — wires each leaf to its hook,
* ``create_tree(factory, xml_path, blackboard)`` — loads the ``.xml``.

Subclass the runtime, implement each leaf (read ports, return a ``NodeStatus``),
register, load, and tick. The engine owns the loop:

.. literalinclude:: ../../examples/models/bt/warehouse_pick_main.cpp
   :language: cpp
   :caption: warehouse_pick_main.cpp — a leaf implementation
   :lines: 48-56

.. literalinclude:: ../../examples/models/bt/warehouse_pick_main.cpp
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
   * - ``send/await`` (FSM coordination)
     - a generated ``_FSMEvent`` behaviour — see :doc:`bt_and_fsm`
   * - ``[failure-if]`` / ``[success-if]`` / ``[on-success]`` / ``[on-failure]`` / ``[post]``
     - a generated ``_Guarded`` decorator; scripts are translated to
       blackboard expressions at generation time

.. note::

   Constructs without a clean py_trees analogue — ``[skip-if]`` / ``[while]``
   / ``[on-halted]`` guards, ``if-then-else`` / ``while-do-else`` /
   ``switch``, ``delay`` / ``loop`` / ``precondition``, and scripted builtins
   — raise ``NotImplementedError`` at generation time. The supported guard
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

.. _pytrees-vs-btcpp:

py_trees vs BehaviorTree.CPP: the semantic gaps
-----------------------------------------------

The two engines differ in more than how the tree is delivered (run-time XML vs
Python code). This section lists the semantic differences, which ones the
``python`` target bridges, and which it deliberately does not.

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * -
     - BehaviorTree.CPP v4
     - py_trees
   * - Node status
     - ``SUCCESS`` / ``FAILURE`` / ``RUNNING`` / **SKIPPED** / ``IDLE``
     - ``SUCCESS`` / ``FAILURE`` / ``RUNNING`` / ``INVALID``
   * - Guards
     - pre/post conditions on **every** node (``_skipIf``, ``_while``,
       ``_onSuccess``, …) with a built-in scripting language
     - none built in
   * - Blackboard
     - shared store; script variables are created on assignment, reading an
       **unset** variable is a run-time error
     - typed client/registry API plus a raw ``Blackboard`` store; no scripting
   * - Halting
     - explicit ``halt()`` with the ``_onHalted`` scripted hook
     - invalidation via ``stop(INVALID)``; no scripted hook
   * - Control-flow composites
     - ``IfThenElse``, ``WhileDoElse``, ``Switch<N>``
     - none (selectors/sequences only)

Bridged by the ``python`` target
''''''''''''''''''''''''''''''''

* **Guards** — ``[failure-if]`` / ``[success-if]`` / ``[on-success]`` /
  ``[on-failure]`` / ``[post]`` compile into a generated ``_Guarded``
  decorator. Timing matches BT.CPP: preconditions are evaluated only when the
  child is not ``RUNNING`` (entry/re-entry) and, when true, return their
  status without ticking the child; completion scripts run exactly once when
  the child returns ``SUCCESS`` or ``FAILURE``.
* **Guard scripts** — translated to Python **at generation time** (no run-time
  interpreter): literals, blackboard variables, comparisons, arithmetic,
  ``&&`` / ``||``, and a single ``key := expr`` assignment for completion
  scripts. Anything outside that subset fails the build, not the run.
* **Unset blackboard reads** — where BT.CPP raises at run time (forcing C++
  mains to pre-seed flags like ``left_arm_fault := false``), the generated
  ``_bb_get`` returns ``None``, so ``flag == true`` is simply false until
  something sets ``flag``. Same observable behaviour, no seeding required.

Not bridged (and why)
'''''''''''''''''''''

* ``[skip-if]`` and ``[while]`` — both produce ``SKIPPED``, a status py_trees
  does not have. A skipped child is *transparent* to its parent composite
  (a sequence continues past it); mapping it onto ``SUCCESS`` or ``FAILURE``
  would silently change the tree's semantics, so it is rejected instead.
* ``[on-halted]`` — py_trees invalidation (``stop(INVALID)``) is not the same
  event as a BT.CPP ``halt()`` of a running node; wiring the script to the
  wrong one would fire it spuriously. Deferred until a use case pins the
  semantics down.
* ``if-then-else`` / ``while-do-else`` / ``switch`` — no py_trees composite
  has these semantics; emulating them from selectors changes tick behaviour.
* ``script`` / ``set_blackboard`` builtins and the full BT.CPP scripting
  language (multiple ``;``-separated statements, string concatenation, …).
* ``delay`` / ``loop`` / ``precondition`` decorators.

All of these raise ``NotImplementedError`` at **generation** time, so an
unsupported model never produces a silently-different Python tree — use the
C++/XML backend for those.

.. _BehaviorTree.CPP: https://www.behaviortree.dev/
.. _py_trees: https://py-trees.readthedocs.io/
