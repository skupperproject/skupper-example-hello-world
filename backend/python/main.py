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

import argparse
import os
import thingid
import uvicorn

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response

name = thingid.generate_id().replace("-", " ").title()
pod = os.environ.get("HOSTNAME", "backend")
star = Starlette(debug=True)

@star.route("/api/hello", methods=["GET", "POST"])
async def hello(request):
    if request.method == "GET":
        return Response(f"Hello, stranger.  I am {name} ({pod}).\n", 200)

    request_data = await request.json()
    requestor = request_data["name"]

    response_data = {
        "text": f"Hi, {requestor}.  I am {name} ({pod}).",
        "name": name,
    }

    return JSONResponse(response_data)

@star.route("/api/health", methods=["GET"])
async def health(request):
    return Response("OK\n", 200)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--ssl-keyfile", default="")
    parser.add_argument("--ssl-certfile", default="")
    parser.add_argument("--ssl-ca-certs", default="")
    parser.add_argument("--ssl-cert-reqs", type=int, default=0)

    args = parser.parse_args()

    uvicorn.run(star, host=args.host, port=args.port, ssl_keyfile=args.ssl_keyfile, ssl_certfile=args.ssl_certfile, ssl_ca_certs=args.ssl_ca_certs, ssl_cert_reqs=args.ssl_cert_reqs)
