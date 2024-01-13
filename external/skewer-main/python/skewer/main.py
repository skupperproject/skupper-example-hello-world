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

standard_steps_yaml = read(join(get_parent_dir(__file__), "standardsteps.yaml"))
standard_steps = parse_yaml(standard_steps_yaml)

example_suite_para = """
This example is part of a [suite of examples][examples] showing the
different ways you can use [Skupper][website] to connect services
across cloud providers, data centers, and edge sites.

[website]: https://skupper.io/
[examples]: https://skupper.io/examples/index.html
""".strip()

standard_prerequisites = """
* The `kubectl` command-line tool, version 1.15 or later
  ([installation guide][install-kubectl])

* Access to at least one Kubernetes cluster, from [any provider you
  choose][kube-providers]

[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[kube-providers]: https://skupper.io/start/kubernetes.html
""".strip()

standard_next_steps = """
Check out the other [examples][examples] on the Skupper website.
""".strip()

about_this_example = """
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
def await_resource(resource, timeout=240):
    assert "/" in resource, resource

    start_time = get_time()

    while True:
        notice(f"Waiting for {resource} to become available")

        if run(f"kubectl get {resource}", output=DEVNULL, check=False, quiet=True).exit_code == 0:
            break

        if get_time() - start_time > timeout:
            fail(f"Timed out waiting for {resource}")

        sleep(5, quiet=True)

    if resource.startswith("deployment/"):
        try:
            run(f"kubectl wait --for condition=available --timeout {timeout}s {resource}", quiet=True, stash=True)
        except:
            run(f"kubectl logs {resource}")
            raise

def await_external_ip(service, timeout=240):
    assert service.startswith("service/"), service

    start_time = get_time()

    await_resource(service, timeout=timeout)

    while True:
        notice(f"Waiting for external IP from {service} to become available")

        if call(f"kubectl get {service} -o jsonpath='{{.status.loadBalancer.ingress}}'", quiet=True) != "":
            break

        if get_time() - start_time > timeout:
            fail(f"Timed out waiting for external IP for {service}")

        sleep(5, quiet=True)

    return call(f"kubectl get {service} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'", quiet=True)

def await_http_ok(service, url_template, user=None, password=None, timeout=240):
    assert service.startswith("service/"), service

    start_time = get_time()

    ip = await_external_ip(service, timeout=timeout)
    url = url_template.format(ip)
    insecure = url.startswith("https")

    while True:
        notice(f"Waiting for HTTP OK from {url}")

        try:
            http_get(url, insecure=insecure, user=user, password=password)
        except PlanoError:
            if get_time() - start_time > timeout:
                fail(f"Timed out waiting for HTTP OK from {url}")

            sleep(5, quiet=True)
        else:
            break

def await_console_ok():
    password = call("kubectl get secret/skupper-console-users -o jsonpath={.data.admin}", quiet=True)
    password = base64_decode(password)

    await_http_ok("service/skupper", "https://{}:8010/", user="admin", password=password)

def run_steps_minikube(skewer_file, debug=False):
    notice("Running steps on Minikube")

    check_environment()
    check_program("minikube")

    skewer_data = read_yaml(skewer_file)

    for site in get_sites(skewer_data):
        site.check()

    kube_sites = [x for x in get_sites(skewer_data) if x.platform == "kubernetes"]
    kubeconfigs = list()

    try:
        run("minikube -p skewer start")

        make_dir("/tmp/skewer", quiet=True)

        for site in kube_sites:
            kubeconfig = site.env["KUBECONFIG"].replace("~", "/tmp/skewer")
            site.env["KUBECONFIG"] = kubeconfig

            kubeconfigs.append(kubeconfig)

            with site:
                run("minikube -p skewer update-context")
                check_file(ENV["KUBECONFIG"])

        with open("/tmp/minikube-tunnel-output", "w") as tunnel_output_file:
            with start("minikube -p skewer tunnel", output=tunnel_output_file):
                run_steps(skewer_file, kubeconfigs=kubeconfigs, debug=debug)
    finally:
        run("minikube -p skewer delete")

def run_steps(skewer_file, kubeconfigs=None, debug=False):
    notice(f"Running steps (skewer_file='{skewer_file}')")

    check_environment()

    skewer_data = read_yaml(skewer_file)

    if kubeconfigs is not None:
        apply_kubeconfigs(skewer_data, kubeconfigs)

    apply_standard_steps(skewer_data)

    for site in get_sites(skewer_data):
        site.check()

    for step in get_steps(skewer_data):
        step.check()

    try:
        for step in skewer_data["steps"]:
            if step.get("id") == "cleaning_up":
                continue

            run_step(skewer_data, step)

        if "SKEWER_DEMO" in ENV:
            pause_for_demo(skewer_data)
    except:
        if debug:
            print("TROUBLE!")
            print("-- Start of debug output")

            for site in get_sites(skewer_data):
                print(f"---- Debug output for site '{site.name}'")

                with site:
                    if site.platform == "kubernetes":
                        run("kubectl get services", check=False)
                        run("kubectl get deployments", check=False)
                        run("kubectl get statefulsets", check=False)
                        run("kubectl get pods", check=False)
                        run("kubectl get events", check=False)

                    run("skupper version", check=False)
                    run("skupper status", check=False)
                    run("skupper link status", check=False)
                    run("skupper service status", check=False)
                    run("skupper network status", check=False)
                    run("skupper debug events", check=False)

                    if site.platform == "kubernetes":
                        run("kubectl logs deployment/skupper-router", check=False)
                        run("kubectl logs deployment/skupper-service-controller", check=False)

            print("-- End of debug output")

        raise
    finally:
        for step in skewer_data["steps"]:
            if step.get("id") == "cleaning_up":
                run_step(skewer_data, step, check=False)
                break

def run_step(skewer_data, step_data, check=True):
    if "commands" not in step_data:
        return

    if "title" in step_data:
        notice("Running step '{}'", step_data["title"])

    for site_name, commands in step_data["commands"].items():
        with get_site(skewer_data, site_name) as site:
            if site.platform == "kubernetes":
                run(f"kubectl config set-context --current --namespace {site.namespace}", stdout=DEVNULL, quiet=True)

            for command in commands:
                if command.get("apply") == "readme":
                    continue

                if "run" in command:
                    make_dir("/tmp/skewer", quiet=True)
                    run(command["run"].replace("~", "/tmp/skewer"), shell=True, check=check)

                if "await_resource" in command:
                    resource = command["await_resource"]
                    await_resource(resource)

                if "await_external_ip" in command:
                    service = command["await_external_ip"]
                    await_external_ip(service)

                if "await_http_ok" in command:
                    service, url_template = command["await_http_ok"]
                    await_http_ok(service, url_template)

                if "await_console_ok" in command:
                    await_console_ok()

def pause_for_demo(skewer_data):
    notice("Pausing for demo time")

    sites = list(get_sites(skewer_data))
    frontend_url = None

    if sites[0].platform == "kubernetes":
        with sites[0]:
            console_ip = await_external_ip("service/skupper")
            console_url = f"https://{console_ip}:8010/"
            password_data = call("kubectl get secret skupper-console-users -o jsonpath='{.data.admin}'", quiet=True)
            password = base64_decode(password_data).decode("ascii")

            if run("kubectl get service/frontend", check=False, output=DEVNULL, quiet=True).exit_code == 0:
                if call("kubectl get service/frontend -o jsonpath='{.spec.type}'", quiet=True) == "LoadBalancer":
                    frontend_ip = await_external_ip("service/frontend")
                    frontend_url = f"http://{frontend_ip}:8080/"

    print()
    print("Demo time!")
    print()
    print("Sites:")

    for site in sites:
        if site.platform == "kubernetes":
            kubeconfig = site.env["KUBECONFIG"]
            print(f"  {site.name}: export KUBECONFIG={kubeconfig}")

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

def generate_readme(skewer_file, output_file):
    notice(f"Generating the readme (skewer_file='{skewer_file}', output_file='{output_file}')")

    skewer_data = read_yaml(skewer_file)

    for site in get_sites(skewer_data):
        site.check()

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

    out.append(example_suite_para)
    out.append("")
    out.append("#### Contents")
    out.append("")

    if "overview" in skewer_data:
        out.append("* [Overview](#overview)")

    out.append("* [Prerequisites](#prerequisites)")

    apply_standard_steps(skewer_data)

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

    prerequisites = standard_prerequisites

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
        out.append(generate_readme_step(skewer_data, step_data))
        out.append("")

    if "summary" in skewer_data:
        out.append("## Summary")
        out.append("")
        out.append(skewer_data["summary"].strip())
        out.append("")

    next_steps = standard_next_steps

    if "next_steps" in skewer_data:
        next_steps = skewer_data["next_steps"].strip()

    out.append("## Next steps")
    out.append("")
    out.append(next_steps)
    out.append("")

    out.append("## About this example")
    out.append("")
    out.append(about_this_example)
    out.append("")

    write(output_file, "\n".join(out).strip() + "\n")

def generate_readme_step(skewer_data, step_data):
    out = list()

    if "preamble" in step_data:
        out.append(step_data["preamble"].strip())
        out.append("")

    if "commands" in step_data:
        items = step_data["commands"].items()

        for i, item in enumerate(items):
            site_name, commands = item
            namespace = skewer_data["sites"][site_name].get("namespace")
            title = skewer_data["sites"][site_name].get("title", namespace)

            if title is None:
                fail(f"Site '{site_name}' has no namespace or title")

            outputs = list()

            out.append(f"_**Console for {title}:**_")
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

def apply_kubeconfigs(skewer_data, kubeconfigs):
    notice("Applying kubeconfigs")

    kube_sites = [x for x in get_sites(skewer_data) if x.platform == "kubernetes"]

    if len(kube_sites) != len(kubeconfigs):
        fail("The provided kubeconfigs are fewer than the number of Kubernetes sites")

    for site, kubeconfig in zip(kube_sites, kubeconfigs):
        site.env["KUBECONFIG"] = kubeconfig

def apply_standard_steps(skewer_data):
    notice("Applying standard steps")

    for step_data in skewer_data["steps"]:
        if "standard" not in step_data:
            continue

        standard_step_data = standard_steps[step_data["standard"]]

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

                for i, site_item in enumerate(skewer_data["sites"].items()):
                    site_name, site = site_item

                    if str(i) in standard_step_data["commands"]:
                        # Is a specific index in the standard commands?
                        commands = standard_step_data["commands"][str(i)]
                        step_data["commands"][site_name] = resolve_commands(commands, site)
                    elif "*" in standard_step_data["commands"]:
                        # Is "*" in the standard commands?
                        commands = standard_step_data["commands"]["*"]
                        step_data["commands"][site_name] = resolve_commands(commands, site)
                    else:
                        # Otherwise, omit commands for this site
                        continue

def resolve_commands(commands, site):
    resolved_commands = list()

    for command in commands:
        resolved_command = dict(command)

        if "run" in command:
            resolved_command["run"] = command["run"]

            if site["platform"] == "kubernetes":
                resolved_command["run"] = resolved_command["run"].replace("@kubeconfig@", site["env"]["KUBECONFIG"])
                resolved_command["run"] = resolved_command["run"].replace("@namespace@", site["namespace"])

        if "output" in command:
            resolved_command["output"] = command["output"]

            if site["platform"] == "kubernetes":
                resolved_command["output"] = resolved_command["output"].replace("@kubeconfig@", site["env"]["KUBECONFIG"])
                resolved_command["output"] = resolved_command["output"].replace("@namespace@", site["namespace"])

        resolved_commands.append(resolved_command)

    return resolved_commands

def get_sites(skewer_data):
    for site_name, site_data in skewer_data["sites"].items():
        yield Site(site_name, site_data)

def get_site(skewer_data, name):
    data = skewer_data["sites"][name]
    return Site(name, data)

class Site:
    def __init__(self, name, data):
        assert name is not None

        self.name = name
        self.title = data.get("title", capitalize(self.name))
        self.platform = data.get("platform")
        self.namespace = data.get("namespace")
        self.env = data.get("env")

    def __enter__(self):
        self._logging_context = logging_context(self.name)
        self._working_env = working_env(**self.env)

        self._logging_context.__enter__()
        self._working_env.__enter__()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._working_env.__exit__(exc_type, exc_value, traceback)
        self._logging_context.__exit__(exc_type, exc_value, traceback)

    def check(self):
        if self.platform is None:
            fail(f"{self} has no 'platform' attribute")

        if self.platform not in ("kubernetes", "podman"):
            fail(f"{self} attribute 'platform' has an illegal value: {self.platform}")

        if self.platform == "kubernetes":
            if self.namespace is None:
                fail(f"Kubernetes {self} has no 'namespace' attribute")

            if "KUBECONFIG" not in self.env:
                fail(f"Kubernetes {self} has no KUBECONFIG environment variable")

        if self.platform == "podman":
            if "SKUPPER_PLATFORM" not in self.env:
                fail(f"Podman {self} has no SKUPPER_PLATFORM environment variable")

            platform = self.env["SKUPPER_PLATFORM"]

            if platform != "podman":
                fail(f"Podman {self} environment variable SKUPPER_PLATFORM has an illegal value: {platform}")

    def __repr__(self):
        return f"site '{self.name}'"

def get_steps(skewer_data):
    for step_data in skewer_data["steps"]:
        yield Step(step_data)

class Step:
    def __init__(self, data):
        self.title = data["title"]
        self.preamble = data.get("preamble")
        self.commands = data.get("commands")
        self.postamble = data.get("postamble")

    def check(self):
        pass
