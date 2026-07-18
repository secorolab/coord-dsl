Installation
============

The Python package (the DSLs and generators)
--------------------------------------------

.. code-block:: bash

   pip install coord_dsl          # from PyPI
   # or, from a checkout:
   pip install -e .

This gives you the ``textx`` command with the ``fsm`` and ``bt`` languages and
their generators registered as entry points.

Verify:

.. code-block:: bash

   textx list-languages          # should list `fsm` and `bt`
   textx list-generators         # fsm_cpp, fsm_python, bt_xml, bt_cpp, ...

Native runtime dependencies (for running generated code)
--------------------------------------------------------

Generated **C++** depends on two libraries:

* coord2b_ — the FSM / event-loop runtime (``produce_event``, ``consume_event``,
  ``fsm_step_nbx``, ``reconfig_event_buffers``). Installed via CMake
  (``find_package(coord2b)``).
* BehaviorTree.CPP_ v4 — the behaviour-tree engine, for BT and BT+FSM.

Generated **Python** for FSMs depends only on ``coord_dsl`` itself
(``coord_dsl.fsm`` and ``coord_dsl.event_loop`` provide the runtime).

Optional: code formatting
-------------------------

If ``clang-format`` is on ``PATH``, the C++ generators format their output
in place using the nearest ``.clang-format`` file. It is a best-effort nicety
and is skipped when unavailable.

Building these docs
-------------------

.. code-block:: bash

   pip install -e ".[docs]"      # sphinx + furo
   sphinx-build -b html docs docs/_build/html

.. _coord2b: https://github.com/rosym-project/coord2b
.. _BehaviorTree.CPP: https://www.behaviortree.dev/
