from databroker.core import BlueskyRun


def ndims_from_descriptor(descriptor: dict, field: str):
    return len(descriptor["data_keys"][field]["shape"])  # NOTE: this doesn't include event dim


def shape_from_descriptor(descriptor: dict, field: str):
    return descriptor["data_keys"][field]["shape"]


def fields_from_stream(run: BlueskyRun, stream: str):
    return fields_from_descriptor(descriptors_from_stream(run, stream))


def descriptors_from_stream(run: BlueskyRun, stream: str):
    return run[stream].metadata["descriptors"]


def fields_from_descriptor(descriptor):
    return list(descriptor["data_keys"].keys())


def streams_from_run(run: BlueskyRun):
    return list(run)


def xarray_from_run(run: BlueskyRun, stream: str = None, field: str = None):
    data = run.to_dask()

    if stream:
        data = data[stream]

        if field:
            data = data[field]

    return data
