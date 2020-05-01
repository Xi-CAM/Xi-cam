# Workflow Documentation

This documentation provides information on the `Worfklow` class and its API reference.

*If you are new to developing Xi-CAM plugins,
it is recommended that you follow the [QuickStart Guide](quickstart.md) first.*

Note that the examples in this documentation can be run in a python interpreter outside of Xi-CAM
(for demonstration purposes).
Auxiliary support code to be able to do this is marked with a comment ```# Only need if not running xicam```.
When developing within Xi-CAM, you will **not** need the lines of code marked with that comment.

## What Is a Workflow?

In Xi-CAM, a `Workflow` is a graph-like structure that represents a sequence of one or more `OperationPlugins` to execute.
Basically, it allows you to process data through some pipeline of operations. 
Multiple operations can be linked together in a `Workflow`,
provided that the connection between any two operations is compatible (based on inputs and outputs).
Execution can be performed asynchronously or synchronously.

### Where Is Workflow?

```python
xicam.core.execution.Workflow
```

### What Does a Workflow Look Like?

As mentioned previously, a Workflow can be thought of as a graph-like structure.
We can add operations (*nodes*) and connect them with links (*edges*).

#### Example

```python
from xicam.core import execution  # Only need if not running xicam
from xicam.core.execution import localexecutor  # Only need if not running xicam
from xicam.core.execution import Workflow
from xicam.plugins.operationplugin import operation, output_names

execution.executor = localexecutor.LocalExecutor()  # Only need if not running xicam

# Define our operations
@operation
@output_names("sum")
def my_add(x, y):
    return x + y

@operation
@output_names("square_root")
def my_sqrt(n):
    from math import sqrt
    return sqrt(n)

# Instanciate operations
add_op = my_add()
sqrt_op = my_sqrt()

# Create a Workflow and add our operation instances to it
workflow = Workflow()
workflow.add_operations(add_op, sqrt_op)

# Link the "sum" output of add_op to the "n" input of sqrt_op
workflow.add_link(add_op, sqrt_op, "sum", "n")

# Execute the workflow, sending 1 and 3 as initial inputs to add_op (the first operation)
# This should give us sqrt(1 + 3) -> 2.0.
result = workflow.execute_synchronous(x=1, y=3)
print(result)  # Should be ({"square_root": 2.0},)
```

In this example, we use an addition operation and a square root operation in our Workflow.
We want to add two numbers, then take the square root of the sum.

First, we instanciate our two operation types.
This gives us an `add_op` operation object and a `sqrt_op` operation object.

Next, we add our operations to the workflow.

We then want to link the operations together so we first add two numbers,
then take the square root of the result.
We do this by connecting `add_op`'s "sum" output to `sqrt_op`'s "n" input.

Now that we have added our operations and connected them as we like,
we can run our workflow. 
In this case, we will use `execute_synchronous` (there are other methods for execution which will be explained later).

However, if we just were to try ```workflow.execute_synchronous()```,
the workflow wouldn't know what the "x" and "y" inputs are supposed to be for the first operation, `add_op`.

**We need to pass in data for any first operations' inputs when we execute our workflow**.
To do this, we simply pass in `x=1` and `y=3` to our `execute_synchronous` call.

## Useful Methods for Modifying the Workflow

