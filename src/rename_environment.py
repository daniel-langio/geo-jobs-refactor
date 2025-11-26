from pathlib import Path

def update_environment_name (project_root: Path, project_environment_name: str):
    pass

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="b-partners/geo-jobs project renamer")

    parser.add_argument("--env-name",  "-n", dest="env_name", type=str, help="New name to use")
    parser.add_argument("--project-root", "-p", dest="project_root", type=str, help="Path of the project to rename")

    args = parser.parse_args()

    env_name = args.env_name
    project_root = args.project_root

    update_environment_name(project_root, env_name)
