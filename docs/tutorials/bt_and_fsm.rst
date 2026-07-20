Tutorial: Coordinating FSMs with a Behaviour Tree
=================================================

This is where the two languages meet: a behaviour tree **coordinates** several
FSMs — it dispatches command events and waits for each FSM to reach a target.
The tutorial has a full **Python** section (py_trees_) and a full **C++** section
(BehaviorTree.CPP_ + coord2b_), including a **synchronous** and an
**asynchronous 1 kHz** execution model.

Read :doc:`../concepts` first — "who owns the loop?" is the model behind
everything here.

Modelling
---------

Declare the FSMs the tree coordinates with ``fsm <name> = "<file>.fsm"``, then
use ``send <fsm.EVENT> await <fsm.TARGET>`` nodes inside any composite. Each
node dispatches a command event and blocks (``RUNNING``) until its target is
reached; in a ``sequence`` the FSMs act in turn, under ``parallel-all`` they run
together.

.. literalinclude:: ../../examples/models/bt/arm_handover/arm_handover_fsms.btree
   :language: text
   :caption: arm_handover_fsms.btree — a sequence coordinating two arms

Await target: event or state
''''''''''''''''''''''''''''

The ``await`` target (and the optional ``on-fail`` target) resolves to **either**
an FSM *event* or an FSM *state*:

* ``await <arm.PICK_DONE>`` — an **event**, *edge-triggered*: succeeds on the
  tick the event fires. Literal, but transient — it must be sampled the moment
  the event is present.
* ``await <arm.PICKED>`` — a **state**, *level-triggered*: succeeds when the FSM
  *is in* that state. Robust to timing, and the only mode that survives a thread
  boundary (an asynchronous controller can swap event buffers before the tree
  samples them).

.. literalinclude:: ../../examples/models/bt/py_pick/py_pick.btree
   :language: text
   :caption: py_pick.btree — state await plus an on-fail target

``on-fail <gripper.FAULT>`` maps the gripper's fault state to node ``FAILURE``,
independently of any scripted ``[failure-if]`` guard. The gripper FSM has the
explicit fault branch:

.. literalinclude:: ../../examples/models/bt/fsms/gripper.fsm
   :language: text
   :caption: gripper.fsm

Generate
--------

Generate the FSM runtimes **and** the BT runtime, for whichever language.
Each example lives in its own directory under ``examples/models/bt``, with the
FSMs they share in ``fsms/``; generated code is **not** checked in, so run this
from the example's directory before building or running it:

.. code-block:: bash

   # Python (py_trees) — from examples/models/bt/py_pick
   textx generate ../fsms/right_arm.fsm --target python -o right_arm.py
   textx generate ../fsms/gripper.fsm   --target python -o gripper.py
   textx generate py_pick.btree --target python

   # C++ (BehaviorTree.CPP + coord2b) — from examples/models/bt/arm_handover
   textx generate ../fsms/right_arm.fsm --target cpp -o right_arm.hpp
   textx generate ../fsms/left_arm.fsm  --target cpp -o left_arm.hpp
   textx generate arm_handover_fsms.btree --target cpp
   textx generate arm_handover_fsms.btree --target xml

The generated BT runtime **owns the FSM instances** (creates them, resolves
event/state names to enum indices) and, per FSM, declares one hook —
``step_<fsm>`` — that you implement: your controller for that FSM.

The one seam: ``step_<fsm>``
'''''''''''''''''''''''''''''

A ``send/await`` node, each tick, calls ``advance()`` which runs your
``step_<fsm>`` and then steps the FSM, and checks the await/fail target. Your
``step_<fsm>`` is exactly the FSM controller: read the FSM's state and produce
the completion (``*_DONE``) events when a sub-behaviour finishes. Everything
else — dispatch, name resolution, the coord2b/``coord_dsl`` step — is generated.

Running in Python
-----------------

Subclass the generated runtime, implement each ``step_<fsm>``, build the tree,
and tick it. The controller below completes a motion after a few ticks by
producing the FSM's completion event:

.. literalinclude:: ../../examples/models/bt/py_pick/py_pick_demo.py
   :language: python
   :caption: py_pick_demo.py — controllers + tick loop
   :lines: 26-63

.. code-block:: bash

   python py_pick_demo.py            # -> SUCCESS
   python py_pick_demo.py --fault    # gripper faults -> on-fail state -> FAILURE

``right_arm`` runs to its ``PICKED`` state, the tree advances, then the gripper
runs — to ``GRASPED`` (SUCCESS) or ``FAULT`` (FAILURE via ``on-fail``).

