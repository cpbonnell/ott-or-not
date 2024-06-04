"""
These classes are utilities for collecting, managing, and curating collections
of images for use in machine learning applications.
"""

import hashlib
import re
import sqlite3
from abc import ABC
from importlib import resources
from pathlib import Path
from typing import Optional, override, Collection

from PIL import Image
from pydantic import BaseModel


class ImageMetadata(BaseModel):
    """
    A Pydantic model for storing information about an image.

    hexdigest - The MD5 hash of the image.
    filepath - The Path to the image file.
    search_query_strings - A list of search query strings that have returned this image.
    tags - A list of tags assigned to this image by the user.
    hashwords - A tuple of two words chosen from a list of adjectives and nouns based on the hexdigest.
    """

    hexdigest: str
    filepath: Path
    search_query_strings: set[str] = set()
    tags: set[str] = set()
    hashwords: Optional[tuple[str, str]] = None

    def update_with(self, other: "ImageMetadata", update_path: bool = False) -> None:
        """
        Update this ImageMetadata object with the values from another ImageMetadata object.

        This method is used to update the search_query_strings and tags fields of this object
        with the values from another object. The hexdigest, and hashwords fields are
        not updated, as they are considered to be immutable. The filepath field is also
        not updated by default, but can be updated by setting the update_path parameter to True.
        """
        self.search_query_strings.update(other.search_query_strings)
        self.tags.update(other.tags)
        if update_path:
            self.filepath = other.filepath


class ImageHasher:
    """
    This class is a singleton that provides methods for hashing images.

    Some of the optional components of the class are ~ 10kb to 15kb in size,
    so they are lazily loaded only if used, and the class is a singleton to
    prevent multiple copies from being loaded into memory.

    The hexdigest is the MD5 hash of the image, and the hashwords are two words
    chosen from a list of adjectives and nouns, based on the hexdigest. The words
    can themselves be used as a type of hash, and should be stable across multiple
    runs of the program, as long as the version of the library (and hence the
    included lists of adjectives and nouns) remains the same.
    """

    _instance: "ImageHasher" = None

    @staticmethod
    def get_or_create() -> "ImageHasher":
        if ImageHasher._instance is None:
            ImageHasher._instance = ImageHasher()
        return ImageHasher._instance

    def __init__(self):
        self._adjectives_resource = (
            resources.files() / "resources" / "words" / "adjectives.txt"
        )
        self._nouns_resource = resources.files() / "resources" / "words" / "nouns.txt"
        self._adjectives = None
        self._nouns = None

    @property
    def adjectives(self):
        if self._adjectives is None:
            self._adjectives = self._adjectives_resource.read_text().split("\n")
        return self._adjectives

    @property
    def nouns(self):
        if self._nouns is None:
            self._nouns = self._nouns_resource.read_text().split("\n")
        return self._nouns

    def _get_hashwords_from_hexdigest(self, hexdigest: str) -> tuple[str, str]:
        adjective = self.adjectives[int(hexdigest[:8], 16) % len(self.adjectives)]
        noun = self.nouns[int(hexdigest[8:], 16) % len(self.nouns)]
        return adjective, noun

    def get_hexdigest(self, image: Image.Image) -> str:
        md5 = hashlib.md5()
        md5.update(image.tobytes())
        return md5.hexdigest()

    def get_hashwords(self, image: Image.Image) -> tuple[str, str]:
        hexdigest = self.get_hexdigest(image)
        return self._get_hashwords_from_hexdigest(hexdigest)

    def get_hashwords_and_hexdigest(self, image: Image.Image) -> tuple[str, str, str]:
        hexdigest = self.get_hexdigest(image)
        adjective, noun = self._get_hashwords_from_hexdigest(hexdigest)
        return adjective, noun, hexdigest


class ImageRepository(ABC):

    file_path_part_pattern = re.compile(r"([a-z]+)_([a-z]+)_([a-f0-9]+)\.jpeg")

    @staticmethod
    def create_image_filename(image: Image.Image) -> str:

        # Get the hashwords and hexdigest for the image.
        adjective, noun, hexdigest = (
            ImageHasher.get_or_create().get_hashwords_and_hexdigest(image)
        )
        return f"{adjective}_{noun}_{hexdigest}.jpeg"

    @staticmethod
    def get_hash_parts_from_filename(filename: str) -> dict[str, str] | None:
        """
        return a dictionary containing the adjective, noun, and hexdigest from the filename.
        """
        match = ImageRepository.file_path_part_pattern.match(filename)
        if match is None or len(match.groups()) < 3:
            return None
        return {
            "adjective": match.group(1),
            "noun": match.group(2),
            "hexdigest": match.group(3),
        }

    def construct_image_metadata(self, image: Image.Image) -> ImageMetadata:
        adjective, noun, hexdigest = (
            ImageHasher.get_or_create().get_hashwords_and_hexdigest(image)
        )
        return ImageMetadata(
            hexdigest=hexdigest,
            filepath=self._root_directory / self.create_image_filename(image),
            hashwords=(adjective, noun),
        )

    def save_image(
        self,
        image: Image.Image,
        search_terms: str | Collection[str] | None = None,
        tags: str | Collection[str] | None = None,
        **kwargs,
    ) -> bool:
        raise NotImplementedError

    def get_image_metadata(self, hexdigest: str) -> Optional[ImageMetadata]:
        raise NotImplementedError


