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
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, Optional

import requests
import yaml
from googleapiclient.discovery import build
from PIL import Image, UnidentifiedImageError
from requests.exceptions import (
    ConnectionError,
    ConnectTimeout,
    HTTPError,
    ReadTimeout,
    SSLError,
)
from tqdm import tqdm

from curator.image_repository import FileSystemImageRepository, ImageRepository
from curator.repo_utilities import ImageSearchRequest, Settings, ShoppingList


@dataclass(frozen=True)
class ImageDownloadResult:
    succeeded: bool
    reason: Optional[str] = None
    url: Optional[str] = None


class ImageDownloadTask:

    def __init__(
        self,
        repository: ImageRepository,
        image_url: str,
        search_term: str = None,
        tags: list[str] = [],
        on_finished_callback: Optional[Callable[[ImageDownloadResult], None]] = None,
    ):
        """
        A class to represent the task of downloading an image from a URL and adding it to the repository.

        The on_finished_callback parameter is a callback function that will be called when the task is
        complete or an error is raised. It takes a single parameter, which is the ImageDownloadResult
        that will be returned from the function.

        :param repository:  The image repository to add the image to.
        :param image_url:  The URL of the image to download.
        :param search_term:  The search term used to find the image.
        :param tags:  A list of tags to associate with the image.
        :param on_finished_callback:  A callback function to call when all work is done.
        """
        self.repository = repository
        self.image_url = image_url
        self.search_term = search_term
        self.tags = tags
        self.on_finished_callback = on_finished_callback

    def __call__(self):
        try:
            response = requests.get(self.image_url, timeout=5)
            response.raise_for_status()
        except (ConnectTimeout, ConnectionError, HTTPError, ReadTimeout, SSLError) as e:
            result = ImageDownloadResult(
                succeeded=False, reason=e.__class__.__name__, url=self.image_url
            )
            if self.on_finished_callback:
                self.on_finished_callback(result)
            return result

        try:
            image = Image.open(BytesIO(response.content))
        except UnidentifiedImageError as e:
            result = ImageDownloadResult(
                succeeded=False, reason=e.__class__.__name__, url=self.image_url
            )
            if self.on_finished_callback:
                self.on_finished_callback(result)
            return result

        self.repository.save_image(image, self.search_term, self.tags)

        result = ImageDownloadResult(succeeded=True, url=self.image_url)
        if self.on_finished_callback:
            self.on_finished_callback(result)

        return result


def main(
    repository_location: Path,
    shopping_list_location: Path,
    concurrent_downloads: int,
    log_level: str,
) -> None:

    # Set the log level based on the command line option
    logging.basicConfig(level=log_level)

    with shopping_list_location.open("r") as f:
        shopping_list: ShoppingList = yaml.load(f, Loader=yaml.Loader)

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

    def callback_update_progress_bar(result: ImageDownloadResult):
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
                            ImageDownloadTask(
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
        failed_results = []
        for future in as_completed(search_results):
            result = future.result()
            if result.succeeded:
                number_downloaded += 1
            else:
                failed_results.append(result)

        # Complete notifications after everything is done.
        progress_bar.close()
        logging.info(f"Downloaded {number_downloaded} images.")

        # Log any failed downloads
        if failed_results:
            logging.warning(
                f"Failed to download {len(failed_results)} images. The URLs are:"
            )
            for result in failed_results:
                logging.warning(
                    f"Failed to download image from {result.url}. Reason: {result.reason}"
                )
