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

import skewer.tests

from skewer import *

@command(passthrough=True)
def test(verbose=False, quiet=False, passthrough_args=[]):
    args = ["-m", "skewer.tests"]

    if verbose:
        args.append("--verbose")

    if quiet:
        args.append("--quiet")

    args += passthrough_args

    PlanoTestCommand().main(args=args)

@command
def coverage(verbose=False, quiet=False):
    """
    Run the tests and measure code coverage
    """
    check_program("coverage")

    with working_env(PYTHONPATH="python"):
        run("coverage run --source skewer -m skewer.tests")

    run("coverage report")
    run("coverage html")

    if not quiet:
        print(f"file:{get_current_dir()}/htmlcov/index.html")

@command
def render(verbose=False, quiet=False):
    """
    Render README.html from README.md
    """
    check_program("pandoc")

    run(f"pandoc -o README.html README.md")

    if not quiet:
        print(f"file:{get_real_path('README.html')}")

@command
def clean():
    remove(find(".", "__pycache__"))
    remove("README.html")
    remove("htmlcov")
    remove(".coverage")

@command
def update_plano():
    """
    Update the embedded Plano repo
    """
    make_dir("external")
    remove("external/plano-main")
    run("curl -sfL https://github.com/ssorj/plano/archive/main.tar.gz | tar -C external -xz", shell=True)
