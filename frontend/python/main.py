#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import animalid
import argparse
import asyncio
import os
import json
import uuid
import uvicorn

from httpx import AsyncClient, HTTPError
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.staticfiles import StaticFiles

process_id = f"frontend-{uuid.uuid4().hex[:8]}"
records = list()

async def startup():
    global change_event
    change_event = asyncio.Event()

star = Starlette(debug=True, on_startup=[startup])
star.mount("/static", StaticFiles(directory="static"), name="static")

@star.route("/")
async def index(request):
    return FileResponse("static/index.html")

@star.route("/api/data")
async def data(request):
    return JSONResponse(records);

@star.route("/api/notifications")
async def notifications(request):
    async def generate():
        while True:
            await change_event.wait()
            yield {"data": "1"}

    return EventSourceResponse(generate())

@star.route("/api/generate-id", methods=["POST"])
async def generate_id(request):
    id = animalid.generate_id()

    response_data = {
        "id": id,
        "name": id.replace("-", " ").title(),
    }

    return JSONResponse(response_data)

@star.route("/api/hello", methods=["POST"])
async def hello(request):
    request_data = await request.json()

    name = request_data["name"]
    text = request_data["text"]

    backend_request, backend_response, backend_error = await send_greeting(name, text)

    record = {
        "request": backend_request,
        "response": backend_response,
        "error": backend_error,
    }

    records.append(record);

    change_event.set()
    change_event.clear()

    return JSONResponse(backend_response)

async def send_greeting(name, text):
    request_data = {
        "name": name,
        "text": text,
    }

    async with AsyncClient(verify=verify, cert=cert) as client:
        try:
            response = await client.post(f"{backend_url}/api/hello", json=request_data)
        except HTTPError as e:
            return request_data, None, str(e)

    response_data = response.json()

    return request_data, response_data, None

@star.route("/api/health", methods=["GET"])
async def health(request):
    await send_greeting("Testy Tiger", "Hi")

    return Response("OK\n", 200)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--backend", metavar="URL", default="http://backend:8080")
    parser.add_argument("--ssl-keyfile", default="")
    parser.add_argument("--ssl-certfile", default="")
    parser.add_argument("--ssl-ca-certs", default="")

    args = parser.parse_args()

    global backend_url
    backend_url = args.backend

    global cert
    if args.ssl_certfile and args.ssl_keyfile:
        cert = (args.ssl_certfile, args.ssl_keyfile)

    global verify
    if args.ssl_ca_certs:
        verify = args.ssl_ca_certs
    else:
        verify = True

    uvicorn.run(star, host=args.host, port=args.port)
