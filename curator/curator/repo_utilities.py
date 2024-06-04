from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console

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


# ========== YAML Classes related to Shopping List ==========
class ImageSearchRequest(yaml.YAMLObject):
    yaml_tag = "!ImageSearchRequest"

    def __init__(
        self, search_term: str, desired_quantity: int = 100, tags: list[str] = []
    ):
        self.search_term = search_term
        self.desired_quantity = desired_quantity
        self.tags = tags

        if desired_quantity > 100:
            console.print(
                f"Google image search only allows a maximum of 100 results per search term. "
                f"Limiting the number of results for search term '{search_term}' to 100."
            )
            self.desired_quantity = 100
        else:
            self.desired_quantity = desired_quantity

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"search_term={self.search_term}, "
            f"desired_quantity={self.desired_quantity}, "
            f"tags={self.tags})"
        )


class Settings(yaml.YAMLObject):
    yaml_tag = "!Settings"

    VALID_SEARCH_PROVIDERS = ["google", "bing"]

    def __init__(
        self,
        search_provider: str = "google",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        rate_limit: Optional[int] = None,
    ):
        if search_provider.lower() not in self.VALID_SEARCH_PROVIDERS:
            raise ValueError(
                f"Invalid search provider '{search_provider}'. "
                f"Valid options are {self.VALID_SEARCH_PROVIDERS}."
            )
        else:
            self.search_provider = search_provider.lower()

        self.api_key = api_key
        self.api_secret = api_secret
        self.rate_limit = rate_limit

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(search_provider={self.search_provider}, rate_limit={self.rate_limit})"
        )


class ShoppingList(yaml.YAMLObject):
    yaml_tag = "!ShoppingList"

    def __init__(self, settings: Settings, searches: list[ImageSearchRequest]):
        self.settings = settings
        self.searches = searches

    def __repr__(self):
        return f"{self.__class__.__name__}(settings={self.settings}, searches={self.searches})"


def create_sample_shopping_list() -> ShoppingList:
    settings = Settings(
        search_provider="google", rate_limit=100, api_key="123456", api_secret="abcdef"
    )
    search1 = ImageSearchRequest(
        search_term="cat", desired_quantity=10, tags=["animal"]
    )
    search2 = ImageSearchRequest(
        search_term="dog", desired_quantity=10, tags=["animal"]
    )

    shopping_list = ShoppingList(settings=settings, searches=[search1, search2])

    return shopping_list
