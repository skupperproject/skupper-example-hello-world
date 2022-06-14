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

_standard_steps_yaml = """
configure_separate_console_sessions:
  title: Configure separate console sessions
  preamble: |
    Skupper is designed for use with multiple namespaces, typically on
    different clusters.  The `skupper` command uses your
    [kubeconfig][kubeconfig] and current context to select the
    namespace where it operates.

    [kubeconfig]: https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/

    Your kubeconfig is stored in a file in your home directory.  The
    `skupper` and `kubectl` commands use the `KUBECONFIG` environment
    variable to locate it.

    A single kubeconfig supports only one active context per user.
    Since you will be using multiple contexts at once in this
    exercise, you need to create distinct kubeconfigs.

    Start a console session for each of your namespaces.  Set the
    `KUBECONFIG` environment variable to a different path in each
    session.
  commands:
    "*":
      - run: export KUBECONFIG=~/.kube/config-@namespace@
access_your_clusters:
  title: Access your clusters
  preamble: |
    The methods for accessing your clusters vary by Kubernetes
    provider. Find the instructions for your chosen providers and use
    them to authenticate and configure access for each console
    session.  See the following links for more information:

    * [Minikube](https://skupper.io/start/minikube.html)
    * [Amazon Elastic Kubernetes Service (EKS)](https://skupper.io/start/eks.html)
    * [Azure Kubernetes Service (AKS)](https://skupper.io/start/aks.html)
    * [Google Kubernetes Engine (GKE)](https://skupper.io/start/gke.html)
    * [IBM Kubernetes Service](https://skupper.io/start/ibmks.html)
    * [OpenShift](https://skupper.io/start/openshift.html)
    * [More providers](https://kubernetes.io/partners/#kcsp)
set_up_your_namespaces:
  title: Set up your namespaces
  preamble: |
    Use `kubectl create namespace` to create the namespaces you wish
    to use (or use existing namespaces).  Use `kubectl config
    set-context` to set the current namespace for each session.
  commands:
    "*":
      - output: namespace/@namespace@ created
        run: kubectl create namespace @namespace@
      - output: Context "minikube" modified.
        run: kubectl config set-context --current --namespace @namespace@
install_skupper_in_your_namespaces:
  title: Install Skupper in your namespaces
  preamble: |
    The `skupper init` command installs the Skupper router and service
    controller in the current namespace.  Run the `skupper init` command
    in each namespace.

    **Note:** If you are using Minikube, [you need to start `minikube
    tunnel`][minikube-tunnel] before you install Skupper.

    [minikube-tunnel]: https://skupper.io/start/minikube.html#running-minikube-tunnel
  commands:
    "*":
      - run: skupper init
        output: |
          Waiting for LoadBalancer IP or hostname...
          Skupper is now installed in namespace '@namespace@'.  Use 'skupper status' to get more information.
      - await: [deployment/skupper-service-controller, deployment/skupper-router]
check_the_status_of_your_namespaces:
  title: Check the status of your namespaces
  preamble: |
    Use `skupper status` in each console to check that Skupper is
    installed.
  commands:
    "*":
      - run: skupper status
        output: |
          Skupper is enabled for namespace "@namespace@" in interior mode. It is connected to 1 other site. It has 1 exposed service.
          The site console url is: <console-url>
          The credentials for internal console-auth mode are held in secret: 'skupper-console-users'
  postamble: |
    As you move through the steps below, you can use `skupper status` at
    any time to check your progress.
link_your_namespaces:
  title: Link your namespaces
  preamble: |
    Creating a link requires use of two `skupper` commands in
    conjunction, `skupper token create` and `skupper link create`.

    The `skupper token create` command generates a secret token that
    signifies permission to create a link.  The token also carries the
    link details.  Then, in a remote namespace, The `skupper link
    create` command uses the token to create a link to the namespace
    that generated it.

    **Note:** The link token is truly a *secret*.  Anyone who has the
    token can link to your namespace.  Make sure that only those you
    trust have access to it.

    First, use `skupper token create` in one namespace to generate the
    token.  Then, use `skupper link create` in the other to create a
    link.
  commands:
    "0":
      - output: Token written to ~/secret.token
        run: skupper token create ~/secret.token
    "1":
      - run: skupper link create ~/secret.token
        output: |
          Site configured to link to https://10.105.193.154:8081/ed9c37f6-d78a-11ec-a8c7-04421a4c5042 (name=link1)
          Check the status of the link using 'skupper link status'.
      - run: skupper link status --wait 60
        apply: test
  postamble: |
    If your console sessions are on different machines, you may need
    to use `sftp` or a similar tool to transfer the token securely.
    By default, tokens expire after a single use or 15 minutes after
    creation.
test_the_application:
  title: Test the application
  preamble: |
    Now we're ready to try it out.  Use `kubectl get service/frontend`
    to look up the external IP of the frontend service.  Then use
    `curl` or a similar tool to request the `/api/health` endpoint at
    that address.

    **Note:** The `<external-ip>` field in the following commands is a
    placeholder.  The actual value is an IP address.
  commands:
    "0":
      - run: kubectl get service/frontend
        apply: readme
        output: |
          NAME       TYPE           CLUSTER-IP      EXTERNAL-IP     PORT(S)          AGE
          frontend   LoadBalancer   10.103.232.28   <external-ip>   8080:30407/TCP   15s
      - run: curl http://<external-ip>:8080/api/health
        apply: readme
        output: OK
      - await_external_ip: service/frontend
      - run: curl --fail --verbose --retry 60 --retry-connrefused --retry-delay 2 $(kubectl get service/frontend -o jsonpath='http://{.status.loadBalancer.ingress[0].ip}:8080/api/health'); echo
        apply: test
  postamble: |
    If everything is in order, you can now access the web interface by
    navigating to `http://<external-ip>:8080/` in your browser.
accessing_the_web_console:
  title: Accessing the web console
  numbered: false
  preamble: |
    Skupper includes a web console you can use to view the application
    network.  To access it, use `skupper status` to look up the URL of
    the web console.  Then use `kubectl get
    secret/skupper-console-users` to look up the console admin
    password.

    **Note:** The `<console-url>` and `<password>` fields in the
    following output are placeholders.  The actual values are specific
    to your environment.
  commands:
    "0":
      - run: skupper status
        apply: readme
        output: |
          Skupper is enabled for namespace "@namespace@" in interior mode. It is connected to 1 other site. It has 1 exposed service.
          The site console url is: <console-url>
          The credentials for internal console-auth mode are held in secret: 'skupper-console-users'
      - run: kubectl get secret/skupper-console-users -o jsonpath={.data.admin} | base64 -d
        apply: readme
        output: <password>
      - await_external_ip: service/skupper
      - run: curl --fail --insecure --verbose --retry 60 --retry-connrefused --retry-delay 2 $(kubectl get service/skupper -o jsonpath='https://{.status.loadBalancer.ingress[0].ip}:8080/') --user admin:$(kubectl get secret/skupper-console-users -o jsonpath={.data.admin} | base64 -d); echo
        apply: test
  postamble: |
    Navigate to `<console-url>` in your browser.  When prompted, log
    in as user `admin` and enter the password.
cleaning_up:
  id: cleaning_up
  title: Cleaning up
  numbered: false
  preamble: |
    To remove Skupper and the other resources from this exercise, use
    the following commands.
  commands:
    "*":
      - run: skupper delete
"""

