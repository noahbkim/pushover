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


def sha512_file(path: PathLike):
    """Get the sha256 checksum of a file."""

    with open(path, "rb") as file:
        return sha512(file.read()).hexdigest()  # This should iterate large blocks but the files are small


def package_icons(path: PathLike, icons: PathLike):
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
        resized2.save(icons.joinpath(f"icon_{size}x{size}@2x.png"))


def package_manifest(package: PathLike, manifest: PathLike):
    """Get the SHA256 sums of all of the items in the package."""

    # Package the manifest dictionary with everything
    output = {}
    files = (
        str(os.path.join(dp, file))
        for dp, dn, files in os.walk(package)
        for file in files
        if not file.startswith("."))
    for file in files:
        name = file.split(os.sep, 1)[1]
        output[name] = {"hashType": "sha512", "hashValue": sha512_file(file)}

    # Write to file
    with open(manifest, "w") as file:
        raw = json.dumps(output, indent=4)
        raw = raw.replace("/", "\\/")
        file.write(raw)


def package_signature(manifest: PathLike, certificates: PathLike, package: PathLike):
    """Package the signature file for the package."""

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


def package(namespace) -> PathLike:
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
        package_icons(namespace.icon, icons)
    else:
        shutil.rmtree(icons)
        shutil.copytree(namespace.icon, icons)

    # Copy website metadata
    shutil.copyfile(namespace.website, package.joinpath("website.json"))

    # Package the manifest
    manifest = package.joinpath("manifest.json")
    package_manifest(package, manifest)

    # Package the package signature
    package_signature(manifest, namespace.certificates, package)

    shutil.make_archive("pushPackage", "zip", package)
    return "pushPackage.zip"
