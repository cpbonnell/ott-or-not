"""
These classes are utilities for collecting, managing, and curating collections
of images for use in machine learning applications.
"""

from abc import ABC
from PIL import Image
import hashlib
from importlib import resources


class ImageHasher:
    """
    This class is a singleton that provides a method for hashing images.
    """

    instance: "ImageHasher" = None

    @staticmethod
    def get_or_create() -> "ImageHasher":
        if ImageHasher.instance is None:
            ImageHasher.instance = ImageHasher()
        return ImageHasher.instance

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

    @staticmethod
    def create_image_filename(image: Image.Image, extension: str = ".jpg") -> str:

        # Strip leading periods from the extension, and check that it is an acceptable format.
        while extension[0] == ".":
            extension = extension[1:]
        assert extension in ["jpg", "jpeg", "png"]

        # Get the hashwords and hexdigest for the image.
        adjective, noun, hexdigest = (
            ImageHasher.get_or_create().get_hashwords_and_hexdigest(image)
        )
        return f"{adjective}_{noun}_{hexdigest}.{extension}"


class FileSystemImageRepository(ImageRepository):
    pass
