from enum import Enum, unique, auto


@unique
class AstEdgeType(Enum):
    reference_edge = auto()
    subfile_edge = auto()
    file_item_edge = auto()


@unique
class DocItemType(Enum):
    _repo = auto()
    _dir = auto()
    _file = auto()
    _class = auto()
    _class_method = auto()
    _function = auto()
    _sub_function = auto()
    _global_var = auto()
