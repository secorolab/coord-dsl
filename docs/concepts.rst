Concepts
========

Who owns the loop?
------------------

The single most important idea in coord-dsl is **who owns the tick loop**. The
two languages answer it differently, and understanding that makes the
generated code obvious.

.. list-table::
   :header-rows: 1
   :widths: 26 37 37

   * -
     - FSM
     - BT
   * - Owns the tick loop
     - **you** (your control loop)
     - **the engine** (``tickWhileRunning``)
   * - Generated artifact is
     - passive data + a step function
     - a runtime contract + glue
   * - You write
     - the loop *and* the per-state behaviour
     - per-leaf callbacks
   * - Executes in
     - Python (``coord_dsl``) or C++ (coord2b)
     - Python (py_trees) or C++ (BehaviorTree.CPP)

An **FSM** header hands you ``create_fsm()``, the state/event enums, and
``fsm_step``. Nothing runs until *you* call them in a loop. You "define
behaviour" by writing the function that produces and consumes events.

.. note::

   The event loop only works with states that span at least **two** steps —
   work that completes within a single step should not get its own state (see
   `coord-dsl@5d983e2
   <https://github.com/secorolab/coord-dsl/commit/5d983e2011957c373ca829f538c3baaa79266308>`_).

A **BT** header hands you an abstract runtime class with one method per leaf.
You fill the callbacks; the engine owns the loop and calls them.

Coordinating FSMs from a BT
---------------------------

The ``send <fsm.EVENT> await <fsm.TARGET>`` node bridges the two models. It
generates a ``BT::StatefulActionNode`` that:

#. **dispatches** the command event to the FSM (``send``),
#. each tick **advances** the FSM and **checks** whether the awaited target was
   reached, returning ``RUNNING`` until then, then ``SUCCESS`` (``await``).

Because the node routes *dispatch / advance / poll* through overridable runtime
virtuals, the **same generated node** supports two execution models:

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Model
     - ``advance()``
     - Who steps the FSM
   * - **synchronous**
     - runs the controller + coord2b step
     - the BT tick (single thread)
   * - **asynchronous**
     - a no-op (overridden)
     - a self-driving controller, e.g. a 1 kHz thread; the BT only sends & polls

Await: edge vs level
--------------------

``await`` targets **either an event or a state** of the FSM:

* ``await <arm.PICK_DONE>`` — an **event** (edge-triggered). Succeeds on the
  tick the event fires. Literal, but transient.
* ``await <arm.PICKED>`` — a **state** (level-triggered). Succeeds when the FSM
  *is in* that state. Robust to timing, and the only mode that survives a thread
  boundary (an async controller may swap event buffers before the BT samples
  them, so async coordination should await states).

Failure
-------

An optional ``on-fail <fsm.TARGET>`` (event or state) maps an FSM fault to node
``FAILURE`` — independent of the scripted ``[failure-if: ...]`` guard. Use it
when the FSM itself can signal an error.

The RDF graph
-------------

Every model also has an RDF (JSON-LD) representation. It is the canonical,
tool-agnostic form; the XML and C++ backends are projections of it. For
``send/await`` in particular, the JSON-LD graph is the richest target — it
records the FSM instances, the dispatched event, and the await/fail targets and
their kinds.
