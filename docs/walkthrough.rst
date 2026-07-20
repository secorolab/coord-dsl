Walkthrough: coordinate two FSMs with a behaviour tree
======================================================

A hands-on, end-to-end build. We model a small pick task, generate it, write the
controllers, and **run it** — first in Python, then in C++ — watching the same
coordination play out both ways.

**What we build.** A robot picks an object in two steps: an *arm* moves in and
picks, then a *gripper* grasps. Each step is a small FSM. A behaviour tree
**sequences** them — start the arm, wait until it has picked, then start the
gripper and wait until it has grasped. The gripper can also **fault**, and we
want that to fail the task cleanly.

By the end you will have run this and understood every moving part:

.. code-block:: text

   sequence
   ├── send PICK to right_arm,  await state PICKED
   └── send GRASP to gripper,   await state GRASPED   (on fault -> FAILURE)

Prerequisites
-------------

.. code-block:: bash

   pip install -e .            # the coord-dsl CLI and generators
   pip install py_trees        # to run the Python version
   mkdir pick && cd pick       # a scratch directory to work in

For the C++ version you also need coord2b_ and BehaviorTree.CPP_ (see
:doc:`installation`). Everything below uses files that ship in
``examples/models/bt`` — copy them into your scratch directory, or edit along.

Step 1 — model the arm FSM
--------------------------

The arm's lifecycle: it sits ``IDLE``; a ``PICK`` command moves it to
``PICKING``; when the motion finishes (a ``PICK_DONE`` event) it reaches
``PICKED``. (It has two more states for a later handover; ignore them here.)

.. literalinclude:: ../examples/models/bt/fsms/right_arm.fsm
   :language: text
   :caption: right_arm.fsm

Read the ``reactions`` as the policy: *when* ``PICK`` fires, *do* the
``PICK_OBJECT`` transition (``IDLE`` → ``PICKING``); *when* ``PICK_DONE`` fires,
*do* ``FINISH_PICK`` (``PICKING`` → ``PICKED``). The command event (``PICK``)
comes from outside; the completion event (``PICK_DONE``) comes from the arm's
own controller when the motion is done.

Step 2 — model the gripper FSM (with a fault)
---------------------------------------------

Same shape, but ``GRASPING`` has **two** exits — success (``GRASPED_OK`` →
``GRASPED``) or fault (``GRASP_FAULT`` → ``FAULT``):

.. literalinclude:: ../examples/models/bt/fsms/gripper.fsm
   :language: text
   :caption: gripper.fsm

Because reactions are ordered and both start from ``GRASPING``, whichever event
the controller produces decides the branch.

Step 3 — model the coordinating tree
------------------------------------

Now the behaviour tree. Import the two FSMs, then a ``sequence`` of two
``send/await`` nodes:

.. literalinclude:: ../examples/models/bt/py_pick/py_pick.btree
   :language: text
   :caption: py_pick.btree

Two things to notice:

* We ``await`` a **state** (``PICKED``, ``GRASPED``), not an event. State await is
  *level-triggered* — it succeeds when the FSM *is in* that state, which is robust
  to timing (see :doc:`concepts`).
* ``on-fail <gripper.FAULT>`` maps the gripper's fault state to node ``FAILURE``.

That is the whole model. Now we run it — pick a track.

----

Track A — run it in Python (py_trees)
-------------------------------------

**A1. Generate.** One command per FSM (to a Python module) and one for the tree:

.. code-block:: console

   $ textx generate right_arm.fsm --target python -o right_arm.py
   FSM Python code generated at right_arm.py
   $ textx generate gripper.fsm   --target python -o gripper.py
   FSM Python code generated at gripper.py
   $ textx generate py_pick.btree --target python
   BT Python module generated at py_pick.py

**A2. Look at what was generated.** ``py_pick.py`` contains a runtime class and a
tree builder. The tree is literal py_trees code:

.. code-block:: python

   def create_tree(runtime) -> py_trees.behaviour.Behaviour:
       return py_trees.composites.Sequence(
           name='sequence', memory=True,
           children=[
               _FSMEvent('right_arm.PICK', runtime, 'right_arm', 'PICK', 'PICKED', 'state'),
               _FSMEvent('gripper.GRASP', runtime, 'gripper', 'GRASP', 'GRASPED', 'state',
                         on_fail='FAULT', on_fail_kind='state'),
           ],
       )

The ``PyPickRuntime`` class owns the two FSM instances and declares the **only
hooks you implement** — one per FSM:

.. code-block:: python

   class PyPickRuntime:
       def step_right_arm(self, fsm): ...   # your arm controller
       def step_gripper(self, fsm): ...     # your gripper controller

**A3. Write the controllers.** A controller reads the FSM's state and, when a
motion is "done", produces the completion event. Here each motion "runs" for a
few ticks, then completes:

.. literalinclude:: ../examples/models/bt/py_pick/py_pick_demo.py
   :language: python
   :caption: py_pick_demo.py
   :lines: 26-63

**A4. Run it.**

.. code-block:: console

   $ python py_pick_demo.py
   === py_pick: py_trees coordinating FSMs ===
     right_arm: finished, produced completion event
     gripper: finished, produced completion event
   === py_pick: SUCCESS ===

