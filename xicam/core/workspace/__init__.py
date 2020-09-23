import enum


class Workspace:
    ...


class WorkspaceDataType(enum.Enum):
    Ensemble = enum.auto()
    Catalog = enum.auto()
    Intent = enum.auto()
