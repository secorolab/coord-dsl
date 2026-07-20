.. _pytrees-vs-btcpp:

py_trees vs BehaviorTree.CPP
============================

The two BT engines (py_trees_ for the ``python`` target, BehaviorTree.CPP_ for
``xml``/``cpp``) differ in more than how the tree is delivered (run-time XML vs
Python code). This page lists the semantic differences, which ones the
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
     - ``IfThenElse``, ``WhileDoElse``, ``Switch<N>``, ``TryCatch``
     - none built in (selectors/sequences only; ``Composite`` is subclassable)

Bridged by the ``python`` target
--------------------------------

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
* **Ports** — a port bound to a blackboard key (``goal: {pick_pose}``) is read
  when the leaf ticks, via ``node.ports["goal"]``; an ``out``/``inout`` port is
  written back with ``node.set_port("pose", value)``. Literal and quantity
  arguments are resolved at generation time.
* **Sub-trees** — ``subtree <t> as inst (…)``, with or without ``autoremap``, is
  **expanded at generation time**, with each instance's keys resolved there: a
  bound parameter becomes the caller's key (or its literal), and any key the
  caller did not bind becomes ``inst/key`` (or the caller's key of the same
  name, under ``autoremap``). That reproduces BT.CPP's per-sub-tree blackboard —
  two instances of the same sub-tree share nothing — without a run-time
  remapping layer. The cost is that the tree is inlined per instance, so a
  sub-tree used twice appears twice in the built tree.

Not bridged (and why)
---------------------

* ``[skip-if]`` and ``[while]`` — both produce ``SKIPPED``, a status py_trees
  does not have. A skipped child is *transparent* to its parent composite
  (a sequence continues past it); mapping it onto ``SUCCESS`` or ``FAILURE``
  would silently change the tree's semantics, so it is rejected instead.
* ``[on-halted]`` — py_trees invalidation (``stop(INVALID)``) is not the same
  event as a BT.CPP ``halt()`` of a running node; wiring the script to the
  wrong one would fire it spuriously. Deferred until a use case pins the
  semantics down.
* ``if-then-else`` / ``while-do-else`` / ``switch`` / ``try-catch`` — no
  *native* py_trees composite has these semantics. A custom ``Composite``
  subclass could implement each of them exactly; what is rejected is
  emulating them from the built-in selectors, which changes tick behaviour.
* ``script`` / ``set_blackboard`` builtins and the full BT.CPP scripting
  language (multiple ``;``-separated statements, string concatenation, …).
* ``delay`` / ``loop`` / ``precondition`` decorators.
* **Recursive** sub-trees — rejected here at generation time, as BT.CPP rejects
  them at load time (``"Recursive behavior tree cycle detected"``); neither
  engine builds a self-referencing tree.

All of these raise ``NotImplementedError`` at **generation** time, so an
unsupported model never produces a silently-different Python tree — use the
C++/XML backend for those.

.. _BehaviorTree.CPP: https://www.behaviortree.dev/
.. _py_trees: https://py-trees.readthedocs.io/
