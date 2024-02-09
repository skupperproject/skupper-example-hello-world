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

from plano import *
from plano.github import *

image_tag = "quay.io/skupper/hello-world-frontend"

@command
def build(no_cache=False):
    no_cache_arg = "--no-cache" if no_cache else ""

    run(f"podman build {no_cache_arg} --format docker -t {image_tag} .")

@command
def run_():
    run(f"podman run --net host {image_tag} --host localhost --port 8080 --backend http://localhost:8081")

@command
def test():
    # The backend must be running on port 8081
    check_port(8081)

    with start(f"podman run --net host {image_tag} python python/main.py --host localhost --port 8080 --backend http://localhost:8081"):
        await_port(8080)

        print(http_get("http://localhost:8081/api/health"))
        print(http_get("http://localhost:8081/api/hello"))

        print(len(http_get("http://localhost:8080/")))
        print()
        print(http_get_json("http://localhost:8080/api/data"))
        print()
        print(http_post_json("http://localhost:8080/api/hello", {"name": "Obtuse Ocelot", "text": "Bon jour"}))
        print()

@command
def debug():
    run(f"podman run -it --net host --entrypoint /bin/sh {image_tag}")

@command
def push():
    run("podman login quay.io")
    run(f"podman push {image_tag}")

@command
def update_gesso():
    update_external_from_github("static/gesso", "ssorj", "gesso")
