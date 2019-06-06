# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
from recommonmark.transform import AutoStructify
from sphinx.ext import autodoc


# -- Project information -----------------------------------------------------

project = 'Xi-cam'
copyright = '2019, Ronald Pandolfi'
author = 'Ronald Pandolfi'

# The full version, including alpha/beta/rc tags
release = '0.1.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
   'numpydoc',
   'recommonmark',
   'sphinx.ext.autodoc',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


class SimpleClassDocumenter(autodoc.ClassDocumenter):
   objtype = "simpleclass"
   content_indent = ""
   
   def add_directive_header(self, sig):
      pass


class SimpleFunctionDocumenter(autodoc.FunctionDocumenter):
   objtype = "simplefunction"
   content_indent = ""
   
   def add_directive_header(self, sig):
      pass


def process_signature(app, what, name, obj, options, signature, return_annotation):
   print("RET: {}", return_annotation)
   print("app: {}\nwhat: {}\nname: {}\nobj: {}\noptions: {}\nsignature: {}",
      app, what, name, obj, options, signature)

def process_docstring(app, what, name, obj, options, lines):
   for line in lines:
      print("LINE: {}", line)

def setup(app):
    app.add_config_value('recommonmark_config', {
        'enable_eval_rst': True
        }, True)
    app.add_transform(AutoStructify)
   #  app.connect('autodoc-process-signature', process_signature)
   #  app.connect('autodoc-process-docstring', process_docstring)
   #  from sphinx.ext.autodoc import cut_lines
   #  app.connect('autodoc-process-docstring', cut_lines(4, what=['class']))
    app.add_autodocumenter(SimpleClassDocumenter)
    app.add_autodocumenter(SimpleFunctionDocumenter)
