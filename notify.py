"""A small script for sending notifications to subscribers."""

import ssl
import json
import socket
import binascii
import struct
from pathlib import Path
from OpenSSL import crypto
from argparse import ArgumentParser

from pushover import get_config, load_certificates


# Create the parent parser
parser = ArgumentParser()
parser.add_argument("-c", "--config", dest="config", default=None, help="custom pushover config")

# Parse args and delegate
namespace = parser.parse_args()
config = get_config(namespace.config)
certificates = Path(config["files"]["certificatesPath"].rstrip("p12") + "pem")

# Check if the certificate needs to be converted
if not certificates.exists():
    p12 = load_certificates(config)
    with open("files/certificates.pem", "wb") as file:
        file.write(crypto.dump_certificate(crypto.FILETYPE_PEM, p12.get_certificate()))
        file.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, p12.get_privatekey()))

# Get input for the payload
title = input("Title: ")
body = input("Body: ")
args = map(lambda x: x.strip(), input("Slug: ").split(","))

# Generate the payload body
message = json.dumps({
    "aps": {
        "alert": {
            "title": title,
            "body": body,
            "action": "View"
        },
        "url-args": tuple(args),
    },
})

# Open an SSL context
hostname = "ssl://gateway.push.apple.com:2195"
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain("files/certificates.pem")

# Open an SSL socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
        ssock.connect(("gateway.push.apple.com", 2195))

        # Send a message to all devices
        with open("devices.txt") as file:
            for line in file:
                device = line.strip()

                # Pack the device
                device_pack = binascii.a2b_hex(device)
                device_payload = struct.pack(">H", len(device_pack)) + device_pack
                message_payload = struct.pack(">H", len(message)) + message.encode()
                payload = b"\x00" + device_payload + message_payload

                # Send
                print("Sent", ssock.write(payload), "bytes!")

        ssock.close()
