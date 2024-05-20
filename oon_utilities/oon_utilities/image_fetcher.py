from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path, PurePath
from typing import Optional

import click
import requests
from googleapiclient.discovery import build
from requests.exceptions import ConnectTimeout, ConnectionError, ReadTimeout, SSLError
from tqdm import tqdm
from urllib3.util import parse_url

from oon_utilities.configuration import (
    GOOGLE_CUSTOM_SEARCH_API_KEY,
    GOOGLE_CUSTOM_SEARCH_ENGINE_ID,
)

TRUST_ANYWAY = [
    "www.nwf.org",
]


@dataclass(frozen=True)
class ImageSearchRequest:
    search_term: str
    label_category: str
    quantity: int


@dataclass(frozen=True)
class ImageSearchResult:
    search_term: str
    label_category: str
    image_url: str


class ImageDownloadResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    FAILED_SSL_ERROR = "SSLError"
    FAILED_READ_TIMEOUT = "ReadTimeout"
    FAILED_CONNECTION_TIMEOUT = "ConnectionTimeout"
    FAILED_CONNECTION_ERROR = "ConnectionError"


def quick_image_search(
    search_request: ImageSearchRequest,
    api_key: str = GOOGLE_CUSTOM_SEARCH_API_KEY,
    csi_id: str = GOOGLE_CUSTOM_SEARCH_ENGINE_ID,
    **kwargs,
) -> list[str]:
    """
    Performs a Google Custom Search for images based on the provided search term.

    :param search_request:  ImageSearchRequest object containing information about the search.
    :param api_key:  The Google API key to use for the search.
    :param csi_id:  The Custom Search Engine ID to use for the search.
    :return:  A list of ImageSearchResult objects containing the search results.
    """
    service = build("customsearch", "v1", developerKey=api_key)
    results = list()
    query_index = 0

    # Note: we are tracking the query_index separately from the number of results
    # actually produced.
    while len(results) < search_request.quantity:
        expected_results_required = search_request.quantity - len(results)
        batch_size = expected_results_required if expected_results_required < 10 else 10

        query_result = (
            service.cse()
            .list(
                q=search_request.search_term,
                cx=csi_id,
                searchType="image",
                num=batch_size,
                start=query_index,
                **kwargs,
            )
            .execute()
        )

        results.extend(
            [
                ImageSearchResult(
                    search_term=search_request.search_term,
                    label_category=search_request.label_category,
                    image_url=item["link"],
                )
                for item in query_result["items"]
            ]
        )
        query_index += batch_size

    return results


def download_and_store_image(
    search_result: ImageSearchResult,
    destination_directory_path: Path,
    skip_existing_images: bool = True,
    timeout: int = 8,
    **kwargs,
) -> Optional[ImageSearchResult]:
    """
    Downloads an image from a URL and stores it at the provided destination path.

    :param image_url:  The URL of the image to download.
    :param destination_path:  The path to store the downloaded image.
    :param kwargs:  Additional keyword arguments to pass to the requests.get function.
    :return:  The ImageSearchResult together with its ImageDownloadResult.
    """
    url_parts = parse_url(search_result.image_url)
    image_remote_path = PurePath(url_parts.path)
    destination_path = (
        destination_directory_path
        / search_result.label_category
        / image_remote_path.name
    )
    # If the file already exists, skip this image to avoid fetching it from the internet again.
    if skip_existing_images and destination_path.exists():
        return (search_result, ImageDownloadResult.SUCCESS)

    try:
        response = requests.get(search_result.image_url, timeout=timeout, **kwargs)
    except (ConnectionError, ConnectTimeout, ReadTimeout, SSLError) as e:
        failed_reason = ImageDownloadResult(e.__class__.__name__)
        return (search_result, failed_reason)

    if response.status_code == 200:
        with destination_path.open("wb") as f:
            f.write(response.content)
        return (search_result, ImageDownloadResult.SUCCESS)
    return (search_result, ImageDownloadResult.FAILED)


@click.command
@click.option(
    "--download-path",
    type=click.Path(exists=True),
    default=Path("/mnt/a/data/ott-or-not").expanduser(),
)
@click.option("--concurrent-downloads", type=int, default=12)
def main(download_path: Path, concurrent_downloads: int):

    # NOTE: Google Image search API will not return more than 100 results for a given
    # search term. There is also a limit of 1,200 results per minute before you get
    # a 400 status code indicating you've exceeded the limit.

    # Ensure we have the necessary configuration
    assert GOOGLE_CUSTOM_SEARCH_API_KEY
    assert GOOGLE_CUSTOM_SEARCH_ENGINE_ID

    # Search for some images of various different otter species
    otter_searches = [
        # ImageSearchRequest(
        #     "North American River Otter", "north_american_river_otter", 100
        # ),
        # ImageSearchRequest("Sea Otter", "sea_otter", 100),
        # ImageSearchRequest("Asian Small Clawed Otter", "asian_small_clawed_otter", 100),
        # ImageSearchRequest("Giant Otter", "giant_otter", 100),
        ImageSearchRequest("Eurasian River Otter", "eurasian_river_otter", 100),
    ]

    # Add some non-otter images for the "not otter" category
    non_otter_searches = [
        # ImageSearchRequest("Beaver", "beaver", 100),
        # ImageSearchRequest("Platypus", "platypus", 100),
        # ImageSearchRequest("Muskrat", "muskrat", 100),
        # ImageSearchRequest("Mink", "mink", 100),
        ImageSearchRequest("Raccoon", "raccoon", 100),
    ]
    searches = otter_searches + non_otter_searches

    failed_downloads = list()
    for search in searches:

        # Perform the search
        print(f"Performing image search for {search.search_term}.")
        search_results = quick_image_search(search)

        print(f"Downloading images for {search.search_term}.")
        search_results_directory = download_path / search.label_category
        search_results_directory.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=concurrent_downloads) as executor:
            results = list(
                tqdm(
                    executor.map(
                        download_and_store_image,
                        search_results,
                        [download_path] * len(search_results),
                    ),
                    total=len(search_results),
                )
            )

            # Log any failed downloads
            failed_downloads.extend(
                [
                    (r, reason)
                    for r, reason in results
                    if reason != ImageDownloadResult.SUCCESS
                ]
            )

    # Write a report of failed downloads into the download directory
    failed_downloads_report_path = (
        download_path / f"failed_downloads_{datetime.now()}.txt"
    )

    print(f"Writing a report of failed downloads to {failed_downloads_report_path}.")
    with failed_downloads_report_path.open("w") as f:
        for result, reason in failed_downloads:
            f.write(f"{result.image_url} failed with reason: {reason}\n")
