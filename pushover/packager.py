"""The Push Packager

This module is intended to implement the functionality provided by the
accompanying PHP script in the Safari push API documentation:

https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/NotificationProgrammingGuideForWebsites/PushNotifications/PushNotifications.html#//apple_ref/doc/uid/TP40013225-CH3-SW1
"""


import os
import shutil
import json
from OpenSSL import crypto
from pathlib import Path
from typing import Union
from hashlib import sha512

PathLike = Union[Path, str]


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


def sha512_file(path: PathLike):
    """Get the sha256 checksum of a file."""

    running = sha512()
    with open(path, "rb") as file:
        while True:
            data = file.read(65536)
            if not data:
                break
            running.update(data)
    return running.hexdigest()


def build_icons(path: PathLike, icons: PathLike):
    """Generate the icon set given a base image."""

    from PIL import Image

    # Check the path
    path = Path(path)
    if not path.name.endswith(".png"):
        print("A PNG image is required for icon generation")
        raise RuntimeError

    # Make the icon set folder
    os.makedirs(icons, exist_ok=True)

    # Generate the requisite icon size
    icon = Image.open(path)
    for size in (16, 32, 128):
        resized = icon.resize((size, size), resample=Image.LANCZOS)
        resized2 = resized.resize((size * 2, size * 2), resample=0)
        resized.save(icons.joinpath(f"icon_{size}x{size}.png"))
        resized2.save(icons.joinpath(f"icon_{size}x{size}@2.png"))


def build_manifest(package: PathLike, manifest: PathLike):
    """Get the SHA256 sums of all of the items in the package."""

    # Build the manifest dictionary with everything
    output = {}
    files = (
        os.path.join(dp, file)
        for dp, dn, files in os.walk(package)
        for file in files
        if not file.startswith("."))
    for file in files:
        output[file] = {"hashType": "sha512", "hashValue": sha512_file(file)}

    # Write to file
    with open(manifest, "w") as file:
        json.dump(output, file, indent=2)


def build_signature(manifest: PathLike, certificates: PathLike, package: PathLike):
    """Build the signature file for the package."""

    # Read the certificates
    with open(certificates, "rb") as file:
        raw = file.read()
    try:
        p12 = crypto.load_pkcs12(raw)
    except crypto.Error:
        import getpass
        password = getpass.getpass("Enter the password to your developer certificates: ")
        p12 = crypto.load_pkcs12(raw, password)

    # https://stackoverflow.com/questions/33634379/pkcs-7-detached-signature-with-python-and-pyopenssl/33726421#33726421
    # How the fuck did this guy even figure this out?

    # Create the memory buffer for the signature
    with open(manifest, "rb") as file:
        buffer_in = crypto._new_mem_buf(file.read())

    # Grab the flags from source
    # https://github.com/openssl/openssl/blob/52df25cf2e656146cb3b206d8220124f0417d03f/include/openssl/pkcs7.h
    PKCS7_DETACHED = 0x40
    PKCS7_BINARY = 0x80

    # Sign the actual file
    pkcs7 = crypto._lib.PKCS7_sign(
        p12.get_certificate()._x509,
        p12.get_privatekey()._pkey,
        crypto._ffi.NULL,
        buffer_in,
        PKCS7_BINARY | PKCS7_DETACHED)

    # Write out the result
    buffer_out = crypto._new_mem_buf()
    crypto._lib.i2d_PKCS7_bio(buffer_out, pkcs7)
    der = crypto._bio_to_string(buffer_out)
    with open(package.joinpath("signature"), "wb") as file:
        file.write(der)


def build(namespace) -> PathLike:
    """Generate a full push package."""

    # Make sure the package exists
    package = Path("pushPackage")
    os.makedirs(package, exist_ok=True)

    # Create icons
    icons = package.joinpath("icon.iconset")
    if namespace.icon is None:
        if not icons.exists():  # Allow user to omit argument if icons are already there
            print("Icon set does not already exist")
            raise RuntimeError
    elif not os.path.exists(namespace.icon):
        print("Icon file does not exist!")
        raise RuntimeError
    elif os.path.isfile(namespace.icon):
        build_icons(namespace.icon, icons)
    else:
        shutil.rmtree(icons)
        shutil.copytree(namespace.icon, icons)

    # Copy website metadata
    shutil.copyfile(namespace.website, package.joinpath("website.json"))

    # Build the manifest
    manifest = package.joinpath("manifest.json")
    build_manifest(package, manifest)

    # Build the package signature
    build_signature(manifest, namespace.certificates, package)

    shutil.make_archive("pushPackage", "zip", package)
    return "pushPackage.zip"


def interactive():
    """Run the packager."""

    from argparse import ArgumentParser

    try:

        # Create the parent parser
        parser = ArgumentParser()
        subparsers = parser.add_subparsers(help="packager modes", dest="command")
        subparsers.required = True

        # Create the generator parser
        build_parser = subparsers.add_parser("build", help="generate a static push package")
        build_parser.add_argument("-i", "--icon", dest="icon", help=HELP_IMAGE)
        build_parser.add_argument("-w", "--website", dest="website", required=True, help=HELP_WEBSITE)
        build_parser.add_argument("-c", "--certificates", dest="certificates", required=True, help=HELP_CERTIFICATES)

        # Create the server parser
        server_parser = subparsers.add_parser("serve", help="serve the push package")

        # Parse args and delegate
        namespace = parser.parse_args()
        if namespace is None:
            return
        if namespace.command == "build":
            build(namespace)

    # The error should be printed before this happens
    except RuntimeError:
        return
