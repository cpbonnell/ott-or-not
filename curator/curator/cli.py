import click
from pathlib import Path
from rich.console import Console
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@click.group()
@click.option(
    "--repository-location",
    "-r",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    envvar="CURATOR_REPOSITORY_LOCATION",
    help="The location of the image repository that the images should be added to.",
)
@click.pass_context
def cli_group(ctx: click.Context, repository_location: Path):
    # Note: The repository location can come from the environment
    # variable CURATOR_REPOSITORY_LOCATION

    ctx.obj = {"repository_location": repository_location}


@cli_group.command(name="import-directory")
@click.argument(
    "directory",
    type=click.Path(exists=True),
)
@click.option(
    "--number-of-workers",
    "-n",
    type=int,
    default=6,
    help="The number of worker threads to use.",
)
@click.option(
    "--tag-with-parent-directory",
    is_flag=True,
    help="If set, the parent directory of the image will be used as a tag.",
)
@click.pass_context
def import_directory(
    ctx: click.Context,
    directory: Path,
    number_of_workers: int,
    tag_with_parent_directory: bool,
):
    from curator.directory_import import main

    repository_location = ctx.obj["repository_location"]
    main(directory, repository_location, number_of_workers, tag_with_parent_directory)


def default_manifest_path(
    ctx: click.Context, param: click.Option, value: Optional[Path]
) -> Optional[Path]:
    """
    If the manifest location is not provided, use the repository location to find the manifest.
    """
    if value is not None:
        return value
    repository_location = ctx.params.get("repository_location")
    if repository_location:
        return Path(repository_location) / "shopping-list.yaml"
    return None


@cli_group.command(name="search")
@click.option(
    "--shopping-list-location",
    "-s",
    type=click.Path(path_type=Path),
    default=None,
    callback=default_manifest_path,
    help="The location of the manifest. Defaults to 'manifest.yaml' in the repository location.",
)
@click.option(
    "--concurrent-downloads",
    "-c",
    type=int,
    default=6,
    help="The number of worker threads to use.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="The logging level to use.",
)
@click.pass_context
def search(
    ctx: click.Context,
    shopping_list_location: Optional[Path],
    concurrent_downloads: int,
    log_level: str,
):
    from curator.search import main

    repository_location = ctx.obj["repository_location"]
    if not shopping_list_location:
        shopping_list_location = repository_location / "shopping-list.yaml"

    main(repository_location, shopping_list_location, concurrent_downloads, log_level)


@cli_group.command(name="info")
@click.option(
    "--shopping-list-location",
    "-s",
    type=click.Path(path_type=Path),
    default=None,
    callback=default_manifest_path,
    help="The location of the manifest. Defaults to 'manifest.yaml' in the repository location.",
)
@click.pass_context
def info(ctx: click.Context, shopping_list_location: Optional[Path]):
    from curator.repo_utilities import check_repository_info

    # Idenfity the repository location and the shopping list location.
    repository_location = ctx.obj["repository_location"]

    if not shopping_list_location:
        shopping_list_location = repository_location / "shopping-list.yaml"

    check_repository_info(repository_location, shopping_list_location)


@cli_group.command(name="init")
@click.argument(
    "component",
    type=click.Choice(["repository", "shopping-list", "all"]),
)
@click.pass_context
def init(ctx: click.Context, component: str):
    from curator.repo_utilities import create_sample_shopping_list
    from curator.image_repository import FileSystemImageRepository
    import yaml

    console = Console()
    GREEN_CHECK = "\u2705"

    repository_location = ctx.obj["repository_location"]

    # Initialize repository directory if it does not exist
    if not repository_location.exists():
        repository_location.mkdir(parents=True)
        console.print(
            f"{GREEN_CHECK} The repository directory has been created at {repository_location}."
        )

    # Initialize a database file if needed (FileSystemRepository does this
    # as part of being instantiated)
    if component in ["repository", "all"]:
        fsir = FileSystemImageRepository(root_directory=repository_location)
        console.print(
            f"{GREEN_CHECK} A database of image metadata has been created at {fsir.db_filepath}."
        )

    # Initialize a YAML filw with a sample shopping list
    if component in ["shopping-list", "all"]:
        shopping_list_location = repository_location / "shopping-list.yaml"
        sample_shopping_list = create_sample_shopping_list()

        with open(shopping_list_location, "w") as file:
            file.write(yaml.dump(sample_shopping_list))

        console.print(
            f"{GREEN_CHECK} A sample shopping list has been created in the file {shopping_list_location}."
        )


@cli_group.command(name="inventory")
@click.pass_context
def inventory(ctx: click.Context):
    from curator.inventory import main

    repository_location = ctx.obj["repository_location"]

    main(repository_location)
