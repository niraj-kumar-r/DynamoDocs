from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, unique, auto
from typing import Any, Dict, List, Union, Optional
from colorama import Fore, Style


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
        change_color = Fore.WHITE
        if self == DocItemType._dir:
            change_color = Fore.GREEN
        elif self == DocItemType._file:
            change_color = Fore.YELLOW
        elif self == DocItemType._class:
            change_color = Fore.RED
        elif self in [DocItemType._function, DocItemType._sub_function, DocItemType._class_method]:
            change_color = Fore.BLUE
        return change_color + self.name + Style.RESET_ALL


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
    parent: Optional[DocItem] = None
    depth: int = 0
    tree_path: List[DocItem] = field(default_factory=list)
    references_from_this: List[DocItem] = field(default_factory=list)
    references_to_this: List[DocItem] = field(default_factory=list)

    has_task: bool = False

    @staticmethod
    def check_and_return_ancestor(doc1: DocItem, doc2: DocItem) -> Union[DocItem, None]:
        """Check and return the common ancestor between two DocItems.

        This function checks if either `doc1` is an ancestor of `doc2` or vice versa.
        If one is an ancestor of the other, it returns the ancestor. Otherwise, it returns None.

        Args:
            doc1 (DocItem): The first DocItem to check.
            doc2 (DocItem): The second DocItem to check.

        Returns:
            Union[DocItem, None]: The common ancestor DocItem if found, otherwise None.
        """
        if doc1 in doc2.tree_path:
            return doc1
        elif doc2 in doc1.tree_path:
            return doc2
        else:
            return None

    @staticmethod
    def need_to_generate(doc_item: DocItem, ignore_list: List[str]) -> bool:
        """
        Check if a document item needs to be generated.

        Args:
            doc_item (DocItem): The document item to check.
            ignore_list (List[str]): A list of paths to ignore.

        Returns:
            bool: True if the document item needs to be generated, False otherwise.
        """
        if (doc_item.item_status == DocItemStatus.doc_upto_date) or (doc_item.item_type in [DocItemType._file, DocItemType._dir, DocItemType._repo]):
            return False

        rel_file_path = doc_item.get_full_name()
        doc_item = doc_item.parent
        while doc_item:
            if doc_item.item_type == DocItemType._file:
                if any(
                    rel_file_path.startswith(ignore_item) for ignore_item in ignore_list
                ):
                    return False
                else:
                    return True
            doc_item = doc_item.parent
        return False

    @staticmethod
    def check_has_task(doc: DocItem, ignore_list: List[str]) -> bool:
        """
        Check if the document item has a task.

        Args:
            doc (DocItem): The document item to check.
            ignore_list (List[str]): A list of items to ignore.

        Returns:
            bool: True if the document item has a task, False otherwise.
        """
        if DocItem.need_to_generate(doc, ignore_list=ignore_list):
            doc.has_task = True
        for child in doc.children.values():
            DocItem.check_has_task(child, ignore_list)
            doc.has_task = child.has_task or doc.has_task

    def get_preorder_traversal(self, _travel_list: Optional[List[DocItem]] = None) -> List[DocItem]:
        """
        Returns a list of `DocItem` objects in preorder traversal.

        Args:
            _travel_list (Union[List[DocItem], None], optional): A list to store the `DocItem` objects. Defaults to None.

        Returns:
            List[DocItem]: A list of `DocItem` objects in preorder traversal.
        """
        if _travel_list is None:
            _travel_list = []
        _travel_list.append(self)
        for child in self.children.values():
            child.get_preorder_traversal(_travel_list)
        return _travel_list

    def calculate_depth(self) -> int:
        """Calculate the depth of the current node in the AST.

        This method calculates the depth of the current node in the Abstract Syntax Tree (AST).
        The depth is defined as the maximum depth of any of the node's children, plus one.

        Returns:
            int: The depth of the current node in the AST.
        """
        if not self.children:
            self.depth = 0
        else:
            self.depth = max(child.calculate_depth()
                             for child in self.children.values()) + 1
        return self.depth

    def parse_tree_path(self, now_path: Optional[List[DocItem]] = None) -> None:
        """
        Parse the tree path for each node in a tree-like structure.

        :param now_path: The current path in the tree.
        """
        if now_path is None:
            now_path = []

        now_path.append(self)
        self.tree_path = list(now_path)
        for child in self.children.values():
            child.parse_tree_path(self.tree_path)
        now_path.pop()

    def get_full_name(self, strict: bool = False) -> str:
        """
        Returns the full name of the current item, including the names of its parent items.

        Args:
            strict (bool, optional): If True, appends "(name_duplicate_version)" to the current item's name if it has a duplicate name within its parent's children. Defaults to False.

        Returns:
            str: The full name of the current item.
        """
        if self.parent is None:
            return self.item_name

        name_list = []
        now = self
        while now is not None:
            self_name = now.item_name
            if strict and any(item == now for item in self.parent.children.values()):
                self_name += "(name_duplicate_version)"
            name_list.insert(0, self_name)
            now = now.parent
        name_list = name_list[1:]
        return "/".join(name_list)

    def get_file_name(self):
        """Returns the file name of the doc_item.

        Returns:
            str: The file name of the current doc_item.
        """
        full_name = self.get_full_name()
        return full_name.split(".py")[0] + ".py"

    def find(self, recursive_file_path: List[str]) -> Optional[DocItem]:
        """
        Search for a file in the repository starting from the root node.

        Args:
            recursive_file_path (List[str]): The list of file paths to search for.

        Returns:
            Optional[DocItem]: The corresponding file if found, otherwise None.

        Raises:
            TypeError: If recursive_file_path is not a list or its elements are not strings.
            ValueError: If recursive_file_path is an empty list or self.item_type is not _repo.
        """
        if not isinstance(recursive_file_path, list):
            raise TypeError("recursive_file_path must be a list of strings.")
        if not all(isinstance(path, str) for path in recursive_file_path):
            raise TypeError(
                "All elements in recursive_file_path must be strings.")
        if not recursive_file_path:
            raise ValueError("recursive_file_path cannot be an empty list.")
        if self.item_type != DocItemType._repo:
            raise ValueError(
                "The method can only be called on a repository root node.")

        pos = 0
        now = self
        while pos < len(recursive_file_path):
            if not recursive_file_path[pos] in now.children:
                return None
            now = now.children[recursive_file_path[pos]]
            pos += 1
        return now

    def print_recursive(self, indent=0, print_content=False, diff_status=False, ignore_list=[]):
        def print_indent(indent=0):
            if indent == 0:
                return ""
            return "  " * indent + "|-"
        print_obj_name = CONFIG["repo_path"]
        if self.item_type == DocItemType._repo:
            print_obj_name = CONFIG["repo_path"]
        if diff_status and self.need_to_generate(self, ignore_list=ignore_list):
            print(
                print_indent(indent) + f"{self.item_type.print_self()
                                          }: {print_obj_name} : {self.item_status.name}",
            )
        else:
            print(
                print_indent(indent) +
                f"{self.item_type.print_self()}: {print_obj_name}",
            )
        for child in self.children.values():
            if diff_status and child.has_task == False:
                continue
            child.print_recursive(indent=indent + 1, print_content=print_content,
                                  diff_status=diff_status, ignore_list=ignore_list)
