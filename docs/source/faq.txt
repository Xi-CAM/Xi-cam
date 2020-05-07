# FAQ

## Python

### What is an entry point?

#### Entry Points




## GUIPlugin

### How do I create a GUIPlugin?

You can create a `GUIPlugin` several ways:

* Use `cookiecutter` to interactively set up a gui plugin according to a template.
* Clone/download the `ExamplePlugin` repository and modify it
  * change the class names
  * update the `setup.py` file

For more details, see the [GUIPlugin documentation](gui-plugin.md).

### How do I install my GUIPlugin?

After creating a `GUIPlugin` with appropriate entry points,
you can install it by running `pip install -e .`
in the directory that your `setup.py` file is located.

### How do I prevent a GUIPlugin from showing up in Xi-CAM?

You need to uninstall it using `pip uninstall xicam.NAME`,
where "NAME" is the name defined in the `setup.py` file.