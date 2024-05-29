import click
from pathlib import Path
from PIL import Image

from oon_utilities.curator.image_repository import (
    ImageRepository,
    FileSystemImageRepository,
)


class ImportFileTask:

    def __init__(
        self,
        repository: ImageRepository,
        image_filepath: Path,
        search_terms: str | list[str] | None,
        tags: str | list[str] | None,
    ) -> None:
        self.repository = repository
        self.image_filepath = image_filepath
        self.search_terms = search_terms
        self.tags = tags

    def __call__(self) -> None:
        image = Image.open(self.image_filepath)
        self.repository.save_image(image, self.search_terms, self.tags)
