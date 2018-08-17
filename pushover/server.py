from flask import Flask, request, send_file


app = Flask(__name__)


@app.route("/v1/pushPackages/web.com.noahbkim", methods=["POST"])
def get():
    send_file("pushPackage.zip")


@app.route("/v1/log", methods=["GET", "POST"])
def log():
    print(request.args)
    print(request.json)
    return ""


def serve():
    app.debug = True
    app.run(port=5000)

