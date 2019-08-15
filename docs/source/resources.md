# Resources

## Example Xi-cam Plugins

* [Xi-cam Log Plugin](https://github.com/synchrotrons/Xi-cam.plugins.Log) -
Example of a simple single-stage GUIPlugin.

* [Xi-cam NCEM Plugin](https://github.com/synchrotrons/Xi-cam.NCEM) -
Example of a multi-stage GUIPlugin with more functionality.

## Git

* [Try GitHub](https://try.github.io/) -
Landing page for some introductions and resources about git and GitHub.

* [Git Handbook](https://guides.github.com/introduction/git-handbook/) -
An introduction to git and GitHub.

## NSLS-II

Useful resources about NSLS-II software that Xi-cam uses.

* [Event Model](https://nsls-ii.github.io/architecture-overview.html) -
Describes an event-based data model.

* [Bluesky Documents](https://nsls-ii.github.io/bluesky/documents.html) -
Describes what a bluesky document is. 

## Python

Here are a few resources regarding object-oriented programming with Python3. Feel free to
look through these or even through resources you find on your own if you are interested.

* [Python OOP Introduction and Tutorial](https://realpython.com/python3-object-oriented-programming/) -

* [Presentation on OOP in Python](https://www.cs.colorado.edu/~kena/classes/5448/f12/presentation-materials/li.pdf) -

* [Python OOP](https://www.python-course.eu/python3_object_oriented_programming.php)

## Qt

[Qt](https://www.qt.io/what-is-qt/?utm_campaign=Navigation%202019&utm_source=megamenu) 
is a framework written in C++ for developing graphical user interfaces. 
PySide2 and PyQt5 are two different python bindings to the Qt C++ API. 
QtPy is a wrapper that allows for writing python Qt code with either PySide2 or PyQt5 installed.

Xi-cam uses [QtPy](https://pypi.org/project/QtPy/) to interact with different Python bindings to Qt.
QtPy allows you *"to write your code as if you were using PySide2 but import Qt modules from qtpy instead of PySide2 
(or PyQt5)"*. 
The references below show PySide2 examples and documentation; when writing a Xi-cam
plugin, make sure to use the `qtpy` modules when importing.

* [PyQt5 GUI Tutorial](https://build-system.fman.io/pyqt5-tutorial) - Introductory tutorial for learning the basic
concepts of Qt. *Note: this tutorial is written for PyQt5, remember to import from `qtpy` instead of `PyQt5` or 
`PySide2` when writing code for Xi-cam.*

* [PySide2 Simple Clickable Button](https://wiki.qt.io/Qt_for_Python_Tutorial_ClickableButton) - 
Short tutorial that describes the concept of signals and slots in Qt and shows how to create a button that
responds to clicking.

* [Pyside Documentation (Deprecated)](https://pyside.github.io/docs/pyside/index.html) -
Although this is deprecated, the documentation for Qt classes is pretty good. The newer PySide2 documentation is not
as complete as this documentation.

* [PySide2 Documentation](https://doc.qt.io/qtforpython/) - Documentation for PySide2. Since the QtPy API
resembles PySide2, this documentation is helpful for looking up python Qt modules and classes that you may use.

* [PyQtGraph](http://pyqtgraph.org/documentation/) -
Documentation for the pyqtgraph package, which relies on Qt and provides basic data visualization (plotting) and
various widgets (helpful for writing Xi-cam GUIPlugins).

