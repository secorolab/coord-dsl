coord-dsl
=========

**coord-dsl** is a textX_ Domain-Specific Language for event-driven finite
state machines (``.fsm``), with Python, C++, RDF, and graphviz generators.

From one model you can generate:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Target
     - Artifact
   * - ``cpp`` / ``python``
     - A self-contained state machine and step function
   * - ``graph`` / ``console``
     - JSON-LD, Turtle, or XML RDF graph
   * - ``dot`` / ``dot-console``
     - Graphviz source or a PNG, SVG, or PDF rendering

.. toctree::
   :maxdepth: 2
   :caption: Contents

   installation
   tutorials/fsm

.. _textX: https://textx.github.io/textX/
