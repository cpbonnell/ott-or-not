"""
These classes are utilities for collecting, managing, and curating collections
of images for use in machine learning applications.
"""

from abc import ABC
from PIL import Image
import hashlib


class ImageRepository(ABC):

    @staticmethod
    def get_image_hash(image: Image.Image) -> str:
        md5 = hashlib.md5()
        md5.update(image.tobytes())
        return md5.hexdigest()

    @staticmethod
    def create_image_filename(image: Image.Image, extension: str = ".jpg") -> str:

        # Strip leading periods from the extension, and check that it is an acceptable format.
        while extension[0] == ".":
            extension = extension[1:]
        assert extension in ["jpg", "jpeg", "png"]

        # Compute the hash and return the image name.
        image_hash = ImageRepository.get_image_hash(image)
        return f"{image_hash}.{extension}"


class FileSystemImageRepository(ImageRepository):
    pass
