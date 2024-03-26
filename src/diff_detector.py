import git
import re
import os
import subprocess
from colorama import Fore, Style
from typing import List, Dict, Any, Optional

from src.config import CONFIG
from src.file_handler import FileHandler


class DiffDetector:

    def __int__(self, repo_path: Optional[str]) -> None:
        if repo_path is None:
            self.repo_path = CONFIG["repo_path"]
        else:
            self.repo_path = repo_path
        self.repo = git.Repo(repo_path)

    # looks the differences between the current head and the stage changes and also tells wether the file is newly added or not

    def get_staged_python_files(self) -> Dict[Optional[str], bool]:
        repo = self.repo
        staged_files = {}
        diffs: git.DiffIndex = repo.index.diff("HEAD", R=True)

        # diff is a git.Diff object
        for diff in diffs:
            if diff.change_type in ["A", "M"] and diff.a_path.endswith(".py"):
                is_new_file = diff.change_type == "A"
                staged_files[diff.a_path] = is_new_file

        return staged_files

    # If the file is new, the get_file_diff method stages that file for commit. It ensures that the
    # newly added file is included in the next commit. On the other hand, if the file is not new (i.e., it has already been committed),
    # the method retrieves the differences between the current version (HEAD) and the previous version of the file

    def get_file_diff(self, file_path: str, is_new_file: bool) -> List[str]:
        repo = self.repo

        if is_new_file:
            add_command = f"git -C {repo.working_dir} add {file_path}"
            subprocess.run(add_command, shell=True, check=True)

            diffs = repo.git.diff("--staged", file_path).splitlines()

        else:
            diffs = repo.git.diff("HEAD", file_path).splitlines()

        return diffs
