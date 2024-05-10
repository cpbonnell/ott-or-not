import click
from dataclasses import dataclass
from pathlib import Path, PurePath
import requests
from tqdm import tqdm
from urllib3.util import parse_url, Url
from googleapiclient.discovery import build
from requests.exceptions import SSLError

from oon_utilities.configuration import (
    GOOGLE_CUSTOM_SEARCH_API_KEY,
    GOOGLE_CUSTOM_SEARCH_ENGINE_ID,
)

TRUST_ANYWAY = [
    "www.nwf.org",
]


def quick_image_search(
    search_term: str,
    number_of_images: int = 5,
    api_key: str = GOOGLE_CUSTOM_SEARCH_API_KEY,
    csi_id: str = GOOGLE_CUSTOM_SEARCH_ENGINE_ID,
    **kwargs,
) -> list[str]:
    """
    Performs a Google Custom Search for images based on the provided search term.

    Args:
        search_term (str): The term to search for.
        number_of_images (int, optional): The number of images to return. Defaults to 5.
        api_key (str, optional): The API key for Google Custom Search. Defaults to GOOGLE_CUSTOM_SEARCH_API_KEY.
        csi_id (str, optional): The Custom Search Engine ID. Defaults to GOOGLE_CUSTOM_SEARCH_ENGINE_ID.
        **kwargs: Additional keyword arguments to pass to the Google Custom Search.

    Returns:
        list[str]: A list of URLs for the found images.
    """
    service = build("customsearch", "v1", developerKey=api_key)
    results = (
        service.cse()
        .list(
            q=search_term, cx=csi_id, searchType="image", num=number_of_images, **kwargs
        )
        .execute()
    )
    return [item["link"] for item in results["items"]]


def download_and_store_image(image_url: str, destination_path: Path, **kwargs) -> bool:
    response = requests.get(image_url, **kwargs)
    if response.status_code == 200:
        with open(destination_path, "wb") as f:
            f.write(response.content)
        return True
    return False


@dataclass(frozen=True)
class TrainingImageSearch:
    search_term: str
    label_category: str
    quantity: int


@click.command
@click.option(
    "--download-path",
    type=click.Path(exists=True),
    default=Path("~/Downloads/temporary/").expanduser(),
)
def main(download_path: Path):

    # Ensure we have the necessary configuration
    assert GOOGLE_CUSTOM_SEARCH_API_KEY
    assert GOOGLE_CUSTOM_SEARCH_ENGINE_ID

    # Define the search terms
    searches = [
        TrainingImageSearch("North American River Otter", "otter", 10),
        TrainingImageSearch("Beaver", "beaver", 10),
    ]

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
            destination_path = (
                destination_directory / f"{index}-{image_remote_path.suffix}"
            )
            try:
                download_and_store_image(image_url, destination_path)
            except SSLError as e:
                print(
                    f"SSL Error encountered fetching image {image_remote_path} from host {url_parts.host}."
                )
