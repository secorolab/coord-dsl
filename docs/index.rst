coord-dsl
=========

**coord-dsl** is a family of textX_ Domain-Specific Languages for modelling the
*coordination* of (robot) behaviours, together with code generators that turn a
model into runnable artifacts.

It ships two languages:

* **FSM** — event-driven finite state machines (``.fsm``). A state machine is
  stepped from a control loop; you write the per-state behaviour.
* **BT** — behaviour trees (``.btree``). A tree of composites, decorators and
  leaves, plus **FSM-coordination** nodes that dispatch events to FSMs and wait
  for them to finish.

From one model you generate:

.. list-table::
   :header-rows: 1
   :widths: 18 22 60

   * - Language
     - Target
     - Artifact
   * - FSM
     - ``cpp`` / ``python``
     - A self-contained state machine + step function (coord2b_ runtime)
   * - FSM
     - ``graph``
     - JSON-LD / Turtle / XML RDF graph
   * - BT
     - ``xml``
     - BehaviorTree.CPP_ v4 tree structure
   * - BT
     - ``cpp``
     - A runtime contract + node registrations (BehaviorTree.CPP)
   * - BT
     - ``python``
     - A py_trees_ tree + runtime contract
   * - BT
     - ``jsonld``
     - RDF graph (the canonical form; models ``send/await`` semantics)

.. note::

   Both languages execute in **Python or C++**. FSMs use the ``coord_dsl``
   runtime (Python) or coord2b_ (C++); behaviour trees use py_trees_ (Python) or
   BehaviorTree.CPP_ (C++). Each tutorial has separate **Python** and **C++**
   sections. See :doc:`concepts` for the shared execution model.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   installation
   concepts
   walkthrough
   tutorials/fsm
   tutorials/bt
   tutorials/bt_and_fsm
   pytrees_vs_btcpp

.. _textX: https://textx.github.io/textX/
.. _coord2b: https://github.com/rosym-project/coord2b
.. _BehaviorTree.CPP: https://www.behaviortree.dev/
.. _py_trees: https://py-trees.readthedocs.io/
