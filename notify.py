"""A small script for sending notifications to subscribers."""

import ssl
import json
import socket
from OpenSSL import crypto
from argparse import ArgumentParser

from pushover import get_config, load_certificates


# Create the parent parser
parser = ArgumentParser()
parser.add_argument("-c", "--config", dest="config", default=None, help="custom pushover config")

# Parse args and delegate
namespace = parser.parse_args()
config = get_config(namespace.config)
p12 = load_certificates(config)
with open("files/certificates.pem", "wb") as file:
    file.write(crypto.dump_certificate(crypto.FILETYPE_PEM, p12.get_certificate()))
    file.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, p12.get_privatekey()))

title = input("Title: ")
body = input("Body: ")
args = map(lambda x: x.strip(), input("Slug: ").split(","))

message = json.dumps(
{
    "aps": {
        "alert": {
            "title": title,
            "body": body,
            "action": "View"
        },
        "url-args": tuple(args),
    },
})


print(message)

hostname = "ssl://gateway.push.apple.com:2195"
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
# context.load_verify_locations(cafile="files/intermediate.pem")
context.load_cert_chain("files/certificates.pem")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
        ssock.connect(("gateway.push.apple.com", 2195))
        print(ssock.write(message.encode()))
        ssock.close()
