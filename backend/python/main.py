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

import os
import uvicorn

from thingid import generate_thing_id
from starlette.applications import Starlette
from starlette.responses import JSONResponse

name = generate_thing_id().replace("-", " ").title()
pod = os.environ.get("HOSTNAME", "backend")

star = Starlette(debug=True)

@star.route("/api/hello", methods=["POST"])
async def hello(request):
    request_data = await request.json()
    requestor = request_data["name"]

    response_data = {
        "text": f"Hi, {requestor}.  I am {name} ({pod}).",
        "name": name,
    }

    return JSONResponse(response_data)

if __name__ == "__main__":
    host = os.environ.get("BACKEND_SERVICE_HOST", "0.0.0.0")
    port = int(os.environ.get("BACKEND_SERVICE_PORT", 8080))

    uvicorn.run(star, host=host, port=port)