_standard_steps = parse_yaml(_standard_steps_yaml)

_example_suite_para = """
This example is part of a [suite of examples][examples] showing the
different ways you can use [Skupper][website] to connect services
across cloud providers, data centers, and edge sites.

[website]: https://skupper.io/
[examples]: https://skupper.io/examples/index.html
"""

_standard_prerequisites = """
* The `kubectl` command-line tool, version 1.15 or later
  ([installation guide][install-kubectl])

* The `skupper` command-line tool, the latest version ([installation
  guide][install-skupper])

* Access to at least one Kubernetes cluster, from any provider you
  choose

[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[install-skupper]: https://skupper.io/install/index.html
"""

_standard_next_steps = """
Check out the other [examples][examples] on the Skupper website.
"""

def check_environment():
    check_program("base64")
    check_program("curl")
    check_program("kubectl")
    check_program("skupper")

# Eventually Kubernetes will make this nicer:
# https://github.com/kubernetes/kubernetes/pull/87399
# https://github.com/kubernetes/kubernetes/issues/80828
# https://github.com/kubernetes/kubernetes/issues/83094
def await_resource(group, name, namespace=None):
    base_command = "kubectl"

    if namespace is not None:
        base_command = f"{base_command} -n {namespace}"

    notice(f"Waiting for {group}/{name} to become available")

    for i in range(90):
        sleep(2)

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

def await_external_ip(group, name, namespace=None):
    await_resource(group, name, namespace=namespace)

    base_command = "kubectl"

    if namespace is not None:
        base_command = f"{base_command} -n {namespace}"

    for i in range(90):
        sleep(2)

        if call(f"{base_command} get {group}/{name} -o jsonpath='{{.status.loadBalancer.ingress}}'") != "":
            break
    else:
        fail(f"Timed out waiting for external IP for {group}/{name}")

    return call(f"{base_command} get {group}/{name} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'")

def run_steps_on_minikube(skewer_file):
    check_environment()
    check_program("minikube")

    skewer_data = read_yaml(skewer_file)
    work_dir = make_temp_dir()

    _apply_standard_steps(skewer_data)

    try:
        run(f"minikube -p skewer start")

        for name, value in skewer_data["sites"].items():
            kubeconfig = value["kubeconfig"].replace("~", work_dir)

            with working_env(KUBECONFIG=kubeconfig):
                run(f"minikube -p skewer update-context")
                check_file(ENV["KUBECONFIG"])

        with open("/tmp/minikube-tunnel-output", "w") as tunnel_output_file:
            with start(f"minikube -p skewer tunnel", output=tunnel_output_file):
                _run_steps(work_dir, skewer_data)
    finally:
        run(f"minikube -p skewer delete")

def run_steps_external(skewer_file, **kubeconfigs):
    check_environment()

    skewer_data = read_yaml(skewer_file)
    work_dir = make_temp_dir()

    _apply_standard_steps(skewer_data)

    for name, kubeconfig in kubeconfigs.items():
        skewer_data["sites"][name]["kubeconfig"] = kubeconfig

    _run_steps(work_dir, skewer_data)

def _run_steps(work_dir, skewer_data):
    steps = list()
    cleaning_up_step = None

    for step in skewer_data["steps"]:
        if step.get("id") == "cleaning_up":
            cleaning_up_step = step
        else:
            steps.append(step)

    try:
        for step in steps:
            _run_step(work_dir, skewer_data, step)

        if "SKEWER_DEMO" in ENV:
            _pause_for_demo(work_dir, skewer_data)
    except:
        run("skupper debug events")
    finally:
        if cleaning_up_step is not None:
            _run_step(work_dir, skewer_data, cleaning_up_step, check=False)

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

    while input("Are you done (yes)? ") != "yes":
        pass

def _run_step(work_dir, skewer_data, step_data, check=True):
    if "commands" not in step_data:
        return

    if "title" in step_data:
        notice("Running step '{}'", step_data["title"])

    try:
        items = step_data["commands"].items()
    except AttributeError:
        items = list()

        for site_name in skewer_data["sites"]:
            items.append((site_name, step_data["commands"]))

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

        fragment = replace(title, " ", "_")
        fragment = replace(fragment, r"[\W]", "")
        fragment = replace(fragment, "_", "-")
        fragment = fragment.lower()

        out.append(f"* [{title}](#{fragment})")

    if "summary" in skewer_data:
        out.append("* [Summary](#summary)")

    if "next_steps" in skewer_data:
        out.append("* [Next steps](#next-steps)")

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
        if step_data.get("numbered", True):
            title = f"Step {i}: {step_data['title']}"
        else:
            title = step_data['title']

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

                    for namespace, site_data in skewer_data["sites"].items():
                        commands = standard_step_data["commands"]["*"]

                        step_data["commands"][namespace] = _resolve_commands(commands, namespace)
                else:
                    for site_index in standard_step_data["commands"]:
                        commands = standard_step_data["commands"][site_index]
                        namespace = list(skewer_data["sites"])[int(site_index)]

                        step_data["commands"][namespace] = _resolve_commands(commands, namespace)

def _resolve_commands(commands, namespace):
    resolved_commands = list()

    for command in commands:
        resolved_command = dict(command)

        if "run" in command:
            resolved_command["run"] = command["run"].replace("@namespace@", namespace)

        if "output" in command:
            resolved_command["output"] = command["output"].replace("@namespace@", namespace)

        resolved_commands.append(resolved_command)

    return resolved_commands
