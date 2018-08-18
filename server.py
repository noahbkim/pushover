from pushover import get_config, build_package
from flask import Flask, request, send_file

import logging
logging.basicConfig(
    filename="server.log",
    filemode="a",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%m/%d/%y %I:%M:%S %p",
    level=logging.DEBUG)


app = Flask(__name__)


@app.route("/v2/pushPackages/web.com.noahbkim", methods=("POST",))
def get():
    config = app.config["config"]
    build_package(config)
    return send_file("build/package.zip")


@app.route("/v1/log", methods=("POST",))
def log():
    if request.json and "logs" in request.json:
        logging.error(request.json["logs"])
    return ""


def command_line():
    """Run the command line prompt."""

    from argparse import ArgumentParser

    # Create the parent parser
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", dest="config", default=None, help="custom pushover config")

    # Parse args and delegate
    namespace = parser.parse_args()
    app.config["config"] = get_config(namespace.config)
    app.debug = True
    app.run(port=5000)


if __name__ == "__main__":
    command_line()
