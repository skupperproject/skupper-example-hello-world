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

from .main import *

_html_template = """
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

def convert_github_markdown(markdown):
    json = emit_json({"text": markdown})
    content = http_post("https://api.github.com/markdown", json, content_type="application/json")

    # Remove the "user-content-" prefix from internal anchors
    content = content.replace("id=\"user-content-", "id=\"")

    return _html_template.replace("@content@", content)

def update_external_from_github(dir, owner, repo, ref="main"):
    dir = get_absolute_path(dir)
    make_parent_dir(dir)

    url = f"https://github.com/{owner}/{repo}/archive/{ref}.tar.gz"

    with temp_file() as temp:
        assert exists(temp)

        http_get(url, output_file=temp)

        with working_dir(quiet=True):
            extract_archive(temp)

            extracted_dir = list_dir()[0]
            assert is_dir(extracted_dir)

            replace(dir, extracted_dir)
