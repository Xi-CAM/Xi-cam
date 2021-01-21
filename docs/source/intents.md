# Intents Documentation

This documentation provides information on the use of Intents to annotate data, including how they're applied to `OperationPlugin`'s.

*If you are new to developing Xi-CAM operations,
it is recommended that you follow the [operations development guide](operation-plugin.md) first.*

For more general development resources, see the [Resources](resources.md) page.

<!--Note that the examples in this documentation can be run in a python interpreter outside of Xi-CAM-->
<!--(for demonstration purposes).-->
<!--Auxiliary support code to be able to do this is marked with a comment ```# Only need if not running xicam```.-->
<!--When developing within Xi-CAM, you will **not** need the lines of code marked with that comment.-->

## What Is an Intent?

In Xi-CAM, an `Intent` generally represents a descriptive annotation of how to visualize data.
Basically, an `Intent` is a recipe for constructing a visualization.
When an `Intent` is associated with an operation, Xi-CAM may use it to automatically generate plots as you adjust your workflow.
An `Intent` can be embedded in a Databroker `BluesklyRun`, so they may be preserved along with derived (and also raw) data.

TODO: image representing intents visually

### The Lifecycle of an Intent

A `GUIPlugin` that supports intents will contain a `CanvasManager`.
Active intents will be rendered into a `Canvas` owned by the `CanvasManager`.
When an `Intent` is activated, the manager may generate a new `Canvas` for its rendering.
In cases such as co-plotting, a pre-existing `Canvas` may be used; that choice is based on the corresponding intents' `match_key` attributes.

## What Types of Intents are Available?

The list of intents is extensible via the `IntentPlugin`, however many use cases will fit into one of these generic types:

- PlotIntent
- ImageIntent
- ErrorBarIntent
- BarIntent

Although these types are primitive, additional specialized features can be added to them by specifying `mixin`'s.

## Adding Intents to Operations

The `@intent(...)` decorator can be used to annotate an `OperationPlugin` as shown:
```eval_rst
.. autodecorator:: xicam.plugins.operationplugin.intent
```
