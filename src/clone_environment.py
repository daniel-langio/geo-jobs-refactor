#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path

from src.cli import run_cmd
from src.rename_environment import update_environment_name


REMOTE_GEO_JOBS_CENTRAL = "git@github.com:b-partners/geo-jobs.git"
DEFAULT_BRANCH = "prod"


def clone_repository(dest_dir: Path):
    """
    Clone the git repository into the destination folder.
    """
    print(f"[INFO] Cloning repository into: {dest_dir}")

    run_cmd([
        "git", "clone",
        "--depth", "1",
        "--branch", DEFAULT_BRANCH,
        REMOTE_GEO_JOBS_CENTRAL,
        str(dest_dir)
    ])

    print("[INFO] Repository cloned successfully.")


def checkout_branch(dest_dir: Path):
    """
    Checkout or create the prod branch in the cloned repo.
    """
    print("[INFO] Switching to the prod branch...")
    run_cmd(["git", "checkout", "-B", DEFAULT_BRANCH], cwd=dest_dir)


def parse_arguments():
    """
    Parse CLI arguments using argparse, including the destination directory.
    """
    parser = argparse.ArgumentParser(
        description="Clone geo-jobs repository into a specified environment directory."
    )

    parser.add_argument(
        "-n", "--name",
        help="Name of the environment",
    )

    # positional env_name
    parser.add_argument(
        "env_name",
        nargs="?",
        help="Environment name (positional argument)",
    )

    # optional destination directory
    parser.add_argument(
        "-d", "--dest",
        type=Path,
        help="Destination directory in which the environment folder will be created",
    )

    # Optional second positional arg for destination (more flexible)
    parser.add_argument(
        "dest_dir",
        nargs="?",
        type=Path,
        help="Destination directory (positional alternative)",
    )

    args = parser.parse_args()

    # Determine env name
    env_name = args.name or args.env_name
    if not env_name:
        parser.error("ENV_NAME is required (via -n or positional argument).")

    # Determine destination directory
    dest_root = args.dest or args.dest_dir or Path.cwd()

    return env_name, Path(dest_root)


def main():
    env_name, dest_root = parse_arguments()

    # final path = dest_root / env_name
    dest_dir = dest_root / env_name

    clone_repository(dest_dir)
    checkout_branch(dest_dir)
    update_environment_name(dest_dir, env_name)

    print(f"[SUCCESS] Environment '{env_name}' setup completed in: {dest_dir}")


if __name__ == "__main__":
    main()
