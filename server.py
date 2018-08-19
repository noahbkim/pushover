from argparse import ArgumentParser
from flask import Flask, request, send_file

from pushover import get_config, build_package

import logging
logging.basicConfig(
    filename="server.log",
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%m/%d/%y %I:%M:%S %p",
    level=logging.DEBUG)


app = Flask(__name__)


# Create the parent parser
parser = ArgumentParser()
parser.add_argument("-c", "--config", dest="config", default=None, help="custom pushover config")

# Parse args and delegate
namespace = parser.parse_args()

try:
    config = get_config(namespace.config)
except RuntimeError:
    import sys
    sys.exit(0)


# Grab the app ID
push_id = config["website"]["websitePushID"]


@app.route("/v2/pushPackages/" + push_id, methods=("POST",))
def get():
    """Called when a user might subscribe to the notifications."""

    build_package(config)
    return send_file("build/package.zip")


@app.route("/v1/devices/<device_token>/registrations/" + push_id, methods=("POST",))
def register(device_token):
    """Called when a user registers."""

    logging.info(f"user {device_token[:8]}... has registered!")
    with open("devices.txt", "a") as file:
        file.write(device_token + "\n")
    return ""


@app.route("/v1/devices/<device_token>/registrations/" + push_id, methods=("DELETE",))
def unregister(device_token):
    """Called when a user unregisters."""

    logging.info(f"user {device_token[:8]}... has unregistered!")
    with open("devices.txt") as file:
        lines = file.readlines()
    with open("devices.txt", "w") as file:
        for line in lines:
            if not line.startswith(device_token):
                file.write(line)


@app.route("/v1/log", methods=("POST",))
def log():
    """Called when Safari encounters an error."""

    print(request.json)
    if request.json and "logs" in request.json:
        for error in request.json["logs"]:
            logging.error(error)
    return ""


if __name__ == "__main__":
    app.run(port=5000)