class FileSystemImageRepository(ImageRepository):
    """
    A simple image repository using only the local file system.

    This class is an implementation of the ImageRepository ABC that stores images
    on the local file system. It maintains a repository of image metadata in a
    SQLite database, and stores the images in a directory specified by the root_directory
    parameter. The image metadata includes the hexdigest of the image, the file path
    of the image, a list of search query strings that have returned this image, and
    a list of tags assigned to this image by the user.

    Duplicate images are detected by comparing the hexdigest of the image to the
    hexdigests of images already stored in the repository. If a duplicate image is
    detected, the existing metadata is returned, and the image is not saved again.

    Each call to save_image maintains its connection to the SQLite database, so it
    is safe to have multiple threads or processes calling save_image concurrently.
    """

    METADATA_TABLE_CREATION_QUERY = """
    CREATE TABLE IF NOT EXISTS image_metadata (
        hexdigest TEXT PRIMARY KEY,
        metadata JSON NOT NULL
    )
    """

    METADATA_INSERTION_QUERY = """
    INSERT INTO image_metadata (hexdigest, metadata)
    VALUES ('{hexdigest}', '{metadata}')
    ON CONFLICT (hexdigest) DO UPDATE SET metadata = '{metadata}'
    """

    METADATA_GET_QUERY = """
    SELECT metadata FROM image_metadata WHERE hexdigest = '{hexdigest}'
    """

    def __init__(self, root_directory: Path | str) -> None:
        super().__init__()
        self._root_directory = Path(root_directory)

        # Identify the database file for this repository, and ensure that the metadata table exists.
        self._db_filepath = self._root_directory / "image_metadata_repository.db"
        with sqlite3.connect(self._db_filepath) as conn:
            conn.execute(self.METADATA_TABLE_CREATION_QUERY)

    @override
    def get_image_metadata(self, hexdigest: str) -> ImageMetadata | None:
        """
        Retrieve the metadata for an image with the given hexdigest.
        """
        with sqlite3.connect(self._db_filepath) as conn:
            result = conn.execute(
                self.METADATA_GET_QUERY.format(hexdigest=hexdigest)
            ).fetchone()
            if result is None:
                return None
            return ImageMetadata.model_validate_json(result[0])

    @override
    def save_image(
        self,
        image: Image.Image,
        search_terms: str | Collection[str] | None = None,
        tags: str | Collection[str] | None = None,
        **kwargs,
    ) -> Optional[ImageMetadata]:
        """
        Save an image to the repository and return its metadata.

        If the image is already in the repository, the metadata will be updated but the original
        image file will not be overwritten.

        :param image: The image to save.
        :param search_terms: The search terms that returned this image.
        :param tags: The tags assigned to this image.
        :param kwargs: Additional keyword arguments (not currently used, but included for future compatibility)
        :return: The metadata for the saved image.
        """

        new_image_metadata = self.construct_image_metadata(image)
        existing_metadata = self.get_image_metadata(new_image_metadata.hexdigest)

        # Combine all of the metadata for the image.
        if existing_metadata is not None:
            new_image_metadata.update_with(existing_metadata)

        if search_terms is not None:
            if isinstance(search_terms, str):
                search_terms = {search_terms}
            new_image_metadata.search_query_strings.update(search_terms)

        if tags is not None:
            if isinstance(tags, str):
                tags = {tags}
            new_image_metadata.tags.update(tags)

        # If the image is already on disk, we can skip writing it again.
        if not new_image_metadata.filepath.exists():
            image.save(new_image_metadata.filepath, format="JPEG")

        # Save the (possibly updated) metadata to the database.
        with sqlite3.connect(self._db_filepath) as conn:
            prepared_insertion_query = self.METADATA_INSERTION_QUERY.format(
                hexdigest=new_image_metadata.hexdigest,
                metadata=new_image_metadata.model_dump_json(),
            )
            conn.execute(prepared_insertion_query)

        return new_image_metadata