Here is a condensed version of the various ways to modify a Workflow's operation and links.
For more information, see the [API Reference](#api-reference).

### Adding, Inspecting, and Removing Operations

Adding operations:
* `add_operation` -- add an operation to the `Workflow`
* `add_operations` -- add multiple operations to the `Workflow`
* `insert_operation` -- insert an operation at a specific index in the `Workflow`

Inspecting operations:
* `operations` -- get the operations currently in the `Workflow`

Removing operations:
* `remove_operation` -- remove an operation from the `Workflow`
* `clear_operations` -- remove *all* operations from the `Workflow`

### Adding, Inspecting, and Removing Links

Adding links:
* `add_link` -- add a link between one operation's output and another's input
* `auto_connect_all` -- try to automatically connect all the operations based on input/output names

Inspecting links:
* `links` -- get all links in the `Workflow`
* `operation_links` -- get all links connected to a specific operation in the `Workflow`
* `get_inbound_links` -- get all incoming links to a specific operation in the `Workflow`
* `get_outbound_links` -- get all outgoing links from a specific operation in the `Workflow`

Removing links:
* `remove_link` -- remove a link from the `Workflow`
* `clear_operation_links` -- remove all links for a specified operation in the `Workflow`
* `clear_links` -- remove all links in the `Workflow`

### Enabling and Disabling an Operation

It is possible to enable or disable operations.
By default, all operations added to a `Workflow` are enabled.
For more information, see the [API Reference](#api-reference).

## Executing a Workflow

When you execute a Workflow, the operations are executed based on how they are linked together.

There are a few ways to run a Workflow: `execute`, `execute_synchronous`, and `execute_all`.

### Synchronous Execution

As we saw in our example earlier, we can use `execute_syncrhonous` to run a Workflow as a normal snippet of Python code.
When this method is run, the we wait until we get a result back before the interpreter can continue running code.

### Asynchronous Execution (Recommended)

The `execute` and `execute_all` methods are asynchronous, so they run in a separate thread.
This is highly beneficial in a GUI environment like Xi-CAM,
since we don't want to block Xi-CAM's UI from responding,
and we could potentially offload execution onto a remote device.
These methods take in several parameters; for now, we will focus on three of these parameters:

* `callback_slot` --
Function to execute when the results of the Workflow are ready.
The callback_slot gives you access to these results as a positional argument.
**This is invoked for each result.** 
For example, let's say you have a 
crop operation that takes in an image (array) as an input parameter.
You could pass in a list of images to crop to `Workflow.execute_all()`,
and the callback_slot will be invoked for each of the images in the passed list.
Basically, you will get a cropped image for each image sent into the workflow.

* `finished_slot` --
Function to execute when the internal thread in the Workflow has finished its execution
(all of the operations are done).
**This occurs once during a Workflow's execution.**

* `kwargs` --
Any additional keyword arguments to pass into the method;
these usually correspond with the entry operations' inputs (as we saw in our example earlier).

The primary difference between `Workflow.execute` and `Workflow.execute_all` is
that `execute_all` will run multiple times for the `kwargs` passed in. 
This means the `kwargs` must have an iterable value.
Let's look at some examples.

#### Example for execute
Let's revisit our addition and square root workflow from earlier but make it asynchronous:

```python
from qtpy.QtWidgets import QApplication  # Only need if not running xicam
from xicam.core import execution  # Only need if not running xicam
from xicam.core.execution import localexecutor  # Only need if not running xicam
from xicam.core.execution import Workflow
from xicam.plugins.operationplugin import operation, output_names

qapp = QApplication([])  # Only need if not running xicam
execution.executor = localexecutor.LocalExecutor()  # Only need if not running xicam

# Define our operations
@operation
@output_names("sum")
def my_add(x, y):
    return x + y

@operation
@output_names("square_root")
def my_sqrt(n):
    from math import sqrt
    return sqrt(n)

# Define callback slot (when a result is ready)
def print_result(*results):
    print(results)

# Define finished slot (when the workflow is entirely finished)
def finished():
    print("Workflow finished.")

# Instanciate operations
add_op = my_add()
sqrt_op = my_sqrt()

# Create a Workflow and add our operation instances to it
workflow = Workflow()
workflow.add_operations(add_op, sqrt_op)

# Link the "sum" output of add_op to the "n" input of sqrt_op
workflow.add_link(add_op, sqrt_op, "sum", "n")

# Execute the workflow, sending 1 and 3 as initial inputs to add_op (the first operation)
# This should give us sqrt(1 + 3) -> 2.0.
workflow.execute(callback_slot=print_result,
                 finished_slot=finished,
                 x=1,
                 y=3)
```

This will print out:
```bash
({'square_root': 2.0},)
Workflow finished.
```

Notice that we've added two new functions for our callback slot and our finished slot.
`print_result` will be called when the workflow has finished its execution and the result is ready.
`finished` will be called when the workflow has finished execution for all of its input data.
In this case, we have only one set of input data, `x=1` and `y=3`.

(Also note that we have an additional import and that we are creating a QApplication;
this is not needed when working within Xi-CAM).

#### Example for execute_all

Now, let's say we want to do this addition and square root workflow for multiple sets of x and y inputs.
We can use `execute_all` to do this:

```python
from qtpy.QtWidgets import QApplication  # Only need if not running xicam
from xicam.core import execution  # Only need if not running xicam
from xicam.core.execution import localexecutor  # Only need if not running xicam
from xicam.core.execution import Workflow
from xicam.plugins.operationplugin import operation, output_names

qapp = QApplication([])  # Only need if not running xicam
execution.executor = localexecutor.LocalExecutor()  # Only need if not running xicam

# Define our operations
@operation
@output_names("sum")
def my_add(x, y):
    return x + y

@operation
@output_names("square_root")
def my_sqrt(n):
    from math import sqrt
    return sqrt(n)

# Define callback slot (when a result is ready)
def print_result(*results):
    print(results)

# Define finished slot (when the workflow is entirely finished)
def finished():
    print("Workflow finished.")

# Instanciate operations
add_op = my_add()
sqrt_op = my_sqrt()

# Create a Workflow and add our operation instances to it
workflow = Workflow()
workflow.add_operations(add_op, sqrt_op)

# Link the "sum" output of add_op to the "n" input of sqrt_op
workflow.add_link(add_op, sqrt_op, "sum", "n")

# Execute the workflow, sending 1 and 3 as initial inputs to add_op (the first operation)
# This should give us sqrt(1 + 3) -> 2.0.
workflow.execute_all(callback_slot=print_result,
                    finished_slot=finished,
                    x=[1, 10, 50],
                    y=[3, 15, 50])
```

This will print out:
```bash
({'square_root': 2.0},)
({'square_root': 5.0},)
({'square_root': 10.0},)
Workflow finished.

Notice that we've just changed `execute` to `execute_all`, and we've modified the `x` and `y` values to be lists.
Now, we will have three executions: `x=1 y=3`, `x=10 y=15`, and `x=50 y=50`.
Each time one of these executions finishes, our callback slot `print_result` is called.
When the workflow is finished executing everything, then our finished slot `finished` is called.
```

## API Reference

```eval_rst
.. autoclass:: xicam.core.execution.Workflow
   :show-inheritance:
   :inherited-members:
   :members:
```