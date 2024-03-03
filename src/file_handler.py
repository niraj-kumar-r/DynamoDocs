import os

from src.config import CONFIG


class FileHandler:
    def __init__(self, repo_path, file_path):
        self.file_path = file_path  # 这里的file_path是相对于仓库根目录的路径
        self.repo_path = repo_path
        self.project_hierarchy = os.path.join(
            repo_path, CONFIG["project_hierarchy"], "project_hierarchy.json"
        )
