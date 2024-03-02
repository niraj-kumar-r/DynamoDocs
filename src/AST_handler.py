from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, unique, auto
from typing import Any, Dict, List


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

    def to_str(self):
        if self == DocItemType._class:
            return "ClassDef"
        elif self == DocItemType._class_method or self == DocItemType._function or self == DocItemType._sub_function:
            return "FunctionDef"
        # This shouldn't be called for other types
        # assert False, f"{self.name}"
        return self.name

    def print_self(self):
        return self.name


@unique
class DocItemStatus(Enum):
    doc_upto_date = auto()
    doc_has_not_been_generated = auto()
    doc_code_changed = auto()
    doc_has_new_referencer = auto()
    doc_has_no_referencer = auto()


@dataclass
class DocItem:
    item_type: DocItemType = DocItemType._class_method
    item_status: DocItemStatus = DocItemStatus.doc_has_not_been_generated

    item_name: str = ""
    code_start_line: int = -1
    code_end_line: int = -1
    md_content: List[str] = field(default_factory=list)
    content: Dict[Any, Any] = field(default_factory=dict)

    children: Dict[str, DocItem] = field(default_factory=dict)
    parent: Any[DocItem] = None
    depth: int = 0
