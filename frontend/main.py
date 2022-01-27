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

import asyncio
import os
import json
import uuid
import uvicorn

from animalid import generate_animal_id
from httpx import AsyncClient
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.responses import Response, FileResponse, JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

process_id = f"frontend-{uuid.uuid4().hex[:8]}"

backend_host = os.environ.get("BACKEND_SERVICE_HOST", "hello-world-backend")
backend_port = int(os.environ.get("BACKEND_SERVICE_PORT", 8080))
backend_url = f"http://{backend_host}:{backend_port}"

responses = list()
change_event = None

def log(message):
    print(f"{process_id}: {message}")

async def startup():
    global change_event
    change_event = asyncio.Event()

star = Starlette(debug=True, on_startup=[startup])
star.mount("/static", StaticFiles(directory="static"), name="static")

@star.route("/")

async def get_index(request):
    # user = request.query_params.get("user")

    # if user is None:
    #     user = generate_animal_id()
    #     return RedirectResponse(url=f"?user={user}")

    return FileResponse("static/index.html")

@star.route("/api/notifications")
async def get_notifications(request):
    async def generate():
        while True:
            await change_event.wait()
            yield {"data": "1"}

    return EventSourceResponse(generate())

@star.route("/api/data")
async def get_data(request):
    return JSONResponse(responses);

@star.route("/api/generate-id", methods=["POST"])
async def post_generate_id(request):
    id = generate_animal_id()

    data = {
        "id": id,
        "name": id.replace("-", " ").title(),
        "error": None,
    }

    return JSONResponse(data)

@star.route("/api/say-hello", methods=["POST"])
async def post_say_hello(request):
    request_data = await request.json()

    async with AsyncClient() as client:
        response = await client.post(f"{backend_url}/api/say-hello", json=request_data)

    responses.append({
        "request": request_data["text"],
        "response": response.json()["text"],
    });

    change_event.set()
    change_event.clear()

    return JSONResponse({"error": None})

if __name__ == "__main__":
    host = os.environ.get("FRONTEND_SERVICE_HOST", "0.0.0.0")
    port = int(os.environ.get("FRONTEND_SERVICE_PORT", 8080))

    uvicorn.run(star, host=host, port=port)
