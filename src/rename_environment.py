from pathlib import Path

from src.template.template import Template
from .template.blueprints import poja_config_blueprints


def replace_content(file_path: Path, new_content: str):
    """
    Replace the entire content of a file with `new_content`.

    Args:
        file_path (Path): Path to the file to modify.
        new_content (str): New content to write to the file.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    if not file_path.is_file():
        raise ValueError(f"{file_path} is not a file.")

    # Write the new content
    file_path.write_text(new_content, encoding="utf-8")
    print(f"Content replaced for {file_path}")

def update_environment_name (gj_project_root: Path, project_environment_name: str):

    for key in poja_config_blueprints.keys():
        filename = key
        blueprint = poja_config_blueprints[key]

        filepath = gj_project_root / filename
        file_content = Template.build_template(blueprint, {'geo-jobs_env': project_environment_name})

        replace_content(filepath, file_content)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="b-partners/geo-jobs project renamer")

    parser.add_argument("--env-name",  "-n", dest="env_name", type=str, help="New name to use")
    parser.add_argument("--project-root", "-p", dest="gj_project_root", type=str, help="Path of the geo-jobs project to rename")

    args = parser.parse_args()

    env_name = args.env_name
    project_root = Path(args.gj_project_root)

    update_environment_name(project_root, env_name)
