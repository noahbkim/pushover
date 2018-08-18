import shutil
import os
from pathlib import Path

from PIL import Image

import logging
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", datefmt="%m/%d/%y %I:%M:%S %p")


IMAGE_SIZES = (16, 32, 128)


def generate_icons(source: Path, destination: Path):
    """Generate the icon set given a base image."""

    # Check the path
    source = Path(source)
    if not source.name.endswith(".png"):
        print("A PNG image is required for icon generation")
        raise RuntimeError

    # Make the icon set folder
    try:
        os.makedirs(str(destination))
    except FileExistsError:

        # If the destination already exists
        while True:
            response = input(f"Overwrite existing path {destination}? [y/n]: ")
            if "yes".startswith(response.lower()):
                break
            elif "no".startswith(response.lower()):
                return

        # Delete file tree
        logging.debug("clearing existing icons")
        shutil.rmtree(str(destination))
        os.makedirs(str(destination))

    # Generate the requisite icon size
    logging.debug("generating new icons...")
    icon = Image.open(source)
    for size in IMAGE_SIZES:
        new = icon.resize((size, size), resample=Image.LANCZOS)
        new2 = new.resize((size * 2, size * 2), resample=0)
        new.save(destination.joinpath(f"icon_{size}x{size}.png"))
        new2.save(destination.joinpath(f"icon_{size}x{size}@2x.png"))


def command_line():
    """Run the command line prompt."""

    from argparse import ArgumentParser

    # Create the parent parser
    parser = ArgumentParser(description="A small icon set generator script")
    parser.add_argument("source", help="the base PNG image to scale")
    parser.add_argument("destination", default="icon.iconset", nargs="?", help="where to output the images to")

    # Parse args and delegate
    namespace = parser.parse_args()

    try:
        source = Path(namespace.source)
        destination = Path(namespace.destination)
    except TypeError:
        print("An invalid path was supplied!")

    try:
        generate_icons(source, destination)
    except RuntimeError:
        pass
    except KeyError:
        print("Exiting...")


if __name__ == "__main__":
    command_line()
