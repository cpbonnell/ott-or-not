import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import click
from PIL import Image
from tqdm import tqdm

from oon_utilities.curator.image_repository import (
    FileSystemImageRepository,
    ImageRepository,
)


class ImportFileTask:

    def __init__(
        self,
        repository: ImageRepository,
        image_filepath: Path,
        search_terms: str | list[str] | None,
        tags: str | list[str] | None,
        hold_until_event: threading.Event | None = None,
    ) -> None:
        self.repository = repository
        self.image_filepath = image_filepath
        self.search_terms = search_terms
        self.tags = tags
        self.hold_until_event = hold_until_event

    def __call__(self) -> None:

        if self.hold_until_event:
            self.hold_until_event.wait()

        image = Image.open(self.image_filepath)
        self.repository.save_image(image, self.search_terms, self.tags)


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True),
    help="The directory to import images from.",
)
@click.option(
    "--repository-location",
    "-r",
    type=click.Path(),
    default=Path.cwd(),
    help="The location of the image repository that the images should be added to.",
)
@click.option(
    "--number-of-workers",
    "-n",
    type=int,
    default=6,
    help="The number of worker threads to use.",
)
def import_directory(
    directory: Path, repository_location: Path, number_of_workers: int
) -> None:
    repository = FileSystemImageRepository(root_directory=repository_location)
    begin_importing_event = threading.Event()

    # Get all the files in the directory so we have an idea of how much work there is
    tasks_to_be_done = []
    for root, dirs, files in directory.walk():
        for file in files:
            image_filepath = Path(root) / file
            if image_filepath.suffix not in [".jpg", ".jpeg", ".png"]:
                continue

            task = ImportFileTask(
                repository, image_filepath, None, None, begin_importing_event
            )
            tasks_to_be_done.append(task)

    # Submit all the tasks to the thread pool, keeping track of how many are completed
    # so we can update the progress bar
    print(f"Importing {len(tasks_to_be_done)} images from {directory}...")
    progress_bar = tqdm(total=len(tasks_to_be_done))

    with ThreadPoolExecutor(max_workers=number_of_workers) as thread_pool:

        futures = [thread_pool.submit(task) for task in tasks_to_be_done]
        begin_importing_event.set()

        for _ in as_completed(futures):
            progress_bar.update(1)

    progress_bar.close()
    print("Import complete!")
