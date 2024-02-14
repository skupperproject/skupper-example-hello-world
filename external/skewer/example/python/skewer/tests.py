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

@test
def plano_commands():
    with working_dir("example"):
        run("./plano")
        run("./plano generate")
        run("./plano render")
        run("./plano clean")

@test
def config_files():
    check_file("config/.github/workflows/main.yaml")
    check_file("config/.gitignore")
    check_file("config/.plano.py")

    parse_yaml(read("config/.github/workflows/main.yaml"))

@test
def generate_readme_():
    with working_dir("example"):
        generate_readme("skewer.yaml", "README.md")
        check_file("README.md")

@test
def run_steps_():
    with working_dir("example"):
        with Minikube("skewer.yaml") as mk:
            run_steps("skewer.yaml", kubeconfigs=mk.kubeconfigs, work_dir=mk.work_dir, debug=True)

@test
def run_steps_demo():
    with working_dir("example"):
        with Minikube("skewer.yaml") as mk:
            run_steps("skewer.yaml", kubeconfigs=mk.kubeconfigs, work_dir=mk.work_dir, debug=True)

@test
def run_steps_debug():
    with working_dir("example"):
        with expect_error():
            with working_env(SKEWER_FAIL=1):
                with Minikube("skewer.yaml") as mk:
                    run_steps("skewer.yaml", kubeconfigs=mk.kubeconfigs, work_dir=mk.work_dir, debug=True)

if __name__ == "__main__":
    import sys
    run_tests(sys.modules[__name__])
