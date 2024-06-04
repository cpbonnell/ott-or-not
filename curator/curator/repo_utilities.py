from rich.console import Console
from pathlib import Path


def check_repo_exists(repository_location: Path, shopping_list_location: Path) -> bool:
    console = Console()
    green_check = "\u2705"
    red_cross = "\u274C"

    # Idenfity the database file.
    database_location = repository_location / "image_metadata_repository.db"

    # Check if the repository location exists and whether the files have been initialized
    if repository_location.exists():
        repository_status = green_check
    else:
        repository_status = red_cross

    if shopping_list_location.exists():
        sl_status = green_check
    else:
        sl_status = red_cross

    if database_location.exists():
        database_status = green_check
    else:
        database_status = red_cross

    console.print(repository_status + f" Repository directory: {repository_location}")
    console.print(sl_status + f" Shopping list file: {shopping_list_location}")
    console.print(database_status + f" Database location: {database_location}")

    if all(
        [
            repository_location.exists(),
            shopping_list_location.exists(),
            database_location.exists(),
        ]
    ):
        console.print("The repository exists and has been initialized.")
        return True
    else:
        console.print("The repository does not exist or has not been initialized.")
        return False
