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
