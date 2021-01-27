#!/usr/bin/python3

from plano import *

ENV["BACKEND_SERVICE_HOST"] = "localhost"
ENV["BACKEND_SERVICE_PORT"] = backend_port = str(get_random_port())
ENV["FRONTEND_SERVICE_PORT"] = frontend_port = str(get_random_port())

backend_url = f"http://localhost:{backend_port}/api/hello"
frontend_url = f"http://localhost:{frontend_port}/"

with start("python3 backend/app.py") as backend:
    with start("python3 frontend/app.py") as frontend:
        sleep(0.5)

        print(http_get(backend_url))
        print(http_get(backend_url))
        print(http_get(backend_url))

        print(http_get(frontend_url))
        print(http_get(frontend_url))
        print(http_get(frontend_url))

        print("SUCCESS")
