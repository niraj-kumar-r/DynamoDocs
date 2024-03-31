import os
import git
import itertools
from colorama import Fore, Style
from typing import List, Dict

from dynamodocs.config import CONFIG
from dynamodocs.mylogger import logger

latest_verison_substring = "_latest_version.py"


def make_fake_files():
    delete_fake_files()

    repo = git.Repo(CONFIG["repo_path"])
    unstaged_changes = repo.index.diff(None)
    untracked_files = repo.untracked_files
    jump_files: List[str] = []

    for file_name in untracked_files:
        if file_name.endswith(".py"):
            print(f"{Fore.LIGHTMAGENTA_EX}[SKIP untracked files]: {
                  Style.RESET_ALL}{file_name}")
            jump_files.append(file_name)

    for diff_file in unstaged_changes.iter_change_type('A'):
        if diff_file.a_path.endswith(latest_verison_substring):
            logger.error(
                "FAKE_FILE_IN_GIT_STATUS detected! suggest to use `delete_fake_files` and re-generate document")
            exit()
        jump_files.append(diff_file.a_path)

    file_path_reflections: Dict[str, str] = {}

    for diff_file in itertools.chain(unstaged_changes.iter_change_type('M'), unstaged_changes.iter_change_type('D')):
        if diff_file.a_path.endswith(latest_verison_substring):
            logger.error(
                "FAKE_FILE_IN_GIT_STATUS detected! suggest to use `delete_fake_files` and re-generate document")
            exit()

        now_file_path = diff_file.a_path

        if now_file_path.endswith(".py"):
            raw_file_content = diff_file.a_blob.data_stream.read().decode("utf-8")
            latest_file_path = now_file_path[:-3] + latest_verison_substring
            if os.path.exists(os.path.join(CONFIG["repo_path"], now_file_path)):
                os.rename(os.path.join(CONFIG["repo_path"], now_file_path), os.path.join(
                    CONFIG["repo_path"], latest_file_path))

                print(f"{Fore.LIGHTMAGENTA_EX}[Save Latest Version of Code]: {
                      Style.RESET_ALL}{now_file_path} -> {latest_file_path}")
            else:
                print(f"{Fore.LIGHTMAGENTA_EX}[Create Temp-File for Deleted(But not Staged) Files]: {
                      Style.RESET_ALL}{now_file_path} -> {latest_file_path}")
                with open(os.path.join(CONFIG["repo_path"], latest_file_path), "w") as writer:
                    pass
            with open(os.path.join(CONFIG["repo_path"], now_file_path), "w") as writer:
                writer.write(raw_file_content)
            file_path_reflections[now_file_path] = latest_file_path

    return file_path_reflections, jump_files


def delete_fake_files():
    def gci(filepath):
        files = os.listdir(filepath)
        for fi in files:
            fi_d = os.path.join(filepath, fi)
            if os.path.isdir(fi_d):
                gci(fi_d)
            elif fi_d.endswith(latest_verison_substring):
                origin_name = fi_d.replace(latest_verison_substring, ".py")
                os.remove(origin_name)
                if os.path.getsize(fi_d) == 0:
                    print(f"{Fore.LIGHTRED_EX}[Deleting Temp File]: {Style.RESET_ALL}{
                          fi_d[len(CONFIG['repo_path']):]}, {origin_name[len(CONFIG['repo_path']):]}")
                    os.remove(fi_d)
                else:
                    print(f"{Fore.LIGHTRED_EX}[Recovering Latest Version]: {Style.RESET_ALL}{
                          origin_name[len(CONFIG['repo_path']):]} <- {fi_d[len(CONFIG['repo_path']):]}")
                    os.rename(fi_d, origin_name)

    gci(CONFIG["repo_path"])
