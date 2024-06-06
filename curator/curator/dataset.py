from pathlib import Path
from rich.console import Console
from rich.table import Table

from curator.image_repository import FileSystemImageRepository, ImageMetadata


def main(repository_location: Path, output_location: Path, classes: list[str]):

    GREEN_CHECK = "\u2705"
    console = Console()
    repository = FileSystemImageRepository(repository_location)

    # Fetch the image metadata from the repository for each class. Each calss can only
    # contain images that do not have any of the other classes as tags.
    distinct_classes = set(classes)
    metadata_by_class: dict[str, list[ImageMetadata]] = {}
    for tag in classes:
        tags_to_exclude = distinct_classes - {tag}
        metadata_by_class[tag] = repository.get_image_metadata_by_tag(
            tags=[tag], exclude_tags=tags_to_exclude
        )

    console.print("===== Checking for directories =====")

    # Create the dataset directory if it does not exist
    if not output_location.exists():
        output_location.mkdir(parents=True)
        console.print(
            f"{GREEN_CHECK} The dataset directory has been created at {output_location}."
        )

    # Create a subdirectory for each class in the dataset directory
    for class_name in classes:
        class_directory = output_location / class_name
        class_directory.mkdir(parents=True)
        console.print(
            f"{GREEN_CHECK} The directory for class {class_name} has been created at {class_directory}."
        )

    # Symlink the images to the appropriate class directories
    for class_name, metadatas in metadata_by_class.items():
        for metadata in metadatas:
            source = metadata.filepath
            destination = output_location / class_name / source.name
            destination.symlink_to(source)

    # Print a summary of the created dataset

    table = Table(title="Dataset Summary")
    table.add_column("Class", style="cyan")
    table.add_column("Image Count", style="magenta")

    for class_name, metadatas in metadata_by_class.items():
        table.add_row(class_name, str(len(metadatas)))

    console.print("\n===== Begining summary of dataset creation =====")
    console.print(f"A new dataset has been created in the directory {output_location}.")
    console.print(table)
