from databroker.core import BlueskyRun
import numpy as np


class InvalidStreamError(KeyError):
    pass


class InvalidFieldError(KeyError):
    pass


def ndims_from_descriptor(descriptor: dict, field: str):
    return len(descriptor["data_keys"][field]["shape"])  # NOTE: this doesn't include event dim


def shape_from_descriptor(descriptor: dict, field: str):
    return descriptor["data_keys"][field]["shape"]


def fields_from_stream(run: BlueskyRun, stream: str):
    fields = []
    for descriptor in descriptors_from_stream(run, stream):
        fields.extend(fields_from_descriptor(descriptor))
    return fields


def descriptors_from_stream(run: BlueskyRun, stream: str):
    if stream not in run:
        raise InvalidStreamError(f"The stream named {stream} is not present in {BlueskyRun}")
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


def is_image_field(run: BlueskyRun, stream: str, field: str):
    data = getattr(run, stream).to_dask()[field]
    field_dims = data.ndim
    if 6 > field_dims > 2:
        # if field contains at least 1 entry that is at least one-dimensional (shape=2)
        # or 2-dimensional (shape=3) or up to 3-dimensional (shape=4)
        # then add field e.g. 'fccd_image'
        return True


def guess_stream_field(catalog: BlueskyRun):
    # TODO: use some metadata (techniques?) for guidance about how to get a preview

    streams = streams_from_run(catalog)
    if "primary" in streams:
        streams.remove("primary")
        streams.insert(0, "primary")

    for stream in streams:
        descriptor = descriptors_from_stream(catalog, stream)[0]
        fields = fields_from_descriptor(descriptor)
        for field in fields:
            field_ndims = ndims_from_descriptor(descriptor, field)
            if field_ndims > 1:
                return stream, field


def preview(catalog: BlueskyRun, stream: str, field: str):
    data = getattr(catalog, stream).to_dask()[field].squeeze()
    for i in range(len(data.shape) - 2):
        data = data[0]
    return np.asarray(data.compute())
