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
        --concurrent-downloads 3 \
        --log-level INFO
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from typing import Optional

import click
from googleapiclient.discovery import build
import requests
from tqdm import tqdm
import yaml
from PIL import Image
from requests.exceptions import (
    ConnectionError,
    ConnectTimeout,
    ReadTimeout,
    SSLError,
    HTTPError,
)

from curator.image_repository import FileSystemImageRepository, ImageRepository


# ========== YAML Classes ==========
class ImageSearchTask(yaml.YAMLObject):
    yaml_tag = "!ImageSearchTask"

    def __init__(
        self, search_term: str, desired_quantity: int = 100, tags: list[str] = []
    ):
        self.search_term = search_term
        self.desired_quantity = desired_quantity
        self.tags = tags

        if desired_quantity > 100:
            logging.warning(
                f"Google image search only allows a maximum of 100 results per search term. "
                f"Limiting the number of results for search term '{search_term}' to 100."
            )
            self.desired_quantity = 100
        else:
            self.desired_quantity = desired_quantity

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"search_term={self.search_term}, "
            f"desired_quantity={self.desired_quantity}, "
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


# ========== Helper Classes ==========


class DownloadImageTask:

    def __init__(
        self,
        repository: ImageRepository,
        image_url: str,
        search_term: str = None,
        tags: list[str] = [],
        on_finished_callback: Optional[callable] = None,
    ):
        self.repository = repository
        self.image_url = image_url
        self.search_term = search_term
        self.tags = tags
        self.on_finished_callback = on_finished_callback

    def __call__(self):
        try:
            response = requests.get(self.image_url, timeout=5)
            response.raise_for_status()
        except (ConnectTimeout, ConnectionError, HTTPError) as e:
            logging.error(f"Connection error for {self.image_url}: {e}")
            return
        except ReadTimeout as e:
            logging.error(f"Read timeout for {self.image_url}: {e}")
            return
        except SSLError as e:
            logging.error(f"SSL error for {self.image_url}: {e}")
            return

        image = Image.open(BytesIO(response.content))
        self.repository.save_image(image, self.search_term, self.tags)

        if self.on_finished_callback:
            self.on_finished_callback()


# ========== Command Line Interface ==========
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
    "--concurrent-downloads",
    "-c",
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
    concurrent_downloads: int,
    log_level: str,
) -> None:

    # Set the log level based on the command line option
    logging.basicConfig(level=log_level)

    with shopping_list_location.open("r") as f:
        shopping_list: Manifest = yaml.load(f, Loader=yaml.Loader)

    logging.info(
        f"Loaded shopping list containing {len(shopping_list.searches)} searches."
    )
    logging.debug("===============================\n")
    logging.debug(shopping_list)
    logging.debug("===============================\n")

    # Instantiate the Google search service and the image repository
    repository = FileSystemImageRepository(repository_location)
    service = build("customsearch", "v1", developerKey=shopping_list.settings.api_key)

    # Prep progress bar
    estimated_total_images = sum(
        search.desired_quantity for search in shopping_list.searches
    )
    progress_bar = tqdm(total=estimated_total_images, desc="Downloading images")

    def callback_update_progress_bar():
        progress_bar.update(1)

    # Execute searches and submit tasks for download
    with ThreadPoolExecutor(max_workers=concurrent_downloads) as executor:
        search_results = list()
        for search_request in shopping_list.searches:
            query_index = 0
            while query_index < search_request.desired_quantity:

                # Limit batch size to 10 at a time
                remaining_results = search_request.desired_quantity - query_index
                batch_size = remaining_results if remaining_results < 10 else 10

                query_result = (
                    service.cse()
                    .list(
                        q=search_request.search_term,
                        cx=shopping_list.settings.api_secret,
                        searchType="image",
                        num=batch_size,
                        start=query_index,
                    )
                    .execute()
                )

                for item in query_result["items"]:
                    query_index += 1

                    # Submit the task to our parallel executor, and save the future to
                    # the results list.
                    search_results.append(
                        executor.submit(
                            DownloadImageTask(
                                repository=repository,
                                image_url=item["link"],
                                search_term=search_request.search_term,
                                tags=search_request.tags,
                                on_finished_callback=callback_update_progress_bar,
                            )
                        )
                    )

        # Wait for all tasks to complete
        number_downloaded = 0
        for future in as_completed(search_results):
            future.result()
            number_downloaded += 1

        logging.info(f"Downloaded {number_downloaded} images.")
        progress_bar.close()
