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

_standard_steps_yaml = read(join(get_parent_dir(__file__), "standardsteps.yaml"))
_standard_steps = parse_yaml(_standard_steps_yaml)

_example_suite_para = """
This example is part of a [suite of examples][examples] showing the
different ways you can use [Skupper][website] to connect services
across cloud providers, data centers, and edge sites.

[website]: https://skupper.io/
[examples]: https://skupper.io/examples/index.html
""".strip()

_standard_prerequisites = """
* The `kubectl` command-line tool, version 1.15 or later
  ([installation guide][install-kubectl])

* Access to at least one Kubernetes cluster, from [any provider you
  choose][kube-providers]

[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[kube-providers]: https://skupper.io/start/kubernetes.html
""".strip()

_standard_next_steps = """
Check out the other [examples][examples] on the Skupper website.
""".strip()

_about_this_example = """
This example was produced using [Skewer][skewer], a library for
documenting and testing Skupper examples.

[skewer]: https://github.com/skupperproject/skewer

Skewer provides utility functions for generating the README and
running the example steps.  Use the `./plano` command in the project
root to see what is available.

To quickly stand up the example using Minikube, try the `./plano demo`
command.
""".strip()

def check_environment():
    check_program("base64")
    check_program("curl")
    check_program("kubectl")
    check_program("skupper")

# Eventually Kubernetes will make this nicer:
# https://github.com/kubernetes/kubernetes/pull/87399
# https://github.com/kubernetes/kubernetes/issues/80828
# https://github.com/kubernetes/kubernetes/issues/83094
def await_resource(group, name, timeout=180):
    notice(f"Waiting for {group}/{name} to become available")

    for i in range(timeout):
        sleep(1)

        if run(f"kubectl get {group}/{name}", check=False).exit_code == 0:
            break
    else:
        fail(f"Timed out waiting for {group}/{name}")

    if group == "deployment":
        try:
            run(f"kubectl wait --for condition=available --timeout {timeout}s {group}/{name}")
        except:
            run(f"kubectl logs {group}/{name}")
            raise

def await_external_ip(group, name, timeout=180):
    await_resource(group, name, timeout=timeout)

    for i in range(timeout):
        sleep(1)

        if call(f"kubectl get {group}/{name} -o jsonpath='{{.status.loadBalancer.ingress}}'") != "":
            break
    else:
        fail(f"Timed out waiting for external IP for {group}/{name}")

    return call(f"kubectl get {group}/{name} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'")

def run_steps_minikube(skewer_file, debug=False):
    check_environment()
    check_program("minikube")

    skewer_data = read_yaml(skewer_file)
    kubeconfigs = list()

    for site in skewer_data["sites"]:
        kubeconfigs.append(make_temp_file())

    try:
        run("minikube -p skewer start")

        for kubeconfig in kubeconfigs:
            with working_env(KUBECONFIG=kubeconfig):
                run("minikube -p skewer update-context")
                check_file(ENV["KUBECONFIG"])

        with open("/tmp/minikube-tunnel-output", "w") as tunnel_output_file:
            with start("minikube -p skewer tunnel", output=tunnel_output_file):
                run_steps(skewer_file, *kubeconfigs, debug=debug)
    finally:
        run("minikube -p skewer delete")

def run_steps(skewer_file, *kubeconfigs, debug=False):
    check_environment()

    skewer_data = read_yaml(skewer_file)
    work_dir = make_temp_dir()

    for i, site in enumerate(skewer_data["sites"].values()):
        site["kubeconfig"] = kubeconfigs[i]

    _apply_standard_steps(skewer_data)

    try:
        for step in skewer_data["steps"]:
            if step.get("id") == "cleaning_up":
                continue

            _run_step(work_dir, skewer_data, step)

        if "SKEWER_DEMO" in ENV:
            _pause_for_demo(work_dir, skewer_data)
    except:
        if debug:
            print("TROUBLE!")
            print("-- Start of debug output")

            for site_name, site_data in skewer_data["sites"].items():
                kubeconfig = site_data["kubeconfig"].replace("~", work_dir)
                print(f"---- Debug output for site '{site_name}'")

                with working_env(KUBECONFIG=kubeconfig):
                    run("kubectl get services", check=False)
                    run("kubectl get deployments", check=False)
                    run("kubectl get statefulsets", check=False)
                    run("kubectl get pods", check=False)
                    run("skupper version", check=False)
                    run("skupper status", check=False)
                    run("skupper link status", check=False)
                    run("skupper service status", check=False)
                    run("skupper gateway status", check=False)
                    run("skupper network status", check=False)
                    run("skupper debug events", check=False)
                    run("kubectl logs deployment/skupper-router", check=False)
                    run("kubectl logs deployment/skupper-service-controller", check=False)

            print("-- End of debug output")

        raise
    finally:
        for step in skewer_data["steps"]:
            if step.get("id") == "cleaning_up":
                _run_step(work_dir, skewer_data, step, check=False)
                break


def _pause_for_demo(work_dir, skewer_data):
    first_site_name, first_site_data = list(skewer_data["sites"].items())[0]
    first_site_kubeconfig = first_site_data["kubeconfig"].replace("~", work_dir)
    frontend_url = None

    with working_env(KUBECONFIG=first_site_kubeconfig):
        console_ip = await_external_ip("service", "skupper")
        console_url = f"https://{console_ip}:8080/"
        password_data = call("kubectl get secret skupper-console-users -o jsonpath='{.data.admin}'")
        password = base64_decode(password_data).decode("ascii")

        if run("kubectl get service/frontend", check=False, output=DEVNULL).exit_code == 0:
            if call("kubectl get service/frontend -o jsonpath='{.spec.type}'") == "LoadBalancer":
                frontend_ip = await_external_ip("service", "frontend")
                frontend_url = f"http://{frontend_ip}:8080/"

    print()
    print("Demo time!")
    print()
    print("Sites:")

    for site_name, site_data in skewer_data["sites"].items():
        kubeconfig = site_data["kubeconfig"].replace("~", work_dir)
        print(f"  {site_name}: export KUBECONFIG={kubeconfig}")

    if frontend_url:
        print()
        print(f"Frontend URL:     {frontend_url}")

    print()
    print(f"Console URL:      {console_url}")
    print( "Console user:     admin")
    print(f"Console password: {password}")
    print()

    if "SKEWER_DEMO_NO_WAIT" not in ENV:
        while input("Are you done (yes)? ") != "yes": # pragma: nocover
            pass

def _run_step(work_dir, skewer_data, step_data, check=True):
    if "commands" not in step_data:
        return

    if "title" in step_data:
        notice("Running step '{}'", step_data["title"])

    items = step_data["commands"].items()

    for site_name, commands in items:
        kubeconfig = skewer_data["sites"][site_name]["kubeconfig"].replace("~", work_dir)

        with working_env(KUBECONFIG=kubeconfig):
            for command in commands:
                if command.get("apply") == "readme":
                    continue

                if "run" in command:
                    run(command["run"].replace("~", work_dir), shell=True, check=check)

                if "await" in command:
                    resources = command["await"]

                    if isinstance(resources, str):
                        resources = (resources,)

                    for resource in resources:
                        group, name = resource.split("/", 1)
                        await_resource(group, name)

                if "await_external_ip" in command:
                    resources = command["await_external_ip"]

                    if isinstance(resources, str):
                        resources = (resources,)

                    for resource in resources:
                        group, name = resource.split("/", 1)
                        await_external_ip(group, name)

def generate_readme(skewer_file, output_file):
    skewer_data = read_yaml(skewer_file)
    out = list()

    out.append(f"# {skewer_data['title']}")
    out.append("")

    if "github_actions_url" in skewer_data:
        url = skewer_data["github_actions_url"]
        out.append(f"[![main]({url}/badge.svg)]({url})")
        out.append("")

    if "subtitle" in skewer_data:
        out.append(f"#### {skewer_data['subtitle']}")
        out.append("")

    out.append(_example_suite_para)
    out.append("")
    out.append("#### Contents")
    out.append("")

    if "overview" in skewer_data:
        out.append("* [Overview](#overview)")

    out.append("* [Prerequisites](#prerequisites)")

    _apply_standard_steps(skewer_data)

    for i, step_data in enumerate(skewer_data["steps"], 1):
        if step_data.get("numbered", True):
            title = f"Step {i}: {step_data['title']}"
        else:
            title = step_data['title']

        fragment = replace(title, r"[ -]", "_")
        fragment = replace(fragment, r"[\W]", "")
        fragment = replace(fragment, "_", "-")
        fragment = fragment.lower()

        out.append(f"* [{title}](#{fragment})")

    if "summary" in skewer_data:
        out.append("* [Summary](#summary)")

    if "next_steps" in skewer_data:
        out.append("* [Next steps](#next-steps)")

    out.append("* [About this example](#about-this-example)")
    out.append("")

    if "overview" in skewer_data:
        out.append("## Overview")
        out.append("")
        out.append(skewer_data["overview"].strip())
        out.append("")

    prerequisites = _standard_prerequisites

    if "prerequisites" in skewer_data:
        prerequisites = skewer_data["prerequisites"].strip()

    out.append("## Prerequisites")
    out.append("")
    out.append(prerequisites)
    out.append("")

    for i, step_data in enumerate(skewer_data["steps"], 1):
        notice("Generating step '{}'", step_data["title"])

        if step_data.get("numbered", True):
            title = f"Step {i}: {step_data['title']}"
        else:
            title = step_data["title"]


        out.append(f"## {title}")
        out.append("")
        out.append(_generate_readme_step(skewer_data, step_data))
        out.append("")

    if "summary" in skewer_data:
        out.append("## Summary")
        out.append("")
        out.append(skewer_data["summary"].strip())
        out.append("")

    next_steps = _standard_next_steps

    if "next_steps" in skewer_data:
        next_steps = skewer_data["next_steps"].strip()

    out.append("## Next steps")
    out.append("")
    out.append(next_steps)
    out.append("")

    out.append("## About this example")
    out.append("")
    out.append(_about_this_example)
    out.append("")

    write(output_file, "\n".join(out).strip() + "\n")

def _generate_readme_step(skewer_data, step_data):
    out = list()

    if "preamble" in step_data:
        out.append(step_data["preamble"].strip())
        out.append("")

    if "commands" in step_data:
        items = step_data["commands"].items()

        for i, item in enumerate(items):
            site_name, commands = item
            namespace = skewer_data["sites"][site_name]["namespace"]
            outputs = list()

            out.append(f"_**Console for {namespace}:**_")
            out.append("")
            out.append("~~~ shell")

            for command in commands:
                if command.get("apply") == "test":
                    continue

                if "run" in command:
                    out.append(command["run"])

                if "output" in command:
                    assert "run" in command, command

                    outputs.append((command["run"], command["output"]))

            out.append("~~~")
            out.append("")

            if outputs:
                out.append("_Sample output:_")
                out.append("")
                out.append("~~~ console")
                out.append("\n\n".join((f"$ {run}\n{output.strip()}" for run, output in outputs)))
                out.append("~~~")
                out.append("")

    if "postamble" in step_data:
        out.append(step_data["postamble"].strip())

    return "\n".join(out).strip()

def _apply_standard_steps(skewer_data):
    notice("Applying standard steps")

    for step_data in skewer_data["steps"]:
        if "standard" not in step_data:
            continue

        standard_step_data = _standard_steps[step_data["standard"]]

        if "id" not in step_data:
            step_data["id"] = standard_step_data.get("id")

        if "title" not in step_data:
            step_data["title"] = standard_step_data["title"]

        if "numbered" not in step_data:
            step_data["numbered"] = standard_step_data.get("numbered", True)

        if "preamble" not in step_data:
            if "preamble" in standard_step_data:
                step_data["preamble"] = standard_step_data["preamble"]

        if "postamble" not in step_data:
            if "postamble" in standard_step_data:
                step_data["postamble"] = standard_step_data["postamble"]

        if "commands" not in step_data:
            if "commands" in standard_step_data:
                step_data["commands"] = dict()

                if "*" in standard_step_data["commands"]:
                    assert len(standard_step_data["commands"]) == 1, standard_step_data["commands"]

                    for site_key, site_data in skewer_data["sites"].items():
                        commands = standard_step_data["commands"]["*"]

                        step_data["commands"][site_key] = _resolve_commands(commands, site_data)
                else:
                    for site_index in standard_step_data["commands"]:
                        commands = standard_step_data["commands"][site_index]
                        site_key, site_data = list(skewer_data["sites"].items())[int(site_index)]

                        step_data["commands"][site_key] = _resolve_commands(commands, site_data)

def _resolve_commands(commands, site_data):
    resolved_commands = list()

    for command in commands:
        resolved_command = dict(command)

        if "run" in command:
            resolved_command["run"] = command["run"]
            resolved_command["run"] = resolved_command["run"].replace("@kubeconfig@", site_data["kubeconfig"])
            resolved_command["run"] = resolved_command["run"].replace("@namespace@", site_data["namespace"])

        if "output" in command:
            resolved_command["output"] = command["output"]
            resolved_command["output"] = resolved_command["output"].replace("@kubeconfig@", site_data["kubeconfig"])
            resolved_command["output"] = resolved_command["output"].replace("@namespace@", site_data["namespace"])

        resolved_commands.append(resolved_command)

    return resolved_commands
