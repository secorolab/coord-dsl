Tutorial: Behaviour Tree
========================

Goal: model a behaviour tree, generate its structure and runtime contract, and
run it in **C++**.

.. note::

   Behaviour trees **execute in C++** (BehaviorTree.CPP_). The *Python* side is
   authoring the model and running the generators — there is no Python BT
   runtime. If you want Python execution of coordination logic, use an
   :doc:`FSM <fsm>`.

1. Model
--------

A ``.btree`` declares the **leaf behaviours** it uses (actions and conditions,
with typed ports) and then the tree itself from composites, decorators and
leaves. This example (abridged) shows the vocabulary:

.. literalinclude:: ../../examples/models/bt/fetch_and_place.btree
   :language: text
   :caption: examples/models/bt/fetch_and_place.btree
   :lines: 1-48

Composites (``sequence``, ``fallback``, ``parallel``, ``if-then-else`` …),
decorators (``retry``, ``timeout``, ``repeat`` …), sub-trees, and per-node
guards (``[while: ...]``, ``[failure-if: ...]``, ``[on-success: ...]``) all map
onto BehaviorTree.CPP v4 constructs.

.. _bt-python:

2. Generate (the Python/CLI side)
---------------------------------

.. code-block:: bash

   textx generate fetch_and_place.btree --target xml    # -> tree structure (.xml)
   textx generate fetch_and_place.btree --target cpp    # -> runtime contract (.hpp)
   textx generate fetch_and_place.btree --target jsonld # -> RDF graph (.json)

* ``xml`` is the BehaviorTree.CPP tree that the engine loads.
* ``cpp`` is a header with an **abstract runtime class** — one pure-virtual
  ``on_<behaviour>`` per declared leaf — plus ``register_nodes()`` and
  ``create_tree()``.

.. _bt-cpp:

3. Run it in C++
----------------

Subclass the generated runtime, implement each leaf, register, load the tree,
and tick. The engine owns the loop.

.. literalinclude:: ../../examples/models/bt/warehouse_pick_main.cpp
   :language: cpp
   :caption: examples/models/bt/warehouse_pick_main.cpp (main)
   :lines: 137-163

Each ``on_<behaviour>`` reads its ports and returns ``SUCCESS`` / ``FAILURE``
(or ``RUNNING`` for stateful leaves):

.. literalinclude:: ../../examples/models/bt/warehouse_pick_main.cpp
   :language: cpp
   :caption: A leaf implementation
   :lines: 48-56

Build against BehaviorTree.CPP:

.. code-block:: bash

   cmake -S . -B build && cmake --build build --target warehouse_pick_bt
   ./build/warehouse_pick_bt

The generated ``create_tree`` loads the ``.xml`` at runtime, so ship the XML
next to the binary (the example ``CMakeLists.txt`` copies it into the build
directory).

.. _BehaviorTree.CPP: https://www.behaviortree.dev/
