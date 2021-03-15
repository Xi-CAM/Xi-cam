# Data ingestion in Xi-CAM

## What is an ingestor?

The `ingestor` design is [specified by the Databroker team](https://github.com/danielballan/sniffers_and_ingestors/) to
provide an entrypoint for data generated external from the Bluesky environment. An ingestor is a `Callable` that accepts
a URI (often a local file path) and yields `(name, doc)` pairs. The yielded data follows the Bluesky `event-model`
structure (see [event-model documentation](https://blueskyproject.io/event-model/data-model.html)). Synthesizing these
event-model documents is made easier with the `RunBuilder`
(see [Bluesky-Live documentation](https://github.com/bluesky/bluesky-live)).
