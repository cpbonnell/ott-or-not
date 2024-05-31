from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from curator.image_repository import (
    FileSystemImageRepository,
    ImageHasher,
    ImageRepository,
)


def test_create_image_filename():
    image = Image.new("RGB", (100, 100))
    image_repository = ImageRepository()
    filename = image_repository.create_image_filename(image)
    assert filename.endswith(".jpeg")


def test_get_hash_parts_from_filename():
    image_repository = ImageRepository()
    filename = "happy_dog_123456.jpeg"
    hash_parts = image_repository.get_hash_parts_from_filename(filename)
    assert hash_parts["adjective"] == "happy"
    assert hash_parts["noun"] == "dog"
    assert hash_parts["hexdigest"] == "123456"


def test_construct_image_metadata():
    image = Image.new("RGB", (100, 100))

    with TemporaryDirectory() as tempdir:
        expected_adjective, expected_noun, expected_hexdigest = (
            ImageHasher.get_or_create().get_hashwords_and_hexdigest(image)
        )

        image_repository = FileSystemImageRepository(root_directory=Path(tempdir))
        image_metadata = image_repository.construct_image_metadata(image)
        assert image_metadata.hexdigest == expected_hexdigest
        assert image_metadata.filepath
        assert image_metadata.hashwords
        assert image_metadata.hashwords == (expected_adjective, expected_noun)
        assert image_metadata.filepath.suffix == ".jpeg"


def test_save_image():
    plain_image = Image.new("RGB", (100, 100))
    mandel_image = Image.effect_mandelbrot((200, 200), (-2, -1.5, 1, 1.5), 20)

    with TemporaryDirectory() as tempdir:
        image_repository = FileSystemImageRepository(root_directory=Path(tempdir))

        plain_image_metadata = image_repository.save_image(plain_image)
        assert plain_image_metadata.filepath.is_file()

        mandel_image_metadata = image_repository.save_image(mandel_image)
        assert mandel_image_metadata.filepath.is_file()

        assert plain_image_metadata.filepath != mandel_image_metadata.filepath
        assert plain_image_metadata.hexdigest != mandel_image_metadata.hexdigest


def test_retrieve_image():
    plain_image = Image.new("RGB", (100, 100))
    mandel_image = Image.effect_mandelbrot((200, 200), (-2, -1.5, 1, 1.5), 20)

    with TemporaryDirectory() as tempdir:
        image_repository = FileSystemImageRepository(root_directory=Path(tempdir))

        # insert a few images that we can run tests on
        plain_metadata = image_repository.save_image(plain_image, tags=["plain"])
        assert plain_metadata.filepath.is_file()
        assert "plain" in plain_metadata.tags

        mandel_metadata = image_repository.save_image(
            mandel_image,
            tags=["mandelbrot"],
            search_terms=["Something extremely Fractal"],
        )
        assert mandel_metadata.filepath.is_file()
        assert "mandelbrot" in mandel_metadata.tags
        assert "Something extremely Fractal" in mandel_metadata.search_query_strings

        # Retrieve the image metadata and check that they are the same as the ones we inserted
        plain_hash = ImageHasher.get_or_create().get_hexdigest(plain_image)
        retrieved_plain_metadata = image_repository.get_image_metadata(plain_hash)
        assert retrieved_plain_metadata.filepath.is_file()
        assert retrieved_plain_metadata.hexdigest == plain_metadata.hexdigest
        assert retrieved_plain_metadata.filepath == plain_metadata.filepath
        assert "plain" in retrieved_plain_metadata.tags
        assert "mandelbrot" not in retrieved_plain_metadata.tags

        mandel_hash = ImageHasher.get_or_create().get_hexdigest(mandel_image)
        retrieved_mandle_metadata = image_repository.get_image_metadata(mandel_hash)
        assert retrieved_mandle_metadata.filepath.is_file()
        assert retrieved_mandle_metadata.hexdigest == mandel_metadata.hexdigest
        assert retrieved_mandle_metadata.filepath == mandel_metadata.filepath
        assert "mandelbrot" in retrieved_mandle_metadata.tags
        assert "plain" not in retrieved_mandle_metadata.tags
        assert (
            "Something extremely Fractal"
            in retrieved_mandle_metadata.search_query_strings
        )

        # Check that we get None when we try to retrieve a non-existent image
        non_existent_metadata = image_repository.get_image_metadata("non_existent")
        assert non_existent_metadata is None
