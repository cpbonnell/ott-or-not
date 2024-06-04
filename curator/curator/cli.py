import click
from pathlib import Path


@click.group()
def cli_group():
    pass


@cli_group.command(name="import-directory")
@click.argument(
    "directory",
    type=click.Path(exists=True),
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
@click.option(
    "--tag-with-parent-directory",
    is_flag=True,
    help="If set, the parent directory of the image will be used as a tag.",
)
def import_directory(
    directory: Path,
    repository_location: Path,
    number_of_workers: int,
    tag_with_parent_directory: bool,
):
    from curator.directory_import import main

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
    "--repository-location",
    "-r",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="The location of the image repository that the images should be added to.",
)
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
def search(
    repository_location: Path,
    shopping_list_location: Path,
    concurrent_downloads: int,
    log_level: str,
):
    from curator.search import main

    main(repository_location, shopping_list_location, concurrent_downloads, log_level)
