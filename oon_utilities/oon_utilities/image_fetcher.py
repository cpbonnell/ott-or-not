import logging
from dataclasses import dataclass
from pathlib import Path, PurePath
from concurrent.futures import ThreadPoolExecutor

import click
import requests
from googleapiclient.discovery import build
from requests.exceptions import ConnectionError, SSLError, Timeout
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


def quick_image_search(
    search_term: str,
    number_of_images_desired: int = 5,
    api_key: str = GOOGLE_CUSTOM_SEARCH_API_KEY,
    csi_id: str = GOOGLE_CUSTOM_SEARCH_ENGINE_ID,
    **kwargs,
) -> list[str]:
    """
    Performs a Google Custom Search for images based on the provided search term.

    :param search_term:  The term to search for.
    :param number_of_images:  The number of images to return.
    :param api_key:  The Google API key to use for the search.
    :param csi_id:  The Custom Search Engine ID to use for the search.
    :return:  A list of URLs to the images found.
    """
    service = build("customsearch", "v1", developerKey=api_key)
    results = []
    query_index = 0

    while len(results) < number_of_images_desired:
        expected_results_required = number_of_images_desired - len(results)
        batch_size = expected_results_required if expected_results_required < 10 else 10

        query_result = (
            service.cse()
            .list(
                q=search_term,
                cx=csi_id,
                searchType="image",
                num=batch_size,
                start=query_index,
                **kwargs,
            )
            .execute()
        )
        results.extend([item["link"] for item in query_result["items"]])
        query_index += batch_size

    return results


def download_and_store_image(
    image_url: str, destination_path: Path, skip_existing_images: bool = True, **kwargs
) -> bool:
    """
    Downloads an image from a URL and stores it at the provided destination path.

    :param image_url:  The URL of the image to download.
    :param destination_path:  The path to store the downloaded image.
    :param kwargs:  Additional keyword arguments to pass to the requests.get function.
    :return:  True if the image was successfully downloaded and stored, False otherwise.
    """
    # If the file already exists, skip this image to avoid fetching it from the internet again.
    if skip_existing_images and destination_path.exists():
        return True

    try:
        response = requests.get(image_url, timeout=14, **kwargs)
    except (ConnectionError, Timeout) as e:
        logging.error(f"Timeout error whie fetching image {image_url}")
        return False

    if response.status_code == 200:
        with open(destination_path, "wb") as f:
            f.write(response.content)
        return True
    return False


@click.command
@click.option(
    "--download-path",
    type=click.Path(exists=True),
    default=Path("/mnt/a/data/ott-or-not").expanduser(),
)
def main(download_path: Path):

    # Ensure we have the necessary configuration
    assert GOOGLE_CUSTOM_SEARCH_API_KEY
    assert GOOGLE_CUSTOM_SEARCH_ENGINE_ID

    # Search for some images of various different otter species
    otter_searches = [
        ImageSearchRequest(
            "North American River Otter", "north_american_river_otter", 200
        ),
        ImageSearchRequest("Sea Otter", "sea_otter", 200),
        ImageSearchRequest("Asian Small Clawed Otter", "asian_small_clawed_otter", 200),
        ImageSearchRequest("Giant Otter", "giant_otter", 200),
    ]

    # Add some non-otter images for the "not otter" category
    non_otter_searches = [
        ImageSearchRequest("Beaver", "beaver", 200),
        ImageSearchRequest("Platypus", "platypus", 200),
        ImageSearchRequest("Muskrat", "muskrat", 200),
        ImageSearchRequest("Mink", "mink", 200),
    ]
    searches = otter_searches + non_otter_searches

    for search in searches:

        # Define the destinatino directory, and ensure it exists
        destination_directory = download_path / search.label_category
        destination_directory.mkdir(parents=True, exist_ok=True)

        # Perform the search
        image_urls = quick_image_search(search.search_term, search.quantity)

        # Download the resulting images
        for index, image_url in tqdm(enumerate(image_urls)):
            url_parts = parse_url(image_url)
            image_remote_path = PurePath(url_parts.path)
            destination_path = destination_directory / image_remote_path.name
            for attempt in range(2):
                # Right now, we will only give 2nd changes for sites in the
                if attempt == 2 and url_parts.host not in TRUST_ANYWAY:
                    break

                # If we've already tried once, and the host is in the TRUST_ANYWAY list, we'll skip verification
                verify = (
                    False if attempt > 0 and url_parts.host in TRUST_ANYWAY else True
                )

                try:
                    download_and_store_image(image_url, destination_path, verify=verify)
                except SSLError as e:
                    logging.error(
                        f"SSL Error encountered from host {url_parts.host} (attempt {attempt})."
                    )
