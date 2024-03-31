import os
import jedi


class ProjectManager:
    def __init__(self, repo_path, project_hierarchy):
        self.repo_path = repo_path
        self.project = jedi.Project(self.repo_path)
        self.project_hierarchy = os.path.join(
            self.repo_path, project_hierarchy, "project_hierarchy.json"
        )

    def get_project_structure(self):
        """
        Returns the structure of the project by recursively walking through the directory tree.

        Returns:
            str: The project structure as a string.
        """
        def walk_dir(root, prefix=""):
            structure.append(prefix + os.path.basename(root))
            new_prefix = prefix + "    "
            for name in sorted(os.listdir(root)):
                if name.startswith("."):
                    continue
                path = os.path.join(root, name)
                if os.path.isdir(path):
                    walk_dir(path, new_prefix)
                elif os.path.isfile(path) and name.endswith(".py"):
                    structure.append(new_prefix + name)

        structure = []
        walk_dir(self.repo_path)
        return "\n".join(structure)


if __name__ == "__main__":
    project_manager = ProjectManager(repo_path="./", project_hierarchy="")
    print(project_manager.get_project_structure())
