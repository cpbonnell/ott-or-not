from rich.console import Console
from rich.table import Table
from curator.image_repository import FileSystemImageRepository, ImageRepository


def main(repository_location: str):

    console = Console()
    repository = FileSystemImageRepository(repository_location)

    count_by_tag_dict = repository.get_count_of_images_by_tag()

    table = Table(title="Image Count by Tag")
    table.add_column("Tag", style="cyan")
    table.add_column("Count", style="magenta")

    for tag, count in count_by_tag_dict.items():
        table.add_row(tag, str(count))

    console.print("===== Begining count of images by tag =====")
    console.print(
        "Note: The count is performed for each tag, so if an image has multiple tags, "
        "it will appear in the count for each one."
    )
    console.print(table)
