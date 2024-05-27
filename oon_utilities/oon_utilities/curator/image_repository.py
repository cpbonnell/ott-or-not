"""
These classes are utilities for collecting, managing, and curating collections
of images for use in machine learning applications.
"""

import hashlib
from abc import ABC
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
import re

from PIL import Image
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import sqlite3


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
    search_query_strings: list[str] = []
    tags: list[str] = []
    hashwords: Optional[tuple[str, str]] = None


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
            ImageHasher.instance = ImageHasher()
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

    def get_image_metadata(self, image: Image.Image) -> ImageMetadata:
        adjective, noun, hexdigest = (
            ImageHasher.get_or_create().get_hashwords_and_hexdigest()
        )
        return ImageMetadata(
            hexdigest=hexdigest,
            filepath=self._root_directory / self.create_image_filename(image),
            hashwords=(adjective, noun),
        )

    def save_image(self, image: Image.Image, **kwargs) -> bool:
        raise NotImplementedError


class FileSystemImageRepository(ImageRepository):
    """
    A simple image repository using only the local file system.

    This class is an implementation of the ImageRepository ABC that stores images
    on the local file system. It maintains an in-memory record of the image hashes
    in all directories it manages, to prevent duplicate images from being saved.
    """

    METADATA_TABLE_CREATION_QUERY = """
    CREATE TABLE IF NOT EXISTS image_metadata (
        hexdigest TEXT PRIMARY KEY,
        filepath TEXT NOT NULL,
        metadata JSON NOT NULL
    )
    """

    METADATA_INSERTION_QUERY = """
    INSERT INTO image_metadata (hexdigest, filepath, metadata)
    VALUES ({hexdigest}, {filepath}, {metadata})
    ON CONFLICT (hexdigest) DO UPDATE SET metadata = {metadata}
    """

    METADATA_CHECK_FOR_EXISTENCE_QUERY = """
    SELECT filepath FROM image_metadata WHERE hexdigest = {hexdigest}
    """

    # NOTE: The JSON_SET function below will fail if the metadata JSON does not contain a "filepath" key.
    # This is what we want, since all metadata should contain a filepath key, and if it does not then we
    # want to an error to tell us that something is wrong.
    METADATA_SET_IMAGE_FILEPATH_QUERY = """
    UPDATE image_metadata 
    SET 
        filepath = {filepath},
        metadata = JSON_REPLACE(metadata, '$.filepath', {filepath})
    WHERE hexdigest = {hexdigest}
    """

    def __init__(self, root_directory: Path | str) -> None:
        super().__init__()
        self._root_directory = Path(root_directory)

        # Identify the database file for this repository, and ensure that the metadata table exists.
        self._db_filepath = self._root_directory / "image_metadata_repository.db"
        with sqlite3.connect(self._db_filepath) as conn:
            conn.execute(self.METADATA_TABLE_CREATION_QUERY)

    def save_image(self, image: Image.Image, **kwargs) -> Optional[ImageMetadata]:

        image_metadata = self.get_image_metadata(image)

        prepared_exists_query = self.METADATA_CHECK_FOR_EXISTENCE_QUERY.format(
            hexdigest=image_metadata.hexdigest
        )
        prepared_insertion_query = self.METADATA_INSERTION_QUERY.format(
            hexdigest=image_metadata.hexdigest,
            filepath=image_metadata.filepath,
            metadata=image_metadata.model_dump_json(),
        )

        # Check if the metadata repository to see if the image has been saved before.
        with sqlite3.connect(self._db_filepath) as conn:

            # If the image already exists in the metadata, we can skip writing it to disk.
            result = conn.execute(prepared_exists_query).fetchone()
            if result is not None:
                reported_filepath = Path(result[0])
                if reported_filepath.exists():
                    # The hash exists, and so does the filepatfh we expect. We can skip writing the file.
                    return image_metadata
                else:
                    # The hash exists, but the file is not where we expect it, so we will write the image
                    # to the correct location and update the table metadata to ensure that we do not clobber
                    # information already known about the image with this hash.
                    conn.execute(
                        self.METADATA_SET_IMAGE_FILEPATH_QUERY.format(
                            hexdigest=image_metadata.hexdigest,
                            filepath=image_metadata.filepath,
                        )
                    )
                    # TODO: we should return the full image metadata here, not the newly created one.
                    return None

            # Write the file and image metadata
            image.save(image_metadata.filepath, format="JPEG")
            conn.execute(prepared_insertion_query)

        return image_metadata
