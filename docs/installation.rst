Installation
============

The Python package
------------------

.. code-block:: bash

   pip install coord_dsl
   # or, from a checkout:
   pip install -e .

This registers the ``.fsm`` language and its generators with ``textx``.

Generated Python uses the bundled ``coord_dsl`` runtime. Generated C++ uses
coord2b_ for the FSM and event-loop runtime.

If ``clang-format`` is on ``PATH``, the C++ generator formats its output using
the nearest ``.clang-format`` file. Graphviz is required only for rendered
``png``, ``svg``, and ``pdf`` output; plain ``dot`` output needs no executable.

Building these docs
-------------------

.. code-block:: bash

   pip install -e ".[docs]"
   sphinx-build -W -b html docs docs/_build/html

.. _coord2b: https://github.com/rosym-project/coord2b
