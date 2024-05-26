"""
These classes are utilities for collecting, managing, and curating collections
of images for use in machine learning applications.
"""

import hashlib
from abc import ABC
from importlib import resources
from pathlib import Path
import re

from PIL import Image


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

    def save_image(self, image: Image.Image, **kwargs) -> bool:
        raise NotImplementedError


class FileSystemImageRepository(ImageRepository):
    """
    A simple image repository using only the local file system.

    This class is an implementation of the ImageRepository ABC that stores images
    on the local file system. It maintains an in-memory record of the image hashes
    in all directories it manages, to prevent duplicate images from being saved.
    """

    def __init__(self, root_directory: Path | str) -> None:
        super().__init__()
        self._root_directory = Path(root_directory)

        self._image_hashes = set()
        for root, dirs, files in self._root_directory.walk(
            self._root_directory, follow_symlinks=False
        ):
            for file in files:
                if file.endswith(".jpeg"):
                    hash_parts = self.get_hash_parts_from_filename(file)
                    if hash_parts is not None:
                        self._image_hashes.add(hash_parts["hexdigest"])
                    else:
                        print(
                            f"Skipping file {file} wich is not an image repository name."
                        )

    def save_image(self, image: Image.Image, **kwargs) -> None:
        filename = self.create_image_filename(image)
        if filename is None:
            return False

        if filename in self._image_hashes:
            True

        image.save(self._root_directory / filename, format="JPEG")
        self._image_hashes.add(filename)
        return True
