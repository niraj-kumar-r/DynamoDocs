from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, unique, auto
from typing import Any, Dict, List, Optional
from colorama import Fore, Style
from tqdm import tqdm
from functools import partial
import jedi
import os
import json

from src.config import CONFIG
from src.mylogger import logger
from src.file_handler import FileHandler
from src.utils.meta_info_utils import latest_verison_substring
from src.parallel import TaskManager, Task


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

    def to_str(self) -> str:
        if self == DocItemType._class:
            return "ClassDef"
        elif self == DocItemType._class_method or self == DocItemType._function or self == DocItemType._sub_function:
            return "FunctionDef"
        # This shouldn't be called for other types
        # assert False, f"{self.name}"
        return self.name

    def print_self(self) -> None:
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
    reference_who: List[DocItem] = field(default_factory=list)
    who_reference_me: List[DocItem] = field(default_factory=list)
    special_reference_type: List[bool] = field(default_factory=list)

    reference_who_name_list: List[str] = field(default_factory=list)
    who_reference_me_name_list: List[str] = field(default_factory=list)

    has_task: bool = False

    multithread_task_id: int = -1

    @staticmethod
    def check_and_return_ancestor(doc1: DocItem, doc2: DocItem) -> Optional[DocItem]:
        """Check and return the common ancestor between two DocItems.

        This function checks if either `doc1` is an ancestor of `doc2` or vice versa.
        If one is an ancestor of the other, it returns the ancestor. Otherwise, it returns None.

        Args:
            doc1 (DocItem): The first DocItem to check.
            doc2 (DocItem): The second DocItem to check.

        Returns:
            Optional[Docitem]: The common ancestor DocItem if found, otherwise None.
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

    def get_file_name(self) -> str:
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

    def print_recursive(self, indent: int = 0, print_content: bool = False, diff_status: bool = False, ignore_list: List[str] = []) -> None:
        def print_indent(indent=0):
            if indent == 0:
                return ""
            return "  " * indent + "|-"
        if self.item_type == DocItemType._repo:
            print_obj_name = CONFIG["repo_path"]
        else:
            print_obj_name = self.item_name
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


def find_all_referencer(repo_path: str, variable_name, file_path: str, line_number, column_number, in_file_only: bool = False):
    """
    Find all references to a variable in a given repository.

    Args:
        repo_path (str): The path to the repository.
        variable_name: The name of the variable to find references for.
        file_path (str): The path to the file where the variable is defined.
        line_number: The line number where the variable is defined.
        column_number: The column number where the variable is defined.
        in_file_only (bool, optional): If True, only search for references within the same file. Defaults to False.

    Returns:
        list: A list of tuples containing the module path, line number, and column number of each reference.
    """
    file_path = os.path.relpath(file_path, repo_path)
    try:
        script = jedi.Script(path=os.path.join(repo_path, file_path))
        if in_file_only:
            references = script.get_references(
                line=line_number, column=column_number, scope="file")
        else:
            references = script.get_references(
                line=line_number, column=column_number)
        variable_references = [ref for ref in references if ref.name == variable_name
                               and not (ref.line == line_number and ref.column == column_number)]

        return [
            (os.path.relpath(ref.module_path, repo_path), ref.line, ref.column)
            for ref in variable_references
        ]

    except Exception as e:
        logger.error(f"Error in finding references: {e}")
        logger.info(
            f"Parameters : {repo_path}, {variable_name}, {file_path}, {
                line_number}, {column_number}, {in_file_only}"
        )
        return []


@dataclass
class MetaInfo:
    repo_path: str = ""
    document_version: str = (
        ""
    )
    target_repo_hierarchical_tree: DocItem = field(default_factory=DocItem)
    white_list: Any[List] = None
    fake_file_reflection: Dict[str, str] = field(default_factory=dict)
    jump_files: List[str] = field(default_factory=list)
    deleted_items_from_older_meta: List[List] = field(default_factory=list)
    in_generation_process: bool = False

    @staticmethod
    def init_meta_info(file_path_reflections: Dict[str, str], jump_files: List[str]) -> MetaInfo:
        abs_path = CONFIG["repo_path"]
        print(f"{Fore.LIGHTRED_EX}Initializing Metainfo: {
              Style.RESET_ALL} from {abs_path}")
        file_handler = FileHandler(abs_path, None)
        repo_structure = file_handler.generate_overall_structure(
            file_path_reflections, jump_files)
        metainfo = MetaInfo.from_project_hierarchy_json(repo_structure)
        metainfo.repo_path = abs_path
        metainfo.fake_file_reflection = file_path_reflections
        metainfo.jump_files = jump_files
        return metainfo

    @staticmethod
    def from_project_hierarchy_path(repo_path: str) -> MetaInfo:
        project_hierarchy_json_path = os.path.join(
            repo_path, "project_hierarchy.json")
        logger.info(f"parsing from {project_hierarchy_json_path}")
        if not os.path.exists(project_hierarchy_json_path):
            raise NotImplementedError("Invalid operation detected")

        with open(project_hierarchy_json_path, "r", encoding="utf-8") as reader:
            project_hierarchy_json = json.load(reader)
        return MetaInfo.from_project_hierarchy_json(project_hierarchy_json)

    @staticmethod
    def from_project_hierarchy_json(project_hierarchy_json) -> MetaInfo:
        target_meta_info = MetaInfo(
            target_repo_hierarchical_tree=DocItem(
                item_type=DocItemType._repo,
                item_name="full_repo",
            )
        )

        for file_name, file_content in tqdm(project_hierarchy_json.items(), desc="parsing parent relationship"):
            if not os.path.exists(os.path.join(CONFIG["repo_path"], file_name)):
                logger.info(f"deleted content: {file_name}")
                continue
            elif os.path.getsize(os.path.join(CONFIG["repo_path"], file_name)) == 0:
                logger.info(f"blank content: {file_name}")
                continue

            recursive_file_path = file_name.split("/")
            pos = 0
            now_structure = target_meta_info.target_repo_hierarchical_tree
            while pos < len(recursive_file_path) - 1:
                if recursive_file_path[pos] not in now_structure.children.keys():
                    now_structure.children[recursive_file_path[pos]] = DocItem(
                        item_type=DocItemType._dir,
                        md_content="",
                        item_name=recursive_file_path[pos],
                    )
                    now_structure.children[
                        recursive_file_path[pos]
                    ].parent = now_structure
                now_structure = now_structure.children[recursive_file_path[pos]]
                pos += 1
            if recursive_file_path[-1] not in now_structure.children.keys():
                now_structure.children[recursive_file_path[pos]] = DocItem(
                    item_type=DocItemType._file,
                    item_name=recursive_file_path[-1],
                )
                now_structure.children[recursive_file_path[pos]
                                       ].parent = now_structure

            assert type(file_content) == list
            file_item = target_meta_info.target_repo_hierarchical_tree.find(
                recursive_file_path)
            assert file_item.item_type == DocItemType._file

            obj_item_list: List[DocItem] = []
            for value in file_content:
                obj_doc_item = DocItem(
                    item_name=value["name"],
                    content=value,
                    md_content=value["md_content"],
                    code_start_line=value["code_start_line"],
                    code_end_line=value["code_end_line"],
                )
                if "item_status" in value.keys():
                    obj_doc_item.item_status = DocItemStatus[value["item_status"]]
                if "reference_who" in value.keys():
                    obj_doc_item.reference_who_name_list = value["reference_who"]
                if "special_reference_type" in value.keys():
                    obj_doc_item.special_reference_type = value["special_reference_type"]
                if "who_reference_me" in value.keys():
                    obj_doc_item.who_reference_me_name_list = value["who_reference_me"]
                obj_item_list.append(obj_doc_item)

            for item in obj_item_list:
                potential_father = None
                for other_item in obj_item_list:
                    def code_contain(item: DocItem, other_item: DocItem) -> bool:
                        if other_item.code_end_line == item.code_end_line and other_item.code_start_line == item.code_start_line:
                            return False
                        if other_item.code_end_line < item.code_end_line or other_item.code_start_line > item.code_start_line:
                            return False
                        return True
                    if code_contain(item, other_item):
                        if potential_father == None or ((other_item.code_end_line - other_item.code_start_line) < (potential_father.code_end_line - potential_father.code_start_line)):
                            potential_father = other_item

                if potential_father == None:
                    potential_father = file_item
                item.parent = potential_father
                child_name = item.item_name
                if child_name in potential_father.children.keys():
                    now_name_id = 0
                    while (child_name + f"_{now_name_id}") in potential_father.children.keys():
                        now_name_id += 1
                    child_name = child_name + f"_{now_name_id}"
                    logger.warning(f"Name duplicate in {file_item.get_full_name()}: rename to {
                                   item.item_name}->{child_name}")
                potential_father.children[child_name] = item

            def change_items(now_item: DocItem):
                if now_item.item_type != DocItemType._file:
                    if now_item.content["type"] == "ClassDef":
                        now_item.item_type = DocItemType._class
                    elif now_item.content["type"] == "FunctionDef":
                        now_item.item_type = DocItemType._function
                        if now_item.parent.item_type == DocItemType._class:
                            now_item.item_type = DocItemType._class_method
                        elif now_item.parent.item_type in [DocItemType._function, DocItemType._sub_function]:
                            now_item.item_type = DocItemType._sub_function
                for _, child in now_item.children.items():
                    change_items(child)
            change_items(file_item)

        target_meta_info.target_repo_hierarchical_tree.parse_tree_path(
            now_path=[])
        target_meta_info.target_repo_hierarchical_tree.calculate_depth()
        return target_meta_info

    @staticmethod
    def from_project_hierarchy_path(repo_path: str) -> MetaInfo:
        project_hierarchy_json_path = os.path.join(
            repo_path, "project_hierarchy.json")
        logger.info(f"parsing from {project_hierarchy_json_path}")
        if not os.path.exists(project_hierarchy_json_path):
            raise NotImplementedError("Invalid operation detected")

        with open(project_hierarchy_json_path, "r", encoding="utf-8") as reader:
            project_hierarchy_json = json.load(reader)
        return MetaInfo.from_project_hierarchy_json(project_hierarchy_json)

    def get_all_files(self) -> List[DocItem]:
        files = []

        def walk_tree(now_node: DocItem) -> None:
            if now_node.item_type == DocItemType._file:
                files.append(now_node)
            for _, child in now_node.children.items():
                walk_tree(child)

        walk_tree(self.target_repo_hierarchical_tree)
        return files

    def find_obj_with_lineno(self, file_node: DocItem, start_line_num) -> DocItem:
        now_node = file_node
        assert now_node != None
        while len(now_node.children) > 0:
            find_qualify_child = False
            for _, child in now_node.children.items():
                assert child.content != None
                if (
                    child.content["code_start_line"] <= start_line_num
                    and child.content["code_end_line"] >= start_line_num
                ):
                    now_node = child
                    find_qualify_child = True
                    break
            if not find_qualify_child:
                return now_node
        return now_node

    def parse_reference(self):
        file_nodes = self.get_all_files()

        white_list_file_names, white_list_obj_names = (
            [],
            [],
        )
        if self.white_list != None:
            white_list_file_names = [cont["file_path"]
                                     for cont in self.white_list]
            white_list_obj_names = [cont["id_text"]
                                    for cont in self.white_list]

        for file_node in tqdm(file_nodes, desc="parsing bidirectional reference"):
            assert not file_node.get_full_name().endswith(latest_verison_substring)

            ref_count = 0
            rel_file_path = file_node.get_full_name()
            assert rel_file_path not in self.jump_files

            if white_list_file_names != [] and (
                file_node.get_file_name() not in white_list_file_names
            ):
                continue

            def walk_file(now_obj: DocItem):
                nonlocal ref_count, white_list_file_names
                in_file_only = False
                if white_list_obj_names != [] and (
                    now_obj.item_name not in white_list_obj_names
                ):
                    in_file_only = True

                reference_list = find_all_referencer(
                    repo_path=self.repo_path,
                    variable_name=now_obj.item_name,
                    file_path=rel_file_path,
                    line_number=now_obj.content["code_start_line"],
                    column_number=now_obj.content["name_column"],
                    in_file_only=in_file_only,
                )
                for referencer_pos in reference_list:
                    referencer_file_ral_path = referencer_pos[0]
                    if referencer_file_ral_path in self.fake_file_reflection.values():
                        print(
                            f"{Fore.LIGHTBLUE_EX}[Reference From Unstaged Version, skip]{
                                Style.RESET_ALL} {referencer_file_ral_path} -> {now_obj.get_full_name()}"
                        )
                        continue
                    elif referencer_file_ral_path in self.jump_files:
                        print(
                            f"{Fore.LIGHTBLUE_EX}[Reference From Unstracked Version, skip]{
                                Style.RESET_ALL} {referencer_file_ral_path} -> {now_obj.get_full_name()}"
                        )
                        continue

                    target_file_hiera = referencer_file_ral_path.split("/")

                    referencer_file_item = self.target_repo_hierarchical_tree.find(
                        target_file_hiera)
                    if referencer_file_item == None:
                        print(
                            f"{Fore.LIGHTRED_EX}Error: Find \"{referencer_file_ral_path}\"(not in target repo){
                                Style.RESET_ALL} referenced {now_obj.get_full_name()}"
                        )
                        continue
                    referencer_node: DocItem = self.find_obj_with_lineno(
                        referencer_file_item, referencer_pos[1])
                    if referencer_node.item_name == now_obj.item_name:
                        logger.info(
                            f"Jedi find {now_obj.get_full_name(
                            )} with name_duplicate_reference, skipped"
                        )
                        continue

                    if DocItem.check_and_return_ancestor(now_obj, referencer_node) == None:
                        if now_obj not in referencer_node.reference_who:
                            special_reference_type = (referencer_node.item_type in [
                                                      DocItemType._function, DocItemType._sub_function, DocItemType._class_method]) and referencer_node.code_start_line == referencer_pos[1]
                            referencer_node.special_reference_type.append(
                                special_reference_type)
                            referencer_node.reference_who.append(now_obj)
                            now_obj.who_reference_me.append(referencer_node)
                            ref_count += 1
                for _, child in now_obj.children.items():
                    walk_file(child)

            for _, child in file_node.children.items():
                walk_file(child)

    def get_task_manager(self, now_node: DocItem, task_available_func) -> TaskManager:
        doc_items = now_node.get_preorder_traversal()
        if self.white_list != None:

            def in_white_list(item: DocItem):
                for cont in self.white_list:
                    if (
                        item.get_file_name() == cont["file_path"]
                        and item.item_name == cont["id_text"]
                    ):
                        return True
                return False

            doc_items = list(filter(in_white_list, doc_items))
        doc_items = list(filter(task_available_func, doc_items))
        doc_items = sorted(doc_items, key=lambda x: x.depth)
        deal_items = []
        task_manager = TaskManager()
        bar = tqdm(total=len(doc_items), desc="parsing topology task-list")
        while doc_items:
            min_break_level = 1e7
            target_item = None
            for item in doc_items:
                best_break_level = 0
                second_best_break_level = 0
                for _, child in item.children.items():
                    if task_available_func(child) and (child not in deal_items):
                        best_break_level += 1
                for referenced, special in zip(item.reference_who, item.special_reference_type):
                    if task_available_func(referenced) and (referenced not in deal_items):
                        best_break_level += 1
                    if task_available_func(referenced) and (not special) and (referenced not in deal_items):
                        second_best_break_level += 1
                if best_break_level == 0:
                    min_break_level = -1
                    target_item = item
                    break
                if second_best_break_level < min_break_level:
                    target_item = item
                    min_break_level = second_best_break_level

            if min_break_level > 0:
                print(f"circle-reference(second-best still failed), level={
                      min_break_level}: {target_item.get_full_name()}")

            item_denp_task_ids = []
            for _, child in target_item.children.items():
                if child.multithread_task_id != -1:
                    assert child.multithread_task_id in task_manager.task_dict.keys()
                    item_denp_task_ids.append(child.multithread_task_id)

            for referenced_item in target_item.reference_who:
                if referenced_item.multithread_task_id in task_manager.task_dict.keys():
                    item_denp_task_ids.append(
                        referenced_item.multithread_task_id)

            item_denp_task_ids = list(set(item_denp_task_ids))

            if task_available_func == None or task_available_func(target_item):
                task_id = task_manager.add_task(
                    dependency_task_id=item_denp_task_ids, extra=target_item
                )
                target_item.multithread_task_id = task_id

            deal_items.append(target_item)
            doc_items.remove(target_item)
            bar.update(1)

        return task_manager

    def get_topology(self, task_available_func) -> TaskManager:
        self.parse_reference()
        task_manager = self.get_task_manager(
            self.target_repo_hierarchical_tree, task_available_func=task_available_func
        )
        return task_manager


if __name__ == "__main__":
    repo_path = "/home/niraj/stuff/coding/projects/DynamoDocs"
    structure = FileHandler(repo_path, None).generate_overall_structure(
        {}, []
    )
    meta = MetaInfo.from_project_hierarchy_json(structure)
    meta.target_repo_hierarchical_tree.print_recursive()
    check_task_avail = partial(DocItem.need_to_generate, ignore_list=[])
    topology_list: TaskManager = meta.get_topology(check_task_avail)
    print(topology_list)
