Tutorial: FSM
=============

An FSM (finite state machine) is coord-dsl's smallest coordination unit. This
tutorial models one, generates it, and runs it — with a full **Python** section
and a full **C++** section. They share the same model and the same event-loop
semantics; only the runtime language differs.

.. contents::
   :local:
   :depth: 1

Modelling
---------

An FSM is a ``.fsm`` file. It declares:

* **STATES** — the stateful behaviours; a ``START_STATE`` and ``END_STATE``.
* **EVENTS** — occurrences the machine reacts to.
* **TRANSITIONS** — a directed ``FROM``/``TO`` edge between two states.
* **REACTIONS** — the policy: ``WHEN`` an event fires, ``DO`` a transition, and
  optionally ``FIRES`` further events.

.. literalinclude:: ../../examples/models/fsm/example.fsm
   :language: text
   :caption: examples/models/fsm/example.fsm

Two rules matter:

* **Reactions are ordered.** On each step the *first* reaction whose event is
  present **and** whose transition starts from the current state is taken; the
  rest are ignored that step.
* A ``namespace`` (``ns``) is required for graph output and gives every state,
  event and transition a stable URI.

The event-loop model (shared by Python and C++)
-----------------------------------------------

Events live in a **double buffer** — a *current* and a *future* set. One tick is
four operations:

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Operation
     - Effect
   * - ``produce_event(ev, E)``
     - set ``E`` in the **future** buffer (schedule it)
   * - ``reconfig_event_buffers(ev)``
     - swap future→current and clear future (advance one tick)
   * - ``consume_event(ev, E)``
     - read ``E`` from the **current** buffer
   * - ``fsm_step``
     - apply the first matching reaction: transition + fire events (to future)

So an event you produce this tick becomes *current* — and drives a transition —
only after the next ``reconfig``. This one-tick pipeline is identical in both
languages; the generated FSM code is only data + ``fsm_step``, never a loop.

Generate
--------

.. code-block:: bash

   textx generate example.fsm --target python -o ex_fsm.py
   textx generate example.fsm --target cpp    -o ex_fsm.hpp
   textx generate example.fsm --target graph --format json-ld --autocompact

Each target emits ``create_fsm()``, ``destroy_fsm()`` (C++), the
state/event/transition/reaction enums, and ``*_URIS`` tables. No control loop —
you own that.

Running in Python
-----------------

The Python runtime is ``coord_dsl.event_loop`` (the buffer ops) and
``coord_dsl.fsm`` (``fsm_step``). The generated module gives you ``EventID`` and
``StateID`` enums, ``create_fsm()`` and ``STATE_URIS``.

The loop is: run **your** behaviour (produce/consume events), ``fsm_step``, then
``reconfig_event_buffers``:

.. code-block:: python

   from coord_dsl.event_loop import produce_event, consume_event, reconfig_event_buffers
   from coord_dsl.fsm import fsm_step
   from ex_fsm import EventID, StateID, create_fsm, STATE_URIS

   fsm = create_fsm()
   while fsm.current_state_index != StateID.S_EXIT:
       behavior(fsm)                          # YOUR code: produce/consume events
       fsm_step(fsm)                          # apply the first matching reaction
       reconfig_event_buffers(fsm.event_data)

``fsm.current_state_index`` is the live state; ``fsm.event_data`` holds the
buffers. You "define behaviour" by writing ``behavior`` — typically it inspects
``current_state_index`` and, when a state's work is done, produces the event
that advances the machine. A complete, time-driven controller ships with the
repo:

.. literalinclude:: ../../examples/models/fsm/generated_fsm_bhv.py
   :language: python
   :caption: examples/models/fsm/generated_fsm_bhv.py
   :lines: 1, 28-80

Run it:

.. code-block:: bash

   textx generate example.fsm --target python -o ex_fsm.py
   python generated_fsm_bhv.py        # Ctrl+C to stop

Running in C++
--------------

The C++ header is self-contained and depends on coord2b_. The API mirrors
Python one-to-one (``produce_event`` / ``consume_event`` /
``reconfig_event_buffers`` / ``fsm_step_nbx``), and the loop has the same shape:

.. literalinclude:: ../../examples/models/fsm/test_fsm.cpp
   :language: cpp
   :caption: examples/models/fsm/test_fsm.cpp — the control loop
   :lines: 27-63

``fsm->current_state_index`` and ``fsm->states[i].name`` read the live machine;
``fsm->event_data`` holds the buffers. Build against coord2b with CMake:

.. literalinclude:: ../../examples/models/fsm/CMakeLists.txt
   :language: cmake
   :caption: examples/models/fsm/CMakeLists.txt

.. code-block:: bash

   cmake -S . -B build && cmake --build build
   ./build/fsm_test

Where to go next
----------------

An FSM captures *one* behaviour's lifecycle. To orchestrate several FSMs — start
one, wait for it, then start another — coordinate them from a
:doc:`behaviour tree <bt_and_fsm>`.

.. _coord2b: https://github.com/rosym-project/coord2b
