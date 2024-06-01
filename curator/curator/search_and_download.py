"""
This module contains the search_and_download command line interface.

The search_and_download command line interface uses google image search to identify images on the
internet that are relevant to the provided search terms. The images are then downloaded and stored
in the image repository. The searches are specified in the manifest.yaml file, which is expected to
be in the root directory of the repository, although it can also be specified by a command line option.

Google image search only allows a limited number of search results per numute (1,200), and also limits
the number of results per search term (100).
"""

import click
from pathlib import Path


@click.command()
@click.option(
    "--repository-location",
    "-r",
    type=click.Path(),
    default=Path.cwd(),
    help="The location of the image repository that the images should be added to.",
)
@click.option(
    "--number-of-workers",
    "-n",
    type=int,
    default=6,
    help="The number of worker threads to use.",
)
@click.option(
    "--manifest-location",
    "-m",
    type=click.Path(),
    default=Path.cwd() / "manifest.yaml",
    help="The location of the manifest file that specifies the search terms.",
)
def main(
    repository_location: Path,
    number_of_workers: int,
    manifest_location: Path,
) -> None:
    pass
