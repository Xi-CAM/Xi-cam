# OperationPlugin Documentation

This documentation provides information on the foundational aspects
of the OperationPlugin class, as well as a more detailed API reference.

*If you are new to developing Xi-CAM plugins,
it is recommended that you follow the [QuickStart Guide](quickstart.md) first.*

## What Is an OperationPlugin?

An OperationPlugin can be thought of as a function with some extra annotations
attached to it.
When we want to define an OperationPlugin, we simply need to define a Python
function, then add some additional syntax to the function to define things like
inputs, outputs, descriptions of inputs/outputs, units, etc.

To achieve this, The OperationClass makes extensive use of Python decorators.

### Where Is OperationPlugin?

```python
xicam.plugins.operationplugin
```

### What Does an OperationPlugin Look Like?

Let's start off with a simple function that computes the square of its input:

```python
def my_square(n):
    return n**2
```

Now, let's make this an OperationPlugin:

```python
from xicam.plugins.operationplugin import operation, output_names

@operation
@output_names("square")
def my_square(n):
    return n**2
```

That's it!

Notice the two decorators here: `@operation` and `@output_names`.

The `@operation` says that this function is now a Xi-CAM OperationPlugin.
Any input arguments for the function will be the input names for the operation.
In this case, our input is `n`. (This can actually be overwritten by using a
different decorator, `@input_names`, which is described later.)

The `@output_names` allows us to name our outputs, in this case, `square`.
This will be useful when connecting multiple operations together in a `Workflow`.

### Default Input Values

If you want to provide you operation with default input values,
you can use argument defaults in your function:

```python
from xicam.plugins.operationplugin import operation, output_names

@operation
@output_names("square")
def my_square(n = 0):
    return n**2
```

This provides this operation's `n` input with a default value of `0`.

### Required and Highly-Used Decorators

In order to make a function an operation,
the following decorators *must* be used:
* `@operation` -- allows creation of operations from the function
* `@output_names` -- defines the name of the output(s)

Additionally, although not required to for an operation,
the following decorators are highly-recommended for use:
* `@display_name` -- the name of the operation
* `@describe_input` -- attach a description to the specified input (can be used multiple times)
* `@describe_output` -- attach a description to the specified output (can be used multiple times)

### Type Hinting (Optional)

With Python3 (3.5+), you can add type hinting to your code.
In the context of Xi-CAM OperationPlugins, this can be used to make your operation code
a little easier to read.

Let's use the `my_square` function we defined earlier in this operation:

```python
from xicam.plugins.operationplugin import operation, output_names

@operation
@output_names("square")
def my_square(n: int) -> int:
    return n**2
```

Note the `n: int` and the `-> int:` here. These *suggest* (but do not mandate) that
the input be an integer, and the output expected is an integer.

Again, these are not required, but they can help with readability and debugging your code.

For more information, see [Python's typing module](https://docs.python.org/3/library/typing.html).

### Example

A simple division operation that returns both the quotient and remainder.

This illustrates the use of multiple input/output descriptions and multiple outputs.

```python
from typing import Tuple
from xicam.plugins.operationplugin import describe_input, describe_output, display_name, operation, output_names

@operation
@output_names("quotient", "remainder")
@display_name("Division with Remainder")
@describe_input("dividend", "The number being divided.")
@describe_input("divisor", "The number to divide by.")
@describe_output("quotient", "The result of the division.")
@describe_output("remainder", "The remaining value.")
def my_divide(dividend: int, divisor: int = 1) -> Tuple[int, int]:
    quotient = int(dividend // divisor)
    remainder = dividend % divisor
    return quotient, remainder
```

## How Do I Use an OperationPlugin?

Now that we've defined an operation, how do we actually use it?

When we define an operation using the `@operation` decorator around a function,
we are defining a new operation class.

We can then create an operation object by using the syntax `func()`,
where `func` is the name of the function in the operation.

Let's take our `my_square` operation (defined above) and create one:

```python
from xicam.plugins.operationplugin import operation, output_names

@operation
@output_names("square")
def my_square(n):
    return n**2

op = my_square()
```

Now that we have an operation object (instance), `op`,
we can use it within a `Workflow`.

Let's create a `Workflow`, add our operation to it, then execute it.

```python
from xicam.core.execution import Workflow
from xicam.plugins.operationplugin import operation, output_names

@operation
@output_names("square")
def my_square(n):
    return n**2

op = my_square()
workflow = Workflow()
workflow.add_operation(op)
result = workflow.execute(n=11).result()
print(result)
```

We create a `my_square` operation, create a `Workflow`, and add the operation to the `Workflow`.
Then, we execute the `Workflow`, sending in the input `n=11`, wait for the result, and print it.

(For purposes of this document, we won't cover `Workflow` in depth.
More information about `Workflow` can be found in the [Workflow Documentation](workflow.md).)

## API Documentation

```eval_rst
.. automodule:: xicam.plugins.operationplugin
    :members:
```

## See Also

* [QuickStart Guide](quickstart.md)
* [GUIPlugin Documentation](gui-plugin.md)
* [Workflow Documentation](workflow.md)