import click
from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

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


@click.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--repository-location", "-r", type=click.Path(), default=Path.cwd())
@click.option("--number-of-workers", "-n", type=int, default=6)
def import_directory(
    directory: Path, repository_location: Path, number_of_workers: int
) -> None:
    repository = FileSystemImageRepository(root_directory=repository_location)
    thread_pool = ThreadPoolExecutor(max_workers=number_of_workers)

    # Get all the files in the directory so we have an idea of how much work there is
    tasks_to_be_done = []
    for root, dirs, files in directory.walk():
        for file in files:
            image_filepath = Path(root) / file
            if image_filepath.suffix not in [".jpg", ".jpeg", ".png"]:
                continue

            task = ImportFileTask(repository, image_filepath, None, None)
            tasks_to_be_done.append(task)

    # Submit all the tasks to the thread pool, keeping track of how many are completed
    # so we can update the progress bar
    print(f"Importing {len(tasks_to_be_done)} images from {directory}...")
    progress_bar = tqdm(total=len(tasks_to_be_done))

    for task in tasks_to_be_done:
        thread_pool.submit(task)

    for t in as_completed(tasks_to_be_done):
        progress_bar.update(1)
    progress_bar.close()
