Tutorial: FSM
=============

Goal: model a finite state machine, generate it, and run it — first in
**Python**, then in **C++**.

1. Model
--------

An FSM is a ``.fsm`` file: states, a start/end state, events, transitions, and
the *reactions* that fire transitions when an event occurs.

.. literalinclude:: ../../examples/models/fsm/example.fsm
   :language: text
   :caption: examples/models/fsm/example.fsm

Reactions are ordered: the first reaction whose event fired *and* whose
transition starts from the current state is taken.

2. Generate
-----------

.. code-block:: bash

   textx generate example.fsm --target python -o ex_fsm.py
   textx generate example.fsm --target cpp    -o ex_fsm.hpp
   textx generate example.fsm --target graph --format json-ld --autocompact

The generated code is **passive**: enums for states/events/transitions, tables,
and a ``create_fsm()`` factory. It contains no loop — you drive it.

.. _fsm-python:

3a. Run it in Python
--------------------

The Python runtime lives in ``coord_dsl.event_loop`` and ``coord_dsl.fsm``. The
tick loop is: run **your** behaviour (produce/consume events), ``fsm_step``,
then ``reconfig_event_buffers`` to swap the event buffers for the next tick.

.. code-block:: python

   from coord_dsl.event_loop import produce_event, consume_event, reconfig_event_buffers
   from coord_dsl.fsm import fsm_step
   from ex_fsm import EventID, StateID, create_fsm

   fsm = create_fsm()
   while fsm.current_state_index != StateID.S_EXIT:
       behavior(fsm)                       # YOUR code: produce/consume events
       fsm_step(fsm)                       # apply the first matching reaction
       reconfig_event_buffers(fsm.event_data)

A complete, runnable example with a real ``behavior`` (a time-driven controller)
ships with the repo:

.. literalinclude:: ../../examples/models/fsm/generated_fsm_bhv.py
   :language: python
   :caption: examples/models/fsm/generated_fsm_bhv.py
   :lines: 1, 44-80

.. _fsm-cpp:

3b. Run it in C++
-----------------

The C++ header is self-contained and depends on coord2b_. The same loop shape
applies: ``produce_event`` → run behaviour → ``fsm_step_nbx`` →
``reconfig_event_buffers``.

.. literalinclude:: ../../examples/models/fsm/test_fsm.cpp
   :language: cpp
   :caption: examples/models/fsm/test_fsm.cpp
   :lines: 27-63

Build it against coord2b with CMake:

.. literalinclude:: ../../examples/models/fsm/CMakeLists.txt
   :language: cmake
   :caption: examples/models/fsm/CMakeLists.txt

.. code-block:: bash

   cmake -S . -B build && cmake --build build
   ./build/fsm_test

Key API (both languages)
------------------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Call
     - Meaning
   * - ``produce_event(ev, E)``
     - schedule event ``E`` (written to the *future* buffer)
   * - ``reconfig_event_buffers(ev)``
     - swap future→current, clear future (advance one tick)
   * - ``consume_event(ev, E)``
     - is ``E`` present on the *current* buffer?
   * - ``fsm_step(fsm)`` / ``fsm_step_nbx(fsm)``
     - apply the first matching reaction, transition, fire events

.. _coord2b: https://github.com/rosym-project/coord2b
