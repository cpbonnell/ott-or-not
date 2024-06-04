from rich.console import Console
from pathlib import Path

console = Console()
GREEN_CHECK = "\u2705"
RED_CROSS = "\u274C"


def check_shopping_list_exists(shopping_list_location: Path) -> bool:
    if shopping_list_location.exists():
        console.print(GREEN_CHECK + f" Shopping list file: {shopping_list_location}")
        return True
    else:
        console.print(RED_CROSS + f" Shopping list file: {shopping_list_location}")
        return False


def check_database_file_exists(repository_location: Path) -> bool:
    # Idenfity the database file.
    database_location = repository_location / "image_metadata_repository.db"

    if database_location.exists():
        console.print(GREEN_CHECK + f" Database location: {database_location}")
        return True
    else:
        console.print(RED_CROSS + f" Database location: {database_location}")
        return False


def check_repository_directory_exists(repository_location: Path) -> bool:
    if repository_location.exists():
        console.print(GREEN_CHECK + f" Repository directory: {repository_location}")
        return True
    else:
        console.print(RED_CROSS + f" Repository directory: {repository_location}")
        return False


def check_repository_info(
    repository_location: Path, shopping_list_location: Path
) -> bool:

    repository_exists = check_repository_directory_exists(repository_location)
    database_exists = check_database_file_exists(repository_location)
    shopping_list_exists = check_shopping_list_exists(shopping_list_location)

    if repository_exists and database_exists and shopping_list_exists:
        console.print("The repository exists and has been initialized.")
        return True
    else:
        console.print("The repository does not exist or has not been initialized.")
        return False
