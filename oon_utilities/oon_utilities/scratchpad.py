import click
from pathlib import Path


@click.command
@click.option("--download-path", type=click.Path(exists=True), default="~/Downloads")
def main(download_path: Path):
    pass