Now make the gripper fault — the tree fails, as designed:

.. code-block:: console

   $ python py_pick_demo.py --fault
   === py_pick: py_trees coordinating FSMs  (gripper will FAULT) ===
     right_arm: finished, produced completion event
     gripper: finished, produced completion event
   === py_pick: FAILURE ===

**What just happened.** The ``_FSMEvent`` for the arm dispatched ``PICK``, then
each tick called ``step_right_arm`` and stepped the FSM: ``IDLE`` → ``PICKING``,
and after three ticks your controller produced ``PICK_DONE`` → ``PICKED``. The
node was awaiting the ``PICKED`` *state*, so it returned ``SUCCESS`` and the
sequence moved to the gripper. With ``--fault`` the gripper produced
``GRASP_FAULT`` → ``FAULT``; the node's ``on-fail`` matched that state and
returned ``FAILURE``, failing the sequence.

----

Track B — run it in C++ (BehaviorTree.CPP + coord2b)
----------------------------------------------------

The same model, the same controllers — a different runtime.

**B1. Generate** the FSM headers, the BT header, and the tree XML:

.. code-block:: console

   $ textx generate right_arm.fsm --target cpp -o right_arm.hpp
   $ textx generate gripper.fsm   --target cpp -o gripper.hpp
   $ textx generate py_pick.btree --target cpp    # -> py_pick.hpp
   $ textx generate py_pick.btree --target xml    # -> py_pick.xml

**B2. Look at the header.** ``py_pick.hpp`` declares the same seam — one
``step_<fsm>`` per FSM — plus a generic ``FSMEvent`` node and ``register_nodes`` /
``create_tree``:

.. code-block:: cpp

   class PyPickRuntime {
    public:
     virtual void step_right_arm(struct fsm_nbx* fsm) = 0;   // your arm controller
     virtual void step_gripper(struct fsm_nbx* fsm) = 0;     // your gripper controller
     // ... fsm_of / event_index / state_index / dispatch / advance / ... (generated)
   };

**B3. Write the runtime.** Subclass it and implement the two controllers — the
same logic as the Python ``step_*`` methods:

.. literalinclude:: ../examples/models/bt/py_pick/py_pick_main.cpp
   :language: cpp
   :caption: py_pick_main.cpp
   :lines: 31-66

**B4. Build and run.** The example ``CMakeLists.txt`` has a ``py_pick_bt`` target:

.. code-block:: console

   $ cmake -S . -B build && cmake --build build --target py_pick_bt
   $ ./build/py_pick_bt
   === py_pick: SEQUENCE, state await ===
   [    0.01 ms] BT  | Sequence                         IDLE -> RUNNING
   [    0.01 ms] BT  | FSMEvent right_arm.PICK          IDLE -> RUNNING
   [   20.34 ms] FSM | right_arm | state=Picking
   [   40.58 ms] FSM | right_arm | finished Picking -> produced completion
   [   40.58 ms] BT  | FSMEvent right_arm.PICK          RUNNING -> SUCCESS
   [   40.59 ms] BT  | FSMEvent gripper.GRASP           IDLE -> RUNNING
   [   60.83 ms] FSM | gripper   | state=Grasping
   [   81.06 ms] FSM | gripper   | finished Grasping -> produced completion
   [   81.07 ms] BT  | FSMEvent gripper.GRASP           RUNNING -> SUCCESS
   [   81.07 ms] BT  | Sequence                         RUNNING -> SUCCESS
   === py_pick: SUCCESS ===

The two tagged streams make the coordination legible: **BT** node transitions
next to the **FSM** state each tick. Read it top to bottom — the arm runs to
``Picking``, completes at ~40 ms, its node turns ``SUCCESS``, then the gripper
starts. With ``--fault`` the gripper's node turns ``FAILURE`` instead and the
sequence fails (exit code 1).

Going real-time: the 1 kHz variant
-----------------------------------

In ``py_pick`` the BT tick drives each FSM. On real hardware the controller
usually runs in its own fixed-rate loop. Because the generated node routes
send / advance / poll through **overridable** methods, you can keep this exact
tree and instead run each FSM in a 1 kHz thread — the BT only sends commands and
polls state. That is exactly what ``async_pick_bt`` does; see
:ref:`the async section of the coordination tutorial <btfsm-async>`.

Recap
-----

You built and ran a real coordination end to end. The pieces:

* an **FSM** is data + a step function — you own its controller (``step_<fsm>``);
* a **behaviour tree** is the coordinator — it owns the tick;
* ``send/await`` is the bridge — dispatch a command event, wait for a target;
* **state await** is robust to timing; **event await** is literal but transient;
* **on-fail** turns an FSM fault into node ``FAILURE``;
* the *same model* runs in Python (py_trees) or C++ (BehaviorTree.CPP), and the
  *same node* runs synchronously or against a real-time controller.

From here, the reference tutorials go deeper: :doc:`tutorials/fsm`,
:doc:`tutorials/bt`, and :doc:`tutorials/bt_and_fsm`.

.. _coord2b: https://github.com/rosym-project/coord2b
.. _BehaviorTree.CPP: https://www.behaviortree.dev/
