***************
Bluesky Browser
***************

A library of Qt widgets for searching saved bluesky data and viewing document
streams either live or from disk.

This is a prototype that may be fully rewritten, abandoned, or moved into other
libraries.

Launching the demo
==================

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
new tab with a more detailed view.

Roadmap
=======

*  Add matplotlib figures to the viewer.
*  Add a way to run just the viewer part against live data (from RE).
*  Make the search inputs, search result row, summary viewer, and tab
   factories configurable.
