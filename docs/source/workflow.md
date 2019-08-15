# Workflows in Xi-cam

*Note: **W**orkflow with an uppercase **W** will be used to refer to a Xi-cam Workflow.*

In Xi-cam, a `Workflow` represents a sequence of one or more `ProcessingPlugins` to execute. With a Workflow, you can
grab input data from a GUIPlugin's internal data model, parameterize each process (ProcessingPlugin), and chain
multiple processes together, where one process's outputs become the next process's inputs.

## Adding Processes to the Workflow

The Workflow class provides a few different ways to add processes:

* __init__() - You can pass a list of ProcessingPlugin objects to be used when constructing the Workflow.
* addProcess() - You can add a ProcessingPlugin to the end of the Workflow's current list of ProcessingPlugins.
* insertProcess() - You can insert a ProcessingPlugin into any position in the Workflow's list of ProcessingPlugins.
* processes() - You can use this setter to provide a new list of ProcessingPlugins for the Workflow to store.

## Connecting Processes to Each Other

By default, processes in a Workflow operate in sequence independently of each other (i.e. their inputs and outputs are
not connected to each other). If you want to chain each process's outputs to the next process's inputs, you can use
`autoConnectAll()` method to configure this for your Workflow. Conversely, the `clearConnections()` method can be used
to remove all input/output connections from the Workflow.

## Executing a Workflow

When you execute a Workflow, the processes are executed in the order in which they have been inserted into the
Workflow. There are two primary methods to execute a Workflow: `execute()` and `execute_all()`. These methods take in
several parameters; for now we will look more closely at three of them:

* callback_slot - Function to execute when the results of the Workflow are ready. The callback_slot gives you access
to these results as a positional argument. This is invoked for *each* result. For example, let's say you have a 
CropProcessingPlugin that takes in an image (array) as an input parameter. You could pass in a list of images to
crop to `Workflow.execute_all()`, and the callback_slot will be invoked for each of the images in the passed list.

* finished_slot - Function to execute when the internal thread in the Workflow has finished its execution (all of the
processes are done). This occurs *once* during a Workflow's execution.

* kwargs - Any additional keyword arguments to pass into the method; these are usually used to pass in the initial
processes inputs.

The primary difference between `Workflow.execute()` and `Workflow.execute_all()` is that `execute_all()` expects
each kwarg to be an iterable of the same length to be iterated over and executed through the Workflow. This is useful
if you want to perform the same process on multiple sources of data.

For example, we could have a CropProcessingPlugin that takes in inputs `data` and `crop_region`. Let's say our data
should be an Image object, and our crop_region should be a CropRegion object. If we use `execute()`, we can pass in one
Image (`data = image`) and one CropRegion (`crop_region = crop`). The callback_slot that we define for the Workflow will
be invoked *once*, since there is one input data set. This would look something like:

```python
class CropProcessingPlugin(ProcessingPlugin):
    data = Input(description='Input image', type=nd.array, visible=False)
    crop_region = Input(description='Crop region-of-interest', type=nd.array, visible=False)
    cropped_data = Output(description='Cropped data', type=nd.array)

    def evaluate(self):
        self.cropped_data.value = some_crop_function(data.value, crop_region.value) 


# --------------------------------------------------------
# ... Code below could be contained in a derived GUIPlugin
    workflow = Workflow()
    workflow.addProcess(CropProcessingPlugin())

    data = currentImage()
    cropRegion = currentROI()
    workflow.execute(callback_slot=saveCropResult, finished_slot=cropFinished, data=data, crop_region=cropRegion)
    # ...

def saveCropResult(self, result):
    print(result)  # prints once (the array in cropped_data.value)

def cropFinished(self):
    print("crop finished")  # prints once

```

If we wanted to crop multiple images with the same CropProcessingPlugin, we could use `execute_all()`.
CropProcessingPlugin would still expect the same parameters, an Image object (data) and a CropRegion object
(crop_region). Now, when using execute_all we could pass a list of Image objects (`data = images`) and a list of
CropRegion objects (`crop_region = crops`) (each list has an equal number of items). This would effectively pass in each
data and crop_region into the CropProcessingPlugin for as many Images / CropRegions are passed into execute_all. The
callback_slot will be invoked each time an Image and CropRegion is processed and ready. The finished_slot will be
invoked once, when all of the Images and CropRegions have been processed.

```python
# Refer to the above code-snippet for CropProcessingPlugin
    
    # ...
    workflow = Workflow()
    workflow.addProcess(CropProcessingPlugin())

    data = currentImages()
    cropRegion = [currentROI()] * len(data)
    workflow.execute_all(None, callback_slot=saveCropResult, finished_slot=cropFinished, data=data, crop_region=cropRegion)

def saveCropResult(self, result):
    # This method will be called N times, where N is the number of Images (len(data))
    # Each result represents the result (cropped_data.value array) of cropping Image N.
    print(result)

def cropFinished(self):
    print("crop finished")  # prints once
```

**Note: `execute_all()` as an extra required positional argument, connection. For now, you can pass `None` as the
initial argument.**