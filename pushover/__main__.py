from argparse import ArgumentParser
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pushover.packager import package
from pushover.server import serve


HELP_IMAGE = (
    "either a 128x128 or larger PNG to generate an icon set from or a folder containing the appropriate sizes of icons"
    "from which to create an icon package"
)

HELP_WEBSITE = (
    "a static JSON file containing website data for the Safari push API"
)

HELP_CERTIFICATES = (
    "your signed developer certificates allowing you to make Safari push notifications"
)


try:

    # Create the parent parser
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(title="mode", dest="command", help="packager modes")

    # Create the generator parser
    build_parser = subparsers.add_parser("build", help="generate a static push package")
    build_parser.add_argument("-i", "--icon", dest="icon", help=HELP_IMAGE)
    build_parser.add_argument("-w", "--website", dest="website", required=True, help=HELP_WEBSITE)
    build_parser.add_argument("-c", "--certificates", dest="certificates", required=True, help=HELP_CERTIFICATES)

    # Create the server parser
    server_parser = subparsers.add_parser("serve", help="serve the push package")

    # Parse args and delegate
    namespace = parser.parse_args()
    if namespace.command is None or namespace.command == "serve":
        serve()
    elif namespace.command == "build":
        package(namespace)

# The error should be printed before this happens
except RuntimeError:
    pass
