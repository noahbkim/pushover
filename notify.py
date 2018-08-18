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
raw = crypto.dump_certificate(crypto.FILETYPE_PEM, p12.get_certificate()).decode()

title = input("Title: ")
body = input("Body: ")
args = map(lambda x: x.strip(), input("Slug: ").split(","))

message = json.dumps({
    "aps": {
        "title": title,
        "body": body,
        "action": "View"
    },
    "url-args": tuple(args),
})


hostname = "ssl://gateway.push.apple.com:2195"
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations(cadata=raw)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
        ssock.connect(("gateway.push.apple.com", 2195))
        ssock.sendall(message.encode())
        ssock.close()
