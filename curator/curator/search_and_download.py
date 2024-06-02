"""
This module contains the search_and_download command line interface.

The search_and_download command line interface uses google image search to identify images on the
internet that are relevant to the provided search terms. The images are then downloaded and stored
in the image repository. The searches are specified in the manifest.yaml file, which is expected to
be in the root directory of the repository, although it can also be specified by a command line option.

Google image search only allows a limited number of search results per numute (1,200), and also limits
the number of results per search term (100).

Example usage:

    poetry run search \
        --repository-location /mnt/a/data/ott-or-not-image-repository \
        --manifest-location /mnt/a/data/ott-or-not-image-repository/manifest.yaml \
        --number-of-workers 6 \
        --log-level DEBUG
"""

import logging
from pathlib import Path
from typing import Optional

import click
import yaml


class ImageSearchTask(yaml.YAMLObject):
    yaml_tag = "!ImageSearchTask"

    def __init__(
        self, search_term: str, desired_qunatity: int = 100, tags: list[str] = []
    ):
        self.search_term = search_term
        # self.desired_qunatity = desired_qunatity
        self.tags = tags

        if desired_qunatity > 100:
            logging.warning(
                f"Google image search only allows a maximum of 100 results per search term. "
                f"Limiting the number of results for search term '{search_term}' to 100."
            )
            self.desired_qunatity = 100
        else:
            self.desired_qunatity = desired_qunatity

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"search_term={self.search_term}, "
            f"desired_qunatity={self.desired_qunatity}, "
            f"tags={self.tags})"
        )


class Settings(yaml.YAMLObject):
    yaml_tag = "!Settings"

    VALID_SEARCH_PROVIDERS = ["google", "bing"]

    def __init__(
        self,
        search_provider: str = "google",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        rate_limit: Optional[int] = None,
    ):
        if search_provider.lower() not in self.VALID_SEARCH_PROVIDERS:
            raise ValueError(
                f"Invalid search provider '{search_provider}'. "
                f"Valid options are {self.VALID_SEARCH_PROVIDERS}."
            )
        else:
            self.search_provider = search_provider.lower()

        self.api_key = api_key
        self.api_secret = api_secret
        self.rate_limit = rate_limit

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(search_provider={self.search_provider}, rate_limit={self.rate_limit})"
        )


class Manifest(yaml.YAMLObject):
    yaml_tag = "!Manifest"

    def __init__(self, settings: Settings, searches: list[ImageSearchTask]):
        self.settings = settings
        self.searches = searches

    def __repr__(self):
        return f"{self.__class__.__name__}(settings={self.settings}, searches={self.searches})"


def default_manifest_path(
    ctx: click.Context, param: click.Option, value: Optional[Path]
) -> Optional[Path]:
    """
    If the manifest location is not provided, use the repository location to find the manifest.
    """
    if value is not None:
        return value
    repository_location = ctx.params.get("repository_location")
    if repository_location:
        return Path(repository_location) / "shopping-list.yaml"
    return None


@click.command()
@click.option(
    "--repository-location",
    "-r",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="The location of the image repository that the images should be added to.",
)
@click.option(
    "--shopping-list-location",
    "-s",
    type=click.Path(path_type=Path),
    default=None,
    callback=default_manifest_path,
    help="The location of the manifest. Defaults to 'manifest.yaml' in the repository location.",
)
@click.option(
    "--number-of-workers",
    "-n",
    type=int,
    default=6,
    help="The number of worker threads to use.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="The logging level to use.",
)
def main(
    repository_location: Path,
    shopping_list_location: Path,
    number_of_workers: int,
    log_level: str,
) -> None:

    # Set the log level based on the command line option
    logging.basicConfig(level=log_level)

    with shopping_list_location.open("r") as f:
        shopping_list = yaml.load(f, Loader=yaml.Loader)

    logging.info(f"Loaded manifest containing {len(shopping_list.searches)} searches.")

    logging.debug("===============================\n")
    logging.debug(shopping_list)
    logging.debug("===============================\n")