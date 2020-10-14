from typing import Generator, Tuple

from databroker.core import BlueskyRun
import numpy as np
from databroker.in_memory import BlueskyInMemoryCatalog


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


def display_name(catalog: BlueskyRun):
    name = []

    if 'sample_name' in catalog.metadata['start']:
        name.append(catalog.metadata['start']['sample_name'])

    if 'scan_id' in catalog.metadata['start']:
        name.append(f"<{catalog.metadata['start']['scan_id']}>")

    name.append(f"#{catalog.metadata['start']['uid'][:5]}")

    return ' '.join(name)


def run_from_doc_stream(doc_stream: Generator[Tuple[str, dict], None, None])->BlueskyRun:
    # load data into catalog
    document = list(doc_stream)
    uid = document[0][1]["uid"]
    catalog = BlueskyInMemoryCatalog()
    # TODO -- change upsert signature to put start and stop as kwargs
    # TODO -- ask about more convenient way to get a BlueskyRun from a document generator
    def psuedo_ingestor():
        yield from document
    catalog.upsert(document[0][1], document[-1][1], psuedo_ingestor, tuple(), {})
    return catalog[uid]