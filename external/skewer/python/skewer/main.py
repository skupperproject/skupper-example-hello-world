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

import inspect

from plano import *

__all__ = [
    "generate_readme", "run_steps", "Minikube",
]

standard_text = read_yaml(join(get_parent_dir(__file__), "standardtext.yaml"))
standard_steps = read_yaml(join(get_parent_dir(__file__), "standardsteps.yaml"))

def check_environment():
    check_program("base64")
    check_program("curl")
    check_program("kubectl")
    check_program("skupper")

def resource_exists(resource):
    return run(f"kubectl get {resource}", output=DEVNULL, check=False, quiet=True).exit_code == 0

def get_resource_jsonpath(resource, jsonpath):
    return call(f"kubectl get {resource} -o jsonpath='{{{jsonpath}}}'", quiet=True)

def await_resource(resource, timeout=240):
    assert "/" in resource, resource

    start_time = get_time()

    while True:
        notice(f"Waiting for {resource} to become available")

        if resource_exists(resource):
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

        if get_resource_jsonpath(service, ".status.loadBalancer.ingress") != "":
            break

        if get_time() - start_time > timeout:
            fail(f"Timed out waiting for external IP for {service}")

        sleep(5, quiet=True)

    return get_resource_jsonpath(service, ".status.loadBalancer.ingress[0].ip")

def await_http_ok(service, url_template, user=None, password=None, timeout=240):
    assert service.startswith("service/"), service

    start_time = get_time()

    ip = await_external_ip(service, timeout=timeout)
    url = url_template.format(ip)
    insecure = url.startswith("https")

    while True:
        notice(f"Waiting for HTTP OK from {url}")

        try:
            http_get(url, insecure=insecure, user=user, password=password, quiet=True)
        except PlanoError:
            if get_time() - start_time > timeout:
                fail(f"Timed out waiting for HTTP OK from {url}")

            sleep(5, quiet=True)
        else:
            break

def await_console_ok():
    await_resource("secret/skupper-console-users")

    password = get_resource_jsonpath("secret/skupper-console-users", ".data.admin")
    password = base64_decode(password)

    await_http_ok("service/skupper", "https://{}:8010/", user="admin", password=password)

def run_steps(skewer_file, kubeconfigs=[], work_dir=None, debug=False):
    notice(f"Running steps (skewer_file='{skewer_file}')")

    check_environment()

    model = Model(skewer_file, kubeconfigs)
    model.check()

    if work_dir is None:
        work_dir = join(get_user_temp_dir(), "skewer")
        remove(work_dir, quiet=True)
        make_dir(work_dir, quiet=True)

    try:
        for step in model.steps:
            if step.name == "cleaning_up":
                continue

            run_step(model, step, work_dir)

        if "SKEWER_DEMO" in ENV:
            pause_for_demo(model)
    except:
        if debug:
            print_debug_output(model)

        raise
    finally:
        for step in model.steps:
            if step.name == "cleaning_up":
                run_step(model, step, work_dir, check=False)
                break

def run_step(model, step, work_dir, check=True):
    if not step.commands:
        return

    notice(f"Running {step}")

    for site_name, commands in step.commands:
        with dict(model.sites)[site_name] as site:
            if site.platform == "kubernetes":
                run(f"kubectl config set-context --current --namespace {site.namespace}", stdout=DEVNULL, quiet=True)

            for command in commands:
                if command.apply == "readme":
                    continue

                if command.await_resource:
                    await_resource(command.await_resource)

                if command.await_external_ip:
                    await_external_ip(command.await_external_ip)

                if command.await_http_ok:
                    await_http_ok(*command.await_http_ok)

                if command.await_console_ok:
                    await_console_ok()

                if command.run:
                    run(command.run.replace("~", work_dir), shell=True, check=check)

