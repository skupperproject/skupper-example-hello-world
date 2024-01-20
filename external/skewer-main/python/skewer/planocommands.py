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
from skewer import *

_render_template = """
<html>
  <head>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.0/github-markdown.min.css"
          integrity="sha512-h/laqMqQKUXxFuu6aLAaSrXYwGYQ7qk4aYCQ+KJwHZMzAGaEoxMM6h8C+haeJTU1V6E9jrSUnjpEzX23OmV/Aw=="
          crossorigin="anonymous" referrerpolicy="no-referrer"/>
    <style>
        .markdown-body {
            box-sizing: border-box;
            min-width: 200px;
            max-width: 980px;
            margin: 0 auto;
            padding: 45px;
        }

        @media (max-width: 767px) {
           .markdown-body {
               padding: 15px;
           }
        }
    </style>
  </head>
  <body>
    <article class="markdown-body">

@content@

    </article>
  </body>
</html>
""".strip()

_debug_param = CommandParameter("debug", help="Produce extra debug output on failure")

@command
def generate(output="README.md"):
    """
    Generate README.md from the data in skewer.yaml
    """
    generate_readme("skewer.yaml", output)

@command
def render(verbose=False, quiet=False):
    """
    Render README.html from README.md
    """
    generate()

    markdown = read("README.md")
    data = {"text": markdown}
    json = emit_json(data)
    content = http_post("https://api.github.com/markdown", json, content_type="application/json")
    html = _render_template.replace("@content@", content)

    write("README.html", html)

    if not quiet:
        print(f"file:{get_real_path('README.html')}")

@command
def clean():
    remove(find(".", "__pycache__"))
    remove("README.html")

@command(parameters=[_debug_param])
def run_(*kubeconfigs, debug=False):
    """
    Run the example steps

    If no kubeconfigs are provided, Skewer starts a local Minikube
    instance and runs the steps using it.
    """
    if not kubeconfigs:
        with Minikube("skewer.yaml") as mk:
            run_steps("skewer.yaml", kubeconfigs=mk.kubeconfigs, work_dir=mk.work_dir, debug=debug)
    else:
        run_steps("skewer.yaml", kubeconfigs=kubeconfigs, debug=debug)

@command(parameters=[_debug_param])
def demo(*kubeconfigs, debug=False):
    """
    Run the example steps and pause for a demo before cleaning up
    """
    with working_env(SKEWER_DEMO=1):
        run_(*kubeconfigs, debug=debug)

@command(parameters=[_debug_param])
def test_(debug=False):
    """
    Test README generation and run the steps on Minikube
    """
    generate(output=make_temp_file())
    run_(debug=debug)

@command
def update_skewer():
    """
    Update the embedded Skewer repo and GitHub workflow

    This results in local changes to review and commit.
    """
    check_program("curl")

    make_dir("external")
    remove("external/skewer-main")
    run("curl -sfL https://github.com/skupperproject/skewer/archive/main.tar.gz | tar -C external -xz", shell=True)
    copy("external/skewer-main/config/.github/workflows/main.yaml", ".github/workflows/main.yaml")
