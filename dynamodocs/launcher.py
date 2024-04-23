from __future__ import annotations
import threading
import os
import json
import json
import git
import itertools
import shutil
from tqdm import tqdm
from typing import List
from functools import partial
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style
import time

from dynamodocs.file_handler import FileHandler
from dynamodocs.utils.meta_info_utils import latest_verison_substring, make_fake_files, delete_fake_files
from dynamodocs.diff_detector import DiffDetector
from dynamodocs.project_manager import ProjectManager
from dynamodocs.engine import ChatEngine
from dynamodocs.tree_handler import MetaInfo, DocItem, DocItemStatus
from dynamodocs.mylogger import logger
from dynamodocs.config import CONFIG
from dynamodocs.threads import worker


def load_whitelist():
    if CONFIG["whitelist_path"] != None:
        assert os.path.exists(
            CONFIG["whitelist_path"]
        ), f"whitelist_path must be a json-file,and must exists: {CONFIG['whitelist_path']}"
        with open(CONFIG["whitelist_path"], "r") as reader:
            white_list_json_data = json.load(reader)

        return white_list_json_data
    else:
        return None


class Runner:
    def __init__(self, clear: bool = False):
        self.project_manager = ProjectManager(
            repo_path=CONFIG["repo_path"], project_hierarchy=CONFIG["project_hierarchy"]
        )
        self.diff_detector = DiffDetector(repo_path=CONFIG["repo_path"])
        print(self.diff_detector.repo_path)
        self.chat_engine = ChatEngine(CONFIG=CONFIG)

        # if (clear):
        #     if os.path.exists(
        #         os.path.join(CONFIG["repo_path"],
        #                      CONFIG["project_hierarchy"])
        #     ):
        #         shutil.rmtree(
        #             os.path.join(CONFIG["repo_path"],
        #                          CONFIG["project_hierarchy"])
        #         )
        #     if os.path.exists(
        #         os.path.join(CONFIG["repo_path"],
        #                      CONFIG["Markdown_Docs_folder"])):
        #         shutil.rmtree(
        #             os.path.join(CONFIG["repo_path"],
        #                          CONFIG["Markdown_Docs_folder"]))

        if not os.path.exists(
            os.path.join(CONFIG["repo_path"], CONFIG["project_hierarchy"])
        ):
            file_path_reflections, jump_files = make_fake_files()
            self.meta_info = MetaInfo.init_meta_info(
                file_path_reflections, jump_files)
            self.meta_info.checkpoint(
                target_dir_path=os.path.join(
                    CONFIG["repo_path"], CONFIG["project_hierarchy"]
                )
            )
        else:
            self.meta_info = MetaInfo.from_checkpoint_path(
                os.path.join(CONFIG["repo_path"], CONFIG["project_hierarchy"])
            )

        self.meta_info.white_list = load_whitelist()
        self.meta_info.checkpoint(
            target_dir_path=os.path.join(
                CONFIG["repo_path"], CONFIG["project_hierarchy"]
            )
        )
        self.runner_lock = threading.Lock()

    def get_all_pys(self, directory):
        """
        Get all Python files in the given directory.

        Args:
            directory (str): The directory to search.

        Returns:
            list: A list of paths to all Python files.
        """
        python_files = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        return python_files

    def generate_doc_for_a_single_item(self, doc_item: DocItem):
        try:
            rel_file_path = doc_item.get_full_name()

            ignore_list = CONFIG.get("ignore_list", [])
            if not DocItem.need_to_generate(doc_item, ignore_list):
                print(
                    f"Ignored/Document already generated, skipping: {doc_item.get_full_name()}")
            else:
                print(f" -- Generating document {Fore.LIGHTYELLOW_EX}{
                    doc_item.item_type.name}: {doc_item.get_full_name()}{Style.RESET_ALL}")
                file_handler = FileHandler(CONFIG["repo_path"], rel_file_path)
                response_message = self.chat_engine.generate_doc(
                    doc_item=doc_item,
                    file_handler=file_handler,
                )
                doc_item.md_content.append(response_message["content"])
                print(
                    f" -- Document successfully appended: {doc_item.get_full_name()}")
                doc_item.item_status = DocItemStatus.doc_upto_date
                self.meta_info.checkpoint(
                    target_dir_path=os.path.join(
                        CONFIG["repo_path"], CONFIG["project_hierarchy"]
                    )
                )
        except Exception as e:
            logger.info(f"Failed to generate document after multiple attempts, skipping: {
                        doc_item.get_full_name()}")
            logger.info("Error:", e)
            doc_item.item_status = DocItemStatus.doc_has_not_been_generated

    def first_generate(self):
        logger.info("Starting to generate documentation")
        ignore_list = CONFIG.get("ignore_list", [])
        check_task_available_func = partial(
            DocItem.need_to_generate, ignore_list=ignore_list)
        task_manager = self.meta_info.get_topology(
            check_task_available_func
        )
        # topology_list = [item for item in topology_list if DocItem.need_to_generate(item, ignore_list)]
        before_task_len = len(task_manager.task_dict)

        if not self.meta_info.in_generation_process:
            self.meta_info.in_generation_process = True
            logger.info("Init a new task-list")
        else:
            logger.info("Load from an existing task-list")
        self.meta_info.print_task_list(task_manager.task_dict)

        try:
            task_manager.sync_func = self.markdown_refresh
            threads = [
                threading.Thread(
                    target=worker,
                    args=(
                        task_manager,
                        process_id,
                        self.generate_doc_for_a_single_item,
                    ),
                )
                for process_id in range(CONFIG["max_thread_count"])
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.meta_info.document_version = (
                self.diff_detector.repo.head.commit.hexsha
            )
            self.meta_info.in_generation_process = False
            self.meta_info.checkpoint(
                target_dir_path=os.path.join(
                    CONFIG["repo_path"], CONFIG["project_hierarchy"]
                )
            )
            logger.info(
                f"Successfully generated {
                    before_task_len - len(task_manager.task_dict)} documents"
            )

            self.markdown_refresh()
            delete_fake_files()

            logger.info(f"Successfully wrote markdown documents")

        except BaseException as e:
            logger.info(
                f"Finding an error as {e}, {
                    before_task_len - len(task_manager.task_dict)} docs are generated at this time"
            )

    def markdown_refresh(self):
        with self.runner_lock:
            markdown_folder = os.path.join(
                CONFIG["repo_path"], CONFIG["Markdown_Docs_folder"])
            if os.path.exists(markdown_folder):
                shutil.rmtree(markdown_folder)
            os.mkdir(markdown_folder)

            file_item_list = self.meta_info.get_all_files()
            for file_item in tqdm(file_item_list):

                def recursive_check(
                    doc_item: DocItem,
                ) -> bool:
                    if doc_item.md_content != []:
                        return True
                    for _, child in doc_item.children.items():
                        if recursive_check(child):
                            return True
                    return False

                if recursive_check(file_item) == False:
                    continue
                rel_file_path = file_item.get_full_name()

                def to_markdown(item: DocItem, now_level: int) -> str:
                    markdown_content = ""
                    markdown_content += (
                        "#" * now_level +
                        f" {item.item_type.to_str()} {item.item_name}"
                    )
                    if (
                        "params" in item.content.keys()
                        and len(item.content["params"]) > 0
                    ):
                        markdown_content += f"({', '.join(
                            item.content['params'])})"
                    markdown_content += "\n"
                    markdown_content += f"{item.md_content[-1] if len(
                        item.md_content) > 0 else 'Doc is waiting to be generated...'}\n"
                    for _, child in item.children.items():
                        markdown_content += to_markdown(child, now_level + 1)
                        markdown_content += "***\n"

                    return markdown_content

                markdown = ""
                for _, child in file_item.children.items():
                    markdown += to_markdown(child, 2)
                assert markdown != None, f"Markdown content is empty, file path: {
                    rel_file_path}"
                file_path = os.path.join(
                    CONFIG["Markdown_Docs_folder"],
                    file_item.get_file_name().replace(".py", ".md"),
                )
                if file_path.startswith("/"):
                    file_path = file_path[1:]
                abs_file_path = os.path.join(CONFIG["repo_path"], file_path)
                os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
                with open(abs_file_path, "w", encoding="utf-8") as file:
                    file.write(markdown)

            logger.info(
                f"markdown document has been refreshed at {
                    CONFIG['Markdown_Docs_folder']}"
            )

    def git_commit(self, commit_message):
        try:
            subprocess.check_call(
                ["git", "commit", "--no-verify", "-m", commit_message],
                shell=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while trying to commit {str(e)}")

    def run(self):
        """
        Runs the document update process.

        This method detects the changed Python files, processes each file, and updates the documents accordingly.

        Returns:
            None
        """

        if self.meta_info.document_version == "":

            self.first_generate()
            self.meta_info.checkpoint(
                target_dir_path=os.path.join(
                    CONFIG["repo_path"], CONFIG["project_hierarchy"]
                ),
                flash_reference_relation=True,
            )
            return

        if not self.meta_info.in_generation_process:
            logger.info("Starting to detect changes.")

            file_path_reflections, jump_files = make_fake_files()
            new_meta_info = MetaInfo.init_meta_info(
                file_path_reflections, jump_files)
            new_meta_info.load_doc_from_older_meta(self.meta_info)

            self.meta_info = new_meta_info
            self.meta_info.in_generation_process = True

        ignore_list = CONFIG.get("ignore_list", [])
        check_task_available_func = partial(
            DocItem.need_to_generate, ignore_list=ignore_list)

        task_manager = self.meta_info.get_task_manager(
            self.meta_info.target_repo_hierarchical_tree, task_available_func=check_task_available_func)

        for item_name, item_type in self.meta_info.deleted_items_from_older_meta:
            print(f"{Fore.LIGHTMAGENTA_EX}[Dir/File/Obj Delete Dected]: {
                  Style.RESET_ALL} {item_type} {item_name}")
        self.meta_info.print_task_list(task_manager.task_dict)
        if task_manager.all_success:
            logger.info(
                "No tasks in the queue, all documents are completed and up to date.")

        task_manager.sync_func = self.markdown_refresh
        threads = [
            threading.Thread(
                target=worker,
                args=(task_manager, process_id,
                      self.generate_doc_for_a_single_item),
            )
            for process_id in range(CONFIG["max_thread_count"])
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.meta_info.in_generation_process = False
        self.meta_info.document_version = self.diff_detector.repo.head.commit.hexsha

        self.meta_info.checkpoint(
            target_dir_path=os.path.join(
                CONFIG["repo_path"], CONFIG["project_hierarchy"]
            ),
            flash_reference_relation=True,
        )
        logger.info(f"Doc has been forwarded to the latest version")

        self.markdown_refresh()
        delete_fake_files()

        logger.info(f"Starting to git-add DocMetaInfo and newly generated Docs")
        time.sleep(1)

        git_add_result = self.diff_detector.add_unstaged_files()

        if len(git_add_result) > 0:
            logger.info(
                f"Added {[file for file in git_add_result]} to staging area")

    def add_new_item(self, file_handler, json_data):
        """
        Add new projects to the JSON file and generate corresponding documentation.

        Args:
            file_handler (FileHandler): The file handler object for reading and writing files.
            json_data (dict): The JSON data storing the project structure information.

        Returns:
            None
        """
        file_dict = {}
        for (
            structure_type,
            name,
            start_line,
            end_line,
            parent,
            params,
        ) in file_handler.get_functions_and_classes(file_handler.read_file()):
            code_info = file_handler.get_obj_code_info(
                structure_type, name, start_line, end_line, parent, params
            )
            response_message = self.chat_engine.generate_doc(
                code_info, file_handler)
            md_content = response_message.content
            code_info["md_content"] = md_content
            file_dict[name] = code_info

        json_data[file_handler.file_path] = file_dict
        with open(self.project_manager.project_hierarchy, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        logger.info(f"{file_handler.file_path}")
        markdown = file_handler.convert_to_markdown_file(
            file_path=file_handler.file_path
        )
        file_handler.write_file(
            os.path.join(
                self.project_manager.repo_path,
                CONFIG["Markdown_Docs_folder"],
                file_handler.file_path.replace(".py", ".md"),
            ),
            markdown,
        )
        logger.info(f"Markdown documentation for the new file {
                    file_handler.file_path} has been generated.")

    def process_file_changes(self, repo_path, file_path, is_new_file):
        """
        This function is called in the loop of detected changed files. Its purpose is to process changed files according to the absolute file path, including new files and existing files.
        Among them, changes_in_pyfile is a dictionary that contains information about the changed structures. An example format is: {'added': {'add_context_stack', '__init__'}, 'removed': set()}

        Args:
            repo_path (str): The path to the repository.
            file_path (str): The relative path to the file.
            is_new_file (bool): Indicates whether the file is new or not.

        Returns:
            None
        """
        file_handler = FileHandler(
            repo_path=repo_path, file_path=file_path
        )
        source_code = file_handler.read_file()
        changed_lines = self.diff_detector.parse_diffs(
            self.diff_detector.get_file_diff(file_path, is_new_file)
        )
        changes_in_pyfile = self.diff_detector.identify_changes_in_structure(
            changed_lines, file_handler.get_functions_and_classes(source_code)
        )
        logger.info(f"Detected changes in objects:\n{changes_in_pyfile}")

        with open(self.project_manager.project_hierarchy, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        if file_handler.file_path in json_data:
            json_data[file_handler.file_path] = self.update_existing_item(
                json_data[file_handler.file_path], file_handler, changes_in_pyfile
            )
            with open(
                self.project_manager.project_hierarchy, "w", encoding="utf-8"
            ) as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)

            logger.info(f"Updated json structure information for the {
                        file_handler.file_path} file.")

            markdown = file_handler.convert_to_markdown_file(
                file_path=file_handler.file_path
            )
            file_handler.write_file(
                os.path.join(
                    self.project_manager.repo_path,
                    CONFIG["Markdown_Docs_folder"],
                    file_handler.file_path.replace(".py", ".md"),
                ),
                markdown,
            )
            logger.info(f"Updated Markdown documentation for the {
                        file_handler.file_path} file.")

        else:
            self.add_new_item(file_handler, json_data)

        git_add_result = self.diff_detector.add_unstaged_files()

        if len(git_add_result) > 0:
            logger.info(
                f"Added {[file for file in git_add_result]} to the staging area")

        # self.git_commit(f"Update documentation for {file_handler.file_path}")

    def update_existing_item(self, file_dict, file_handler, changes_in_pyfile):
        """
        Update existing projects.

        Args:
            file_dict (dict): A dictionary containing file structure information.
            file_handler (FileHandler): The file handler object.
            changes_in_pyfile (dict): A dictionary containing information about the objects that have changed in the file.

        Returns:
            dict: The updated file structure information dictionary.
        """
        new_obj, del_obj = self.get_new_objects(file_handler)

        for obj_name in del_obj:
            if obj_name in file_dict:
                del file_dict[obj_name]
                logger.info(f"Deleted {obj_name} object.")

        referencer_list = []

        current_objects = file_handler.generate_file_structure(
            file_handler.file_path)

        current_info_dict = {obj["name"]                             : obj for obj in current_objects.values()}

        for current_obj_name, current_obj_info in current_info_dict.items():
            if current_obj_name in file_dict:
                file_dict[current_obj_name]["type"] = current_obj_info["type"]
                file_dict[current_obj_name]["code_start_line"] = current_obj_info[
                    "code_start_line"
                ]
                file_dict[current_obj_name]["code_end_line"] = current_obj_info[
                    "code_end_line"
                ]
                file_dict[current_obj_name]["parent"] = current_obj_info["parent"]
                file_dict[current_obj_name]["name_column"] = current_obj_info[
                    "name_column"
                ]
            else:

                file_dict[current_obj_name] = current_obj_info

        for obj_name, _ in changes_in_pyfile["added"]:
            for current_object in current_objects.values():
                if (
                    obj_name == current_object["name"]
                ):
                    referencer_obj = {
                        "obj_name": obj_name,
                        "obj_referencer_list": self.project_manager.find_all_referencer(
                            variable_name=current_object["name"],
                            file_path=file_handler.file_path,
                            line_number=current_object["code_start_line"],
                            column_number=current_object["name_column"],
                        ),
                    }
                    referencer_list.append(
                        referencer_obj
                    )

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for changed_obj in changes_in_pyfile["added"]:
                for ref_obj in referencer_list:
                    if (
                        changed_obj[0] == ref_obj["obj_name"]
                    ):
                        future = executor.submit(
                            self.update_object,
                            file_dict,
                            file_handler,
                            changed_obj[0],
                            ref_obj["obj_referencer_list"],
                        )
                        print(
                            f"Generating documentation for {Fore.CYAN}{file_handler.file_path}{
                                Style.RESET_ALL}'s {Fore.CYAN}{changed_obj[0]}{Style.RESET_ALL} object."
                        )
                        futures.append(future)

            for future in futures:
                future.result()

        return file_dict

    def update_object(self, file_dict, file_handler, obj_name, obj_referencer_list):
        """
        Generate documentation content and update corresponding field information of the object.

        Args:
            file_dict (dict): A dictionary containing old object information.
            file_handler: The file handler.
            obj_name (str): The object name.
            obj_referencer_list (list): The list of object referencers.

        Returns:
            None
        """
        if obj_name in file_dict:
            obj = file_dict[obj_name]
            response_message = self.chat_engine.generate_doc(
                obj, file_handler, obj_referencer_list
            )
            obj["md_content"] = response_message.content

    def get_new_objects(self, file_handler):
        """
        The function gets the added and deleted objects by comparing the current version and the previous version of the .py file.

        Args:
            file_handler (FileHandler): The file handler object.

        Returns:
            tuple: A tuple containing the added and deleted objects, in the format (new_obj, del_obj)

        Output example:
            new_obj: ['add_context_stack', '__init__']
            del_obj: []
        """
        current_version, previous_version = file_handler.get_modified_file_versions()
        parse_current_py = file_handler.get_functions_and_classes(
            current_version)
        parse_previous_py = (
            file_handler.get_functions_and_classes(previous_version)
            if previous_version
            else []
        )

        current_obj = {f[1] for f in parse_current_py}
        previous_obj = {f[1] for f in parse_previous_py}

        new_obj = list(current_obj - previous_obj)
        del_obj = list(previous_obj - current_obj)
        return new_obj, del_obj


if __name__ == "__main__":

    runner = Runner()

    runner.run()

    logger.info("Documentation task completed.")
