# Entry Points

An entry point is a mechanism that can be used to make objects discoverable by a common interface / name.

## Xi-CAM Entry Points

In Xi-CAM, you can define entry points
and `pip install -e .` in your plugin package directory to register plugins.
This allows Xi-CAM to see our plugins when it loads.
Entry points are defined in `setup.py` files, in the `entry_points` key.

Let's look at an example repository and `setup.py`:

```bash
setup.py
xicam/
    myplugin/
        __init__.py           - defines MyGUIPlugin (also marks this directory as a Python module)
        operations/ 
            __init__.py       - marks this directory as a Python module
            edge_detection.py - contains edge detection operations (laplace and sobel)
        workflows/
            __init__.py       - (marks this directory as a Python module)
            myworkflow.py     - defines MyWorkflow.py
```

Here's what our `entry_points` might look like in `setup.py`:

```python
entry_points = {
    "xicam.plugins.GUIPlugin": ["myguiplugin = xicam.myplugin:MyGUIPlugin"],
    "xicam.plugins.OperationPlugin": [
        "laplace_operation = xicam.myplugin.operations.edge_detection:laplace",
        "sobel_operation = xicam.myplugin.operations.edge_detection:sobel"
    ],
}
```

As seen above, `entry_points` is a dictionary,
where each key is an entry point and each value is a list of objects / types being registered to that entry point.

The syntax is: `"entry point name": ["some_identifier = package.subpackage.module:ClassName"]`.

In this case,
we are registering `MyGUIPlugin` to the `xicam.plugins.GUIPlugin` entry point.
Similarly,
we are registering the `laplace` and `sobel` operations to the `xicam.plugins.OperationPlugin` entry point.

Note that `Workflows` are not registered in this way; they are not Xi-CAM plugins.

**Whenever you modify entry points, you must reinstall your package.**
You can do this by running `pip install -e .` in your package directory.

When Xi-CAM loads,
it will see the `xicam.plugins.GUIPlugin` entry point key 
and load in `MyGUIPlugin` defined (in the value).
Similarly, Xi-CAM will see the `xicam.plugins.OperationPlugin` entry point key
and load in the `laplace` and `sobel` operations.

## More Information

For more information about entry points, see the following:

* https://entrypoints.readthedocs.io/en/latest/
* https://packaging.python.org/specifications/entry-points/
* https://amir.rachum.com/blog/2017/07/28/python-entry-points/