def pause_for_demo(model):
    notice("Pausing for demo time")

    first_site = [x for _, x in model.sites][0]
    console_url = None
    password = None
    frontend_url = None

    if first_site.platform == "kubernetes":
        with first_site:
            if resource_exists("service/frontend"):
                if get_resource_jsonpath("service/frontend", ".spec.type") == "LoadBalancer":
                    frontend_ip = await_external_ip("service/frontend")
                    frontend_url = f"http://{frontend_ip}:8080/"

            if resource_exists("secret/skupper-console-users"):
                console_ip = await_external_ip("service/skupper")
                console_url = f"https://{console_ip}:8010/"

                await_resource("secret/skupper-console-users")
                password = get_resource_jsonpath("secret/skupper-console-users", ".data.admin")
                password = base64_decode(password).decode("ascii")

    print()
    print("Demo time!")
    print()
    print("Sites:")
    print()

    for _, site in model.sites:
        if site.platform == "kubernetes":
            kubeconfig = site.env["KUBECONFIG"]
            print(f"  {site.name}: export KUBECONFIG={kubeconfig}")
        elif site.platform == "podman":
            print(f"  {site.name}: export SKUPPER_PLATFORM=podman")

    print()

    if frontend_url:
        print(f"Frontend URL:     {frontend_url}")
        print()

    if console_url:
        print(f"Console URL:      {console_url}")
        print( "Console user:     admin")
        print(f"Console password: {password}")
        print()

    if "SKEWER_DEMO_NO_WAIT" not in ENV:
        while input("Are you done (yes)? ") != "yes": # pragma: nocover
            pass

def print_debug_output(model):
    print("TROUBLE!")
    print("-- Start of debug output")

    for _, site in model.sites:
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

def generate_readme(skewer_file, output_file):
    notice(f"Generating the readme (skewer_file='{skewer_file}', output_file='{output_file}')")

    model = Model(skewer_file)
    model.check()

    out = list()

    def generate_workflow_url(workflow):
        result = parse_url(workflow)

        if result.scheme:
            return workflow

        owner, repo = get_github_owner_repo()

        return f"https://github.com/{owner}/{repo}/actions/workflows/{workflow}"

    def generate_step_heading(step):
        if step.numbered:
            return f"Step {step.number}: {step.title}"
        else:
            return step.title

    def append_toc_entry(heading, condition=True):
        if not condition:
            return

        fragment = replace(heading, r"[ -]", "_")
        fragment = replace(fragment, r"[\W]", "")
        fragment = replace(fragment, "_", "-")
        fragment = fragment.lower()

        out.append(f"* [{heading}](#{fragment})")

    def append_section(heading, text):
        if not text:
            return

        out.append(f"## {heading}")
        out.append("")
        out.append(text.strip())
        out.append("")

    out.append(f"# {model.title}")
    out.append("")

    if model.workflow:
        url = generate_workflow_url(model.workflow)
        out.append(f"[![main]({url}/badge.svg)]({url})")
        out.append("")

    if model.subtitle:
        out.append(f"#### {model.subtitle}")
        out.append("")

    out.append(standard_text["example_suite"].strip())
    out.append("")
    out.append("#### Contents")
    out.append("")

    append_toc_entry("Overview", model.overview)
    append_toc_entry("Prerequisites")

    for step in model.steps:
        append_toc_entry(generate_step_heading(step))

    append_toc_entry("Summary")
    append_toc_entry("Next steps")
    append_toc_entry("About this example")

    out.append("")

    append_section("Overview", model.overview)
    append_section("Prerequisites", model.prerequisites)

    for step in model.steps:
        heading = generate_step_heading(step)
        text = generate_readme_step(model, step)

        append_section(heading, text)

    append_section("Summary", model.summary)
    append_section("Next steps", model.next_steps)
    append_section("About this example", standard_text["about_this_example"].strip())

    write(output_file, "\n".join(out).strip() + "\n")

def generate_readme_step(model, step):
    notice(f"Generating {step}")

    out = list()

    if step.preamble:
        out.append(step.preamble.strip())
        out.append("")

    for site_name, commands in step.commands:
        site = dict(model.sites)[site_name]
        outputs = list()

        out.append(f"_**{site.title}:**_")
        out.append("")
        out.append("~~~ shell")

        for command in commands:
            if command.apply == "test":
                continue

            if command.run:
                out.append(command.run)

            if command.output:
                assert command.run

                outputs.append((command.run, command.output))

        out.append("~~~")
        out.append("")

        if outputs:
            out.append("_Sample output:_")
            out.append("")
            out.append("~~~ console")
            out.append("\n\n".join((f"$ {run}\n{output.strip()}" for run, output in outputs)))
            out.append("~~~")
            out.append("")

    if step.postamble:
        out.append(step.postamble.strip())

    return "\n".join(out).strip()

