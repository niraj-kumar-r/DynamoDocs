import git
import re
import os
import subprocess
from colorama import Fore, Style
from typing import List, Dict, Any, Optional

from dynamodocs.config import CONFIG
from dynamodocs.file_handler import FileHandler


class DiffDetector:

    def __init__(self, repo_path: Optional[str] = None) -> None:
        if repo_path is None:
            self.repo_path = CONFIG["repo_path"]
        else:
            self.repo_path = repo_path
        self.repo = git.Repo(repo_path)

    def get_staged_python_files(self) -> Dict[Optional[str], bool]:
        """looks the differences between the current head and the stage changes and also tells wether the file is newly added or not

        Returns:
            Dict[Optional[str], bool]
        """
        repo = self.repo
        staged_files = {}
        diffs: git.DiffIndex = repo.index.diff("HEAD", R=True)

        # diff is a git.Diff object
        for diff in diffs:
            diff: git.Diff = diff
            if diff.change_type in ["A", "M"] and diff.a_path.endswith(".py"):
                is_new_file = diff.change_type == "A"
                staged_files[diff.a_path] = is_new_file

        return staged_files

    def get_file_diff(self, file_path: str, is_new_file: bool) -> List[str]:
        """If the file is new, the get_file_diff method stages that file for commit. It ensures that the 
        newly added file is included in the next commit. On the other hand, if the file is not new (i.e., it has already been committed),
        the method retrieves the differences between the current version (HEAD) and the previous version of the file

        Args:
            file_path (str)
            is_new_file (bool)

        Returns:
            List[str]
        """
        repo = self.repo

        if is_new_file:
            add_command = f"git -C {repo.working_dir} add {file_path}"
            subprocess.run(add_command, shell=True, check=True)

            diffs = repo.git.diff("--staged", file_path).splitlines()

        else:
            diffs = repo.git.diff("HEAD", file_path).splitlines()

        return diffs

    def parse_diffs(self, diffs: List[str]) -> Dict[str, List[str]]:
        changed_lines = {"added": [], "removed": []}
        line_number_current = 0
        line_number_change = 0

        for line in diffs:
            line_number_info = re.match(r"@@ \-(\d+),\d+ \+(\d+),\d+ @@", line)
            if line_number_info:
                line_number_current = int(line_number_info.group(1))
                line_number_change = int(line_number_info.group(2))
                continue

            if line.startswith("+") and not line.startswith("+++"):
                changed_lines["added"].append((line_number_change, line[1:]))
                line_number_change += 1
            elif line.startswith("-") and not line.startswith("---"):
                changed_lines["removed"].append(
                    (line_number_current, line[1:]))
                line_number_current += 1
            else:
                line_number_current += 1
                line_number_change += 1

        return changed_lines

    def identify_changes_in_structure(self, changed_lines: Dict[str, List[tuple]], structures: List[tuple]) -> Dict[str, set]:
        """
        Identify the structure of the function or class where changes have occurred: Traverse all changed lines, for each line, it checks whether this line is between the start line and the end line of a structure (function or class).
        If so, then this structure is considered to have changed, and its name and the name of the parent structure are added to the corresponding set in the result dictionary changes_in_structures (depending on whether this line is added or deleted).

        Output example: {'add List[Tuple[str, str, int, int, List[str]]]ed': {('PipelineAutoMatNode', None), ('to_json_new', 'PipelineAutoMatNode')}, 'removed': set()}

        Args:
            changed_lines (dict): A dictionary containing the line numbers where changes have occurred, {'added': [(line number, change content)], 'removed': [(line number, change content)]}
            structures (list): The received is a list of function or class structures from get_functions_and_classes, each structure is composed of structure type, name, start line number, end line number, and parent structure name.

        Returns:
            dict: A dictionary containing the structures where changes have occurred, the key is the change type, and the value is a set of structure names and parent structure names.
                Possible change types are 'added' (new) and 'removed' (removed).
        """
        changes_in_structures = {"added": set(), "removed": set()}
        for change_type, lines in changed_lines.items():
            for line_number, _ in lines:
                for (
                    structure_type,
                    name,
                    start_line,
                    end_line,
                    parent_structure,
                ) in structures:
                    if start_line <= line_number <= end_line:
                        changes_in_structures[change_type].add(
                            (name, parent_structure))
        return changes_in_structures

    def get_to_be_staged_files(self) -> List[str]:
        """This method retrieves all unstaged files in the repository that meet one of the following conditions:
        1. The file, when its extension is changed to .md, corresponds to a file that is already staged.
        2. The file's path is the same as the 'project_hierarchy' field in the CONFIG.

        It returns a list of the paths of these files.

        Returns:
            List[str]
        """
        to_be_staged_files = []
        staged_files = [item.a_path for item in self.repo.index.diff("HEAD")]
        print(f"{Fore.LIGHTYELLOW_EX}target_repo_path{
              Style.RESET_ALL}: {self.repo_path}")
        print(f"{Fore.LIGHTMAGENTA_EX}already_staged_files{
              Style.RESET_ALL}:{staged_files}")

        project_hierarchy = CONFIG["project_hierarchy"]
        diffs = self.repo.index.diff(None)
        untracked_files = self.repo.untracked_files
        print(f"{Fore.LIGHTCYAN_EX}untracked_files{
              Style.RESET_ALL}: {untracked_files}")

        for untracked_file in untracked_files:
            if untracked_file.startswith(CONFIG["Markdown_Docs_folder"]):
                to_be_staged_files.append(untracked_file)
            continue

        unstaged_files = [diff.b_path for diff in diffs]
        print(f"{Fore.LIGHTCYAN_EX}unstaged_files{
              Style.RESET_ALL}: {unstaged_files}")

        for unstaged_file in unstaged_files:
            if unstaged_file.startswith(CONFIG["Markdown_Docs_folder"]):
                to_be_staged_files.append(unstaged_file)
            elif unstaged_file == project_hierarchy:
                to_be_staged_files.append(unstaged_file)
            continue
        print(f"{Fore.LIGHTRED_EX}newly_staged_files{
              Style.RESET_ALL}: {to_be_staged_files}")
        return to_be_staged_files

    def add_unstaged_files(self):
        """
        Add unstaged files which meet the condition to the staging area.
        """
        unstaged_files_meeting_conditions = self.get_to_be_staged_files()
        for file_path in unstaged_files_meeting_conditions:
            add_command = f'git -C {self.repo.working_dir} add {file_path}'
            subprocess.run(add_command, shell=True, check=True)
        return unstaged_files_meeting_conditions
