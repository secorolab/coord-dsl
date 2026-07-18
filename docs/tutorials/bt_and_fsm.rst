Tutorial: Coordinating FSMs with a Behaviour Tree
=================================================

Goal: use a behaviour tree to **coordinate** several FSMs — the BT dispatches
command events and waits for each FSM to finish. Two execution models are
shown: **synchronous** (the BT drives the FSMs) and **asynchronous** (each FSM
runs in its own 1 kHz thread; the BT only sends and polls).

Read :doc:`../concepts` first — the "who owns the loop?" section is the mental
model for everything below.

1. Model
--------

Declare the FSMs the tree coordinates with ``fsm <name> = "<file>.fsm"``, then
use ``send <fsm.EVENT> await <fsm.TARGET>`` nodes inside any composite.

.. literalinclude:: ../../examples/models/bt/arm_handover_fsms.btree
   :language: text
   :caption: examples/models/bt/arm_handover_fsms.btree

Each ``send/await`` dispatches a command event and blocks (``RUNNING``) until
the awaited target is reached. In a ``sequence`` the arms act one at a time; put
the same nodes under ``parallel-all`` and they run concurrently.

**Await target — event or state.** The ``await`` (and optional ``on-fail``)
target resolves to either an FSM *event* (edge-triggered) or an FSM *state*
(level-triggered):

.. literalinclude:: ../../examples/models/bt/async_pick.btree
   :language: text
   :caption: examples/models/bt/async_pick.btree — state await + on-fail

Here ``await <right_arm.PICKED>`` waits for a **state**, and
``on-fail <gripper.FAULT>`` maps the gripper's fault state to node ``FAILURE``.
The ``gripper`` FSM has an explicit fault branch:

.. literalinclude:: ../../examples/models/bt/gripper.fsm
   :language: text
   :caption: examples/models/bt/gripper.fsm
   :lines: 3-18

2. Generate
-----------

Generate the FSM headers **and** the BT header + XML (all C++):

.. code-block:: bash

   textx generate right_arm.fsm --target cpp -o right_arm.hpp
   textx generate gripper.fsm   --target cpp -o gripper.hpp
   textx generate async_pick.btree --target xml
   textx generate async_pick.btree --target cpp

The generated BT header now also **owns the FSM instances** and adds, per FSM,
a pure-virtual ``step_<fsm>(fsm_nbx*)`` — the one seam you implement — plus the
generic ``FSMEvent`` node and its registration. The resulting XML carries the
await/fail kinds:

.. code-block:: xml

   <FSMEvent fsm="gripper" event="GRASP" await="GRASPED" await_kind="state"
             on_fail="FAULT" on_fail_kind="state" />

.. _btfsm-sync:

3. Synchronous coordination (C++)
---------------------------------

Subclass the generated runtime and implement ``step_<fsm>`` — your controller
for that FSM: read its state, and produce the completion (``*_DONE``) events
when the sub-behaviour finishes. The BT node calls it each tick, then steps the
FSM. This is the default; you write nothing about the loop.

.. literalinclude:: ../../examples/models/bt/arm_handover_main.cpp
   :language: cpp
   :caption: examples/models/bt/arm_handover_main.cpp — the ``step_<fsm>`` seam
   :lines: 36-57

Register and tick as usual:

.. literalinclude:: ../../examples/models/bt/arm_handover_main.cpp
   :language: cpp
   :lines: 59-74

``arm_handover`` (a ``sequence``) drives ``right_arm`` then ``left_arm``;
``dual_arm`` (a ``parallel-all`` with ``retry`` and ``[failure-if]`` guards)
drives both at once — same node, different composite.

.. _btfsm-async:

4. Asynchronous coordination at 1 kHz (C++)
-------------------------------------------

For real hardware the FSM + controller usually runs in its own fixed-rate loop,
faster than the BT ticks. The generated node routes ``dispatch`` / ``advance``
/ ``current_state`` / ``event_present`` through **overridable virtuals**, so you
keep the same node and tree and just change the execution policy:

* run each FSM in its **own 1 kHz thread** that owns ``step`` +
  ``reconfig_event_buffers`` + ``fsm_step_nbx``,
* override ``advance()`` to a **no-op** (the thread advances the FSM),
* make ``dispatch()`` and ``current_state()`` **thread-safe** (a per-FSM mutex),
* **await states** (level-triggered) — an event edge cannot be sampled reliably
  across the thread boundary.

.. literalinclude:: ../../examples/models/bt/async_pick_main.cpp
   :language: cpp
   :caption: async_pick_main.cpp — execution-policy overrides
   :lines: 65-86

.. literalinclude:: ../../examples/models/bt/async_pick_main.cpp
   :language: cpp
   :caption: async_pick_main.cpp — the 1 kHz controller thread
   :lines: 107-128

Run both outcomes:

.. code-block:: bash

   cmake -S . -B build && cmake --build build --target async_pick_bt
   ./build/async_pick_bt            # -> SUCCESS
   ./build/async_pick_bt --fault    # gripper faults -> on-fail state -> FAILURE (exit 1)

The interleaved log shows the ``FSM`` state stream (each 1 kHz thread) next to
the ``BT`` node transitions: ``right_arm`` reaches ``Picked`` after ~60 ms of
real motion, the BT polls the state and advances, then the gripper runs — to
``Grasped`` (SUCCESS) or ``Fault`` (FAILURE).

Choosing a model
----------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * -
     - Synchronous
     - Asynchronous (1 kHz)
   * - FSM stepped by
     - the BT tick
     - a dedicated thread
   * - ``advance()``
     - default (steps the FSM)
     - overridden to no-op
   * - ``await``
     - event or state
     - state (level-triggered)
   * - Best for
     - tests, deterministic demos
     - real controllers at a fixed rate
