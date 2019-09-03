import os

from flask import Flask, Response
from threading import Lock

app = Flask(__name__)

host = os.environ.get("BACKEND_SERVICE_HOST", "localhost")
port = int(os.environ.get("BACKEND_SERVICE_PORT", 8080))

lock = Lock()
count = 0

@app.route("/api/hello")
def hello():
    global count

    with lock:
        count += 1

    return Response(f"Hello {count}", mimetype="text/plain")

if __name__ == "__main__":
    app.run(host=host, port=port)
