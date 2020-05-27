from databroker.core import BlueskyRun


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

def get_all_image_fields(run_catalog, stream=None):
    # image_fields = []
    all_streams_image_fields = {} 
    streams = [stream] if stream is not None else list(run_catalog)
    for stream in streams:
        stream_fields = get_stream_data_keys(run_catalog, stream)
        field_names = stream_fields.keys()
        for field_name in field_names:
            field_shape = len(stream_fields[field_name]["shape"])
            if field_shape > 1 and field_shape < 5:
                # if field contains at least 1 entry that is at least one-dimensional (shape=2)
                # or 2-dimensional (shape=3) or up to 3-dimensional (shape=4)
                # then add field e.g. 'fccd_image'
                if stream in all_streams_image_fields.keys():  # add values to stream dict key
                    all_streams_image_fields[stream].append(field_name)
                else:  # if stream does not already exist in dict -> create new entry
                    all_streams_image_fields[stream] = [field_name]
            # TODO how to treat non image data fields in streams
            # else:
    return all_streams_image_fields

def get_stream_data_keys(run_catalog, stream):
    return run_catalog[stream].metadata["descriptors"][0]["data_keys"]