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

def check_environment():
    check_program("kubectl")
    check_program("skupper")
    check_program("curl")

# Eventually Kubernetes will make this nicer:
# https://github.com/kubernetes/kubernetes/pull/87399
# https://github.com/kubernetes/kubernetes/issues/80828
# https://github.com/kubernetes/kubernetes/issues/83094
def await_resource(group, name, namespace=None):
    base_command = "kubectl"

    if namespace is not None:
        base_command = f"{base_command} -n {namespace}"

    notice(f"Waiting for {group}/{name} to become available")

    for i in range(180):
        sleep(1)

        if run(f"{base_command} get {group}/{name}", check=False).exit_code == 0:
            break
    else:
        fail(f"Timed out waiting for {group}/{name}")

    if group == "deployment":
        try:
            run(f"{base_command} wait --for condition=available --timeout 180s {group}/{name}")
        except:
            run(f"{base_command} logs {group}/{name}")
            raise

def await_link(name, namespace=None):
    skupper_base_command = "skupper"
    kubectl_base_command = "kubectl"

    if namespace is not None:
        skupper_base_command = f"{skupper_base_command} -n {namespace}"
        kubectl_base_command = f"{kubectl_base_command} -n {namespace}"

    try:
        run(f"{skupper_base_command} link status --wait 180 {name}")
    except:
        run(f"{kubectl_base_command} logs deployment/skupper-router")
        raise

def get_ingress_ip(group, name, namespace=None):
    await_resource(group, name, namespace=namespace)

    base_command = "kubectl"

    if namespace is not None:
        base_command = f"{base_command} -n {namespace}"

    for i in range(180):
        sleep(1)

        if call(f"{base_command} get {group}/{name} -o jsonpath='{{.status.loadBalancer.ingress}}'") != "":
            break
    else:
        fail(f"Timed out waiting for ingress for {group}/{name}")

    return call(f"{base_command} get {group}/{name} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'")
