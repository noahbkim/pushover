"""The pushover module.

This library is intended to completely equip the user to deal with the
poorly-documented API Apple has provided for making push notifications
through Safari. See the README for more information on setup.
"""


import os
import yaml
import shutil
import json
from OpenSSL import crypto
from pathlib import Path
from typing import Union
from hashlib import sha512


import logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%m/%d/%y %I:%M:%S %p",
    level=logging.DEBUG)


PathLike = Union[Path, str]


CONFIGURATION_PATH = Path(os.getcwd()).joinpath("pushover.yml")
BUILD_PATH = Path(os.getcwd()).joinpath("build")


DEFAULT_CONFIGURATION = """\
files:
  certificatesPath: 
  iconsPath: 

website:
  websiteName: 
  websitePushID: 
  allowedDomains:
  urlFormatString:  
  webServiceURL: 
"""


IMAGE_SIZES = (16, 32, 128)
IMAGES = tuple(f"icon_{size}x{size}{multiplier}.png" for size in IMAGE_SIZES for multiplier in ("", "@2x"))
MANIFEST = tuple("icon.iconset/" + image for image in IMAGES) + ("website.json",)


def get_config(path: PathLike=None):
    """Get the user configuration."""

    path = path or CONFIGURATION_PATH
    logging.debug("loading configuration")
    try:
        with open(path) as file:
            return yaml.load(file)
    except FileNotFoundError:
        logging.info("configuration file not found, creating...")
        with open(path, "w") as file:
            file.write(DEFAULT_CONFIGURATION)
        with open(path) as file:
            return yaml.load(file)


def copy_icons(config: dict, build: Path):
    """Assemble and examine all configured files into the build path."""

    # Make the icon directory
    icons = build.joinpath("icon.iconset")
    os.makedirs(str(icons))
    try:
        source = Path(config["files"]["iconsPath"])
    except KeyError:
        print("Error locating iconsPath in configuration!")
        raise RuntimeError
    except TypeError:
        print("Missing iconsPath in configuration!")
        raise RuntimeError

    # Copy only the images we want into the directory
    for image in IMAGES:
        path = source.joinpath(image)
        try:
            shutil.copy(str(path), str(icons))
        except FileNotFoundError:
            print(f"Missing {image}!")
            raise RuntimeError


def make_website(config: dict, website: Path, authentication_token=None):
    """Make the website JSON metadata."""

    logging.debug("creating website metadata...")

    # Create the dictionary
    try:
        base = config["website"]
    except KeyError:
        print("Error locating website metadata in configuration!")
        raise RuntimeError
    base["authenticationToken"] = authentication_token or ""

    # Write to the build directory
    with website.open("w") as file:
        json.dump(base, file, indent=4)


def sha512_file(path: PathLike):
    """Get the sha256 checksum of a file."""

    with open(path, "rb") as file:
        # This should iterate through large blocks of the file to
        # prevent memory flooding, however the sha512.update() is not
        # consistent with reading the file in once for some reason.
        # It's okay though because the files are small :)
        return sha512(file.read()).hexdigest()


def make_manifest(build: Path, manifest: Path):
    """Make the manifest file."""

    logging.debug("generating the package manifest...")

    # Package the manifest dictionary with everything
    output = {}
    for file in MANIFEST:
        output[file] = {"hashType": "sha512", "hashValue": sha512_file(build.joinpath(file))}

    # Write to file
    with manifest.open("w") as file:
        raw = json.dumps(output, indent=4)
        raw = raw.replace("/", "\\/")  # Apple requires escaped forward slashes here for some reason
        file.write(raw)


def make_signature(config: dict, manifest: Path, certificates: Path, signature: Path):
    """Package the signature file for the package."""

    logging.debug("signing the manifest...")

    # Read the certificates
    with certificates.open("rb") as file:
        raw = file.read()
    try:
        p12 = crypto.load_pkcs12(raw)
    except crypto.Error:

        # Check if the config has a certificatesPassword
        if "files" in config and "certificatesPassword" in config["files"]:
            password = config["files"]["certificatesPassword"].encode()
        else:
            import getpass
            password = getpass.getpass("Enter the password to your developer certificates: ").encode()
        p12 = crypto.load_pkcs12(raw, password)

    # https://stackoverflow.com/questions/33634379/pkcs-7-detached-signature-with-python-and-pyopenssl/33726421#33726421
    # How the fuck did this guy even figure this out?

    # Create the memory buffer for the signature
    with manifest.open("rb") as file:
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
    with signature.open("wb") as file:
        file.write(der)


def build_package(config: dict, authentication_token: str=None):
    """Build a push package with an optional authenticationToken."""

    # Figure out some paths
    build_path = BUILD_PATH
    source_path = build_path.joinpath("source")
    website_path = source_path.joinpath("website.json")
    manifest_path = source_path.joinpath("manifest.json")
    signature_path = source_path.joinpath("signature")
    package_path = build_path.joinpath("package.zip")

    # Create the stage
    logging.debug("clearing and creating build directory")
    try:
        shutil.rmtree(BUILD_PATH)
    except FileNotFoundError:
        pass
    os.makedirs(str(BUILD_PATH))

    # Copy icons, make website, make manifest
    copy_icons(config, source_path)
    make_website(config, website_path, authentication_token=authentication_token)
    make_manifest(source_path, manifest_path)

    # Get the certificate path and sign the manifest
    try:
        certificates = Path(config["files"]["certificatesPath"])
    except KeyError:
        print("Error locating certificatesPath in configuration!")
        raise RuntimeError
    except TypeError:
        print("Missing certificatesPath in configuration!")
        raise RuntimeError
    make_signature(config, manifest_path, certificates, signature_path)

    # Zip everything up
    shutil.make_archive("package", "zip", root_dir=source_path)
    try:
        shutil.rmtree(package_path)
    except FileNotFoundError:
        pass
    shutil.move("package.zip", BUILD_PATH)


def command_line():
    """Run the command line prompt."""

    from argparse import ArgumentParser

    # Create the parent parser
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", dest="config", default=None, help="custom pushover config")
    parser.add_argument("-t", "--token", dest="token", default=None, help="website authentication token")

    # Parse args and delegate
    namespace = parser.parse_args()

    try:

        # Build the package
        config = get_config(namespace.config)
        build_package(config)

    except RuntimeError:
        pass
    except KeyError:
        print("Exiting...")


if __name__ == "__main__":
    command_line()