def apply_kubeconfigs(model, kubeconfigs):
    kube_sites = [x for _, x in model.sites if x.platform == "kubernetes"]

    if kubeconfigs and len(kubeconfigs) < len(kube_sites):
        fail("The provided kubeconfigs are fewer than the number of Kubernetes sites")

    for site, kubeconfig in zip(kube_sites, kubeconfigs):
        site.env["KUBECONFIG"] = kubeconfig

def apply_standard_steps(model):
    notice("Applying standard steps")

    for step in model.steps:
        if "standard" not in step.data:
            continue

        standard_step_name = step.data["standard"]

        try:
            standard_step_data = standard_steps[standard_step_name]
        except KeyError:
            fail(f"Standard step '{standard_step_name}' not found")

        del step.data["standard"]

        def apply_attribute(name, default=None):
            if name not in step.data:
                value = standard_step_data.get(name, default)

                if value and name in ("title", "preamble", "postamble"):
                    for i, site in enumerate([x for _, x in model.sites]):
                        value = value.replace(f"@site{i}@", site.title)

                        if site.namespace:
                            value = value.replace(f"@namespace{i}@", site.namespace)

                step.data[name] = value

        apply_attribute("name")
        apply_attribute("title")
        apply_attribute("numbered", True)
        apply_attribute("preamble")
        apply_attribute("postamble")

        platform = standard_step_data.get("platform")

        if "commands" not in step.data and "commands" in standard_step_data:
            step.data["commands"] = dict()

            for i, item in enumerate(dict(model.sites).items()):
                site_name, site = item

                if platform and site.platform != platform:
                    continue

                if str(i) in standard_step_data["commands"]:
                    # Is a specific index in the standard commands?
                    commands = standard_step_data["commands"][str(i)]
                    step.data["commands"][site_name] = resolve_command_variables(commands, site)
                elif "*" in standard_step_data["commands"]:
                    # Is "*" in the standard commands?
                    commands = standard_step_data["commands"]["*"]
                    step.data["commands"][site_name] = resolve_command_variables(commands, site)
                else:
                    # Otherwise, omit commands for this site
                    continue

def resolve_command_variables(commands, site):
    resolved_commands = list()

    for command in commands:
        resolved_command = dict(command)

        if "run" in command:
            resolved_command["run"] = command["run"]

            if site.platform == "kubernetes":
                resolved_command["run"] = resolved_command["run"].replace("@kubeconfig@", site.env["KUBECONFIG"])
                resolved_command["run"] = resolved_command["run"].replace("@namespace@", site.namespace)

        if "output" in command:
            resolved_command["output"] = command["output"]

            if site.platform == "kubernetes":
                resolved_command["output"] = resolved_command["output"].replace("@kubeconfig@", site.env["KUBECONFIG"])
                resolved_command["output"] = resolved_command["output"].replace("@namespace@", site.namespace)

        resolved_commands.append(resolved_command)

    return resolved_commands

def get_github_owner_repo():
    check_program("git")

    url = call("git remote get-url origin", quiet=True)
    result = parse_url(url)

    if result.scheme == "" and result.path.startswith("git@github.com:"):
        path = remove_prefix(result.path, "git@github.com:")
        path = remove_suffix(path, ".git")

        return path.split("/", 1)

    if result.scheme in ("http", "https") and result.netloc == "github.com":
        path = remove_prefix(result.path, "/")

        return path.split("/", 1)

    fail("Unknown origin URL format")

def object_property(name, default=None):
    def get(obj):
        return obj.data.get(name, default)

    return property(get)

def check_required_attributes(obj, *names):
    for name in names:
        if name not in obj.data:
            fail(f"{obj} is missing required attribute '{name}'")

def check_unknown_attributes(obj):
    known_attributes = dict(inspect.getmembers(obj.__class__, lambda x: isinstance(x, property)))

    for name in obj.data:
        if name not in known_attributes:
            fail(f"{obj} has unknown attribute '{name}'")

class Model:
    title = object_property("title")
    subtitle = object_property("subtitle")
    workflow = object_property("workflow", "main.yaml")
    overview = object_property("overview")
    prerequisites = object_property("prerequisites", standard_text["prerequisites"].strip())
    summary = object_property("summary")
    next_steps = object_property("next_steps", standard_text["next_steps"].strip())

    def __init__(self, skewer_file, kubeconfigs=[]):
        self.skewer_file = skewer_file
        self.data = read_yaml(self.skewer_file)

        apply_kubeconfigs(self, kubeconfigs)
        apply_standard_steps(self)

    def __repr__(self):
        return f"model '{self.skewer_file}'"

    def check(self):
        check_required_attributes(self, "title", "sites", "steps")
        check_unknown_attributes(self)

        for _, site in self.sites:
            site.check()

        for step in self.steps:
            step.check()

    @property
    def sites(self):
        for name, data in self.data["sites"].items():
            yield name, Site(self, data, name)

    @property
    def steps(self):
        for data in self.data["steps"]:
            yield Step(self, data)

