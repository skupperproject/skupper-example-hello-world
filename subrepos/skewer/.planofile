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

from skewer import *

@command(passthrough=True)
def test(coverage=False, passthrough_args=[]):
    clean()

    args = " ".join(passthrough_args)

    if coverage:
        check_program("coverage")

        with working_env(PYTHONPATH="python"):
            run(f"coverage run --source skewer -m skewer.tests {args}")

        run("coverage report")
        run("coverage html")

        print(f"file:{get_current_dir()}/htmlcov/index.html")
    else:
        with working_env(PYTHONPATH="python"):
            run(f"python -m skewer.tests {args}")

@command
def render():
    """
    Render README.html from README.md
    """
    check_program("pandoc")

    run(f"pandoc -o README.html README.md")

    print(f"file:{get_real_path('README.html')}")

@command
def clean():
    remove(join("python", "__pycache__"))
    remove(join("test-example", "python", "__pycache__"))
    remove("README.html")
    remove("htmlcov")
    remove(".coverage")
