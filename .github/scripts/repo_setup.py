#!/usr/bin/env python3
import logging
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

HELM_REPOS = {
    "altinity": "https://helm.altinity.com",
    # "bitnami": "https://charts.bitnami.com/bitnami",
}


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    if result.stdout:
        logger.debug(result.stdout.strip())


def add_repos(repos: dict[str, str]) -> None:
    logger.info("Adding Helm repositories...")
    for name, url in repos.items():
        logger.info(f"  Adding {name} -> {url}")
        run(["helm", "repo", "add", name, url])


def update_repos() -> None:
    logger.info("Updating Helm repositories...")
    run(["helm", "repo", "update"])


def main() -> None:
    try:
        add_repos(HELM_REPOS)
        update_repos()
        logger.info("Helm repositories configured successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(e.cmd)}\n{e.stderr.strip()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
