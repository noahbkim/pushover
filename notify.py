"""A small script for sending notifications to subscribers."""

import socket
import json


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

sock = socket.create_connection(("gateway.push.apple.com", 2195))
sock.sendall(message.encode())
sock.close()