``arm_handover`` and ``dual_arm`` ship the same shape — a runtime subclass plus
a tick loop — in ``arm_handover_demo.py`` and ``dual_arm_demo.py``. Their
``[on-success]``/``[on-failure]``/``[failure-if]`` guards translate to a
generated ``_Guarded`` decorator over the py_trees blackboard (see :doc:`bt`),
so the fault path is driven by setting a blackboard flag:

.. code-block:: bash

   python arm_handover_demo.py                # right_arm picks and hands over, left_arm places
   python dual_arm_demo.py                    # both arms in parallel -> SUCCESS
   python dual_arm_demo.py --fault left       # left branch fails its retries -> FAILURE

Running in C++ (synchronous)
----------------------------

Same shape in C++: subclass the runtime, implement ``step_<fsm>``, register and
tick. Here the BT tick drives each FSM directly.

.. literalinclude:: ../../examples/models/bt/arm_handover/arm_handover_main.cpp
   :language: cpp
   :caption: arm_handover_main.cpp — the step_<fsm> seam
   :lines: 36-57

``arm_handover`` (a ``sequence``) drives ``right_arm`` then ``left_arm``;
``dual_arm`` (a ``parallel-all`` with ``retry`` decorators and ``[failure-if]``
guards) drives both at once — the same node, a different composite.

.. code-block:: bash

   cmake -S . -B build && cmake --build build --target arm_handover_bt dual_arm_bt
   ./build/arm_handover_bt        # sequential
   ./build/dual_arm_bt            # parallel

.. _btfsm-async:

Running in C++ (asynchronous, 1 kHz)
------------------------------------

On real hardware an FSM controller usually runs in its own fixed-rate loop,
faster than the tree ticks. The generated node routes ``dispatch`` /
``advance`` / ``current_state`` / ``event_present`` through **overridable
virtuals**, so you keep the same node and tree and only change the execution
policy:

* run each FSM in its **own 1 kHz thread** that owns ``step`` +
  ``reconfig_event_buffers`` + ``fsm_step_nbx``;
* override ``advance()`` to a **no-op** (the thread advances the FSM);
* make ``dispatch()`` and ``current_state()`` **thread-safe** (a per-FSM mutex);
* **await states**, not events (an event edge can't be sampled across the thread
  boundary).

.. literalinclude:: ../../examples/models/bt/async_pick/async_pick_main.cpp
   :language: cpp
   :caption: async_pick_main.cpp — execution-policy overrides
   :lines: 65-86

.. literalinclude:: ../../examples/models/bt/async_pick/async_pick_main.cpp
   :language: cpp
   :caption: async_pick_main.cpp — the 1 kHz controller thread
   :lines: 107-128

.. code-block:: bash

   cmake --build build --target async_pick_bt
   ./build/async_pick_bt            # -> SUCCESS
   ./build/async_pick_bt --fault    # gripper faults -> FAILURE (exit 1)

The interleaved log shows the ``FSM`` state stream (each 1 kHz thread) beside the
``BT`` node transitions: ``right_arm`` reaches ``Picked`` after ~60 ms of real
motion, the tree polls the state and advances, then the gripper runs.

The same override seam works in Python — ``async_pick_demo.py`` is the direct
counterpart: one ``threading.Thread`` per FSM at 1 kHz, ``advance`` overridden
to a no-op, and ``dispatch`` / ``current_state`` / ``event_present`` taking the
controller's lock.

.. literalinclude:: ../../examples/models/bt/async_pick/async_pick_demo.py
   :language: python
   :caption: async_pick_demo.py — execution-policy overrides and the 1 kHz loop
   :lines: 72-118

.. code-block:: bash

   python async_pick_demo.py            # -> SUCCESS
   python async_pick_demo.py --fault    # gripper faults -> FAILURE (exit 1)

Choosing a model
----------------

.. list-table::
   :header-rows: 1
   :widths: 28 24 24 24

   * -
     - Python (sync)
     - C++ (sync)
     - C++ (1 kHz async)
   * - FSM stepped by
     - the tick
     - the tick
     - a dedicated thread
   * - ``advance()``
     - default
     - default
     - overridden to no-op
   * - ``await``
     - event or state
     - event or state
     - state (level-triggered)
   * - Best for
     - Python stacks, prototyping
     - deterministic demos, tests
     - real controllers at a fixed rate

.. _coord2b: https://github.com/rosym-project/coord2b
.. _BehaviorTree.CPP: https://www.behaviortree.dev/
.. _py_trees: https://py-trees.readthedocs.io/
