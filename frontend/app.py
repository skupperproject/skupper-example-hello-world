import os
import requests

from flask import Flask, Response

app = Flask(__name__)

host = os.environ.get("FRONTEND_SERVICE_HOST", "localhost")
port = int(os.environ.get("FRONTEND_SERVICE_PORT", 8080))

backend_host = os.environ.get("BACKEND_SERVICE_HOST", "localhost")
backend_port = os.environ["BACKEND_SERVICE_PORT"]

@app.route('/')
def root():
    result = requests.get(f"http://{backend_host}:{backend_port}/api/hello")

    return Response(f"The backend says '{result.text}'", mimetype="text/plain")

if __name__ == '__main__':
    app.run(host=host, port=port)
