***************
Bluesky Browser
***************

A library of Qt widgets for searching saved bluesky data and viewing document
streams either live or from disk.

This is a prototype that may be fully rewritten, abandoned, or moved into other
libraries.

Launching the demo
==================

Create a custom conda environment.

.. code-block:: bash

   conda create -n bluesky_browser python=3 \
       bluesky jsonschema matplotlib ophyd pyqt \
       pyzmq qtpy suitcase-jsonl tornado traitlets  \
       -c lightsource2-tag
   conda activate bluesky_browser

Clone and install.

.. code-block:: bash

   git clone https://github.com/NSLS-II/bluesky-browser
   cd bluesky-browser
   pip install -e .

Run the demo.

.. code-block:: bash

   bluesky-browser --demo

The above generates example data in a temporary directory and launches a Qt
application to browse that data. It supposes there are two catalogs of data,
`abc` and `xyz`, which could be from two instruments or perhaps "raw" data
and "processed" data from the same instrument. The catalogs may be searched by
date range or any custom Mongo query. Clicking on a search result pulls up a
new tab with a more detailed view. There are two viewing areas to facilitate
comparing data. Right-click and drag a tab to move it between areas.

To customize and extend this, generate a configuration file

.. code-block:: bash

   bluesky-browser --generate-config

and edit it. The ``bluesky-browser`` will automatically discover and apply the
configuration file if it located in the current directory where
``bluesky-browser`` is run. (In the future we will add a proper search path
with other standard locations.)

Intended Scope
==============

* Search saved data from any databroker Catalog (backed by MongoDB or JSONL or
  ....).
* View and compare data from runs. Use "hints" as defaults to guide how to view
  a given run, and let the user adjust from there.
* Perform basic plot manipulations, not rising to the level of a full data
  *analysis* GUI (e.g. no nonlinear curve-fitting) but enabling some
  interactive tuning to provide a useful view of the data.
* View live data streaming in from the RunEngine (via some message bus).
* Be extensible, providing for the possibility of views that are specific to a
  beamline or instrument.

Current Features
================

* Search multiple Catalogs (e.g. multiple beamlines) for saved data and sort
  search results.
* View selected search results in individual tabs or "over-plotted" in one tab.
* View Header, baseline readings, and line plots from saved or streaming data.
* "Over-plot" arbitrary groups of Runs, including saved data, streaming data,
  or a mix of both.

Roadmap
=======

* Get feature parity with Best-Effort Callback.
    * Table
    * Grid
    * PeakStats
* Add image stack viewer.
* Enable user to change what is plotted interactively. (The hints becomes just
  a *default*.)
* Add a way to run just the viewer part against live data (from RE).
* Add a "Summary" widget to the top of the Header tab.
* Add integration with suitcase for file export, starting with CSV.
* Add context menus (right click) as an alternative way to do overplotting,
  etc.
* Support "progressive search", iteratively refining search results.