class Site:
    platform = object_property("platform")
    namespace = object_property("namespace")
    env = object_property("env", dict())

    def __init__(self, model, data, name):
        assert name is not None

        self.model = model
        self.data = data
        self.name = name

    def __repr__(self):
        return f"site '{self.name}'"

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
        check_required_attributes(self, "platform")
        check_unknown_attributes(self)

        if self.platform not in ("kubernetes", "podman"):
            fail(f"{self} attribute 'platform' has an illegal value: {self.platform}")

        if self.platform == "kubernetes":
            check_required_attributes(self, "namespace")

            if "KUBECONFIG" not in self.env:
                fail(f"Kubernetes {self} has no KUBECONFIG environment variable")

        if self.platform == "podman":
            if "SKUPPER_PLATFORM" not in self.env:
                fail(f"Podman {self} has no SKUPPER_PLATFORM environment variable")

            platform = self.env["SKUPPER_PLATFORM"]

            if platform != "podman":
                fail(f"Podman {self} environment variable SKUPPER_PLATFORM has an illegal value: {platform}")

    @property
    def title(self):
        return self.data.get("title", capitalize(self.name))

class Step:
    numbered = object_property("numbered", True)
    name = object_property("name")
    title = object_property("title")
    preamble = object_property("preamble")
    postamble = object_property("postamble")

    def __init__(self, model, data):
        self.model = model
        self.data = data

    def __repr__(self):
        return f"step {self.number} '{self.title}'"

    def check(self):
        check_required_attributes(self, "title")
        check_unknown_attributes(self)

        site_names = [x.name for _, x in self.model.sites]

        for site_name, commands in self.commands:
            if site_name not in site_names:
                fail(f"Unknown site name '{site_name}' in commands for {self}")

            for command in commands:
                command.check()

    @property
    def number(self):
        return self.model.data["steps"].index(self.data) + 1

    @property
    def commands(self):
        for site_name, commands in self.data.get("commands", dict()).items():
            yield site_name, [Command(self.model, data) for data in commands]

class Command:
    run = object_property("run")
    apply = object_property("apply")
    output = object_property("output")
    await_resource = object_property("await_resource")
    await_external_ip = object_property("await_external_ip")
    await_http_ok = object_property("await_http_ok")
    await_console_ok = object_property("await_console_ok")

    def __init__(self, model, data):
        self.model = model
        self.data = data

    def __repr__(self):
        if self.run:
            return f"command '{self.run.splitlines()[0]}'"

        return "command"

    def check(self):
        check_unknown_attributes(self)

class Minikube:
    def __init__(self, skewer_file):
        self.skewer_file = skewer_file
        self.kubeconfigs = list()
        self.work_dir = join(get_user_temp_dir(), "skewer")

    def __enter__(self):
        notice("Starting Minikube")

        check_environment()
        check_program("minikube")

        profile_data = parse_json(call("minikube profile list --output json", quiet=True))

        for profile in profile_data.get("valid", []):
            if profile["Name"] == "skewer":
                fail("A Minikube profile 'skewer' already exists.  Delete it using 'minikube delete -p skewer'.")

        remove(self.work_dir, quiet=True)
        make_dir(self.work_dir, quiet=True)

        run("minikube start -p skewer --auto-update-drivers false")

        tunnel_output_file = open(f"{self.work_dir}/minikube-tunnel-output", "w")
        self.tunnel = start("minikube tunnel -p skewer", output=tunnel_output_file)

        model = Model(self.skewer_file)
        model.check()

        kube_sites = [x for _, x in model.sites if x.platform == "kubernetes"]

        for site in kube_sites:
            kubeconfig = site.env["KUBECONFIG"].replace("~", self.work_dir)
            site.env["KUBECONFIG"] = kubeconfig

            self.kubeconfigs.append(kubeconfig)

            with site:
                run("minikube update-context -p skewer")
                check_file(ENV["KUBECONFIG"])

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        notice("Stopping Minikube")

        stop(self.tunnel)

        run("minikube delete -p skewer")
