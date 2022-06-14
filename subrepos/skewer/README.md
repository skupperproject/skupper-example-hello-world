# Skewer

[![main](https://github.com/skupperproject/skewer/actions/workflows/main.yaml/badge.svg)](https://github.com/skupperproject/skewer/actions/workflows/main.yaml)

A library for documenting and testing Skupper examples

A `skewer.yaml` file describes the steps and commands to achieve an
objective using Skupper.  Skewer takes the `skewer.yaml` file as input
and produces two outputs: a `README.md` file and a test routine.

## An example example

[Example `skewer.yaml` file](test-example/skewer.yaml)

[Example `README.md` output](test-example/README.md)

## Setting up Skewer for your own example

Make sure you have git-subrepo installed:

    dnf install git-subrepo

Add the Skewer code as a subrepo in your example project:

    cd project-dir/
    git subrepo clone https://github.com/skupperproject/skewer subrepos/skewer

Symlink the Skewer libraries into your `python` directory:

    mkdir -p python
    ln -s ../subrepos/skewer/python/skewer.py python/skewer.py
    ln -s ../subrepos/skewer/python/plano.py python/plano.py

Symlink the `plano` command into the root of your project.  Symlink
the standard `example.planofile` as `.planofile` in the root as well:

    ln -s subrepos/skewer/plano
    ln -s subrepos/skewer/example.planofile .planofile

Use your editor to create a `skewer.yaml` file in the root of your
project:

    emacs skewer.yaml

Run the `./plano` command to see the available commands:

~~~ console
$ ./plano
usage: plano [--verbose] [--quiet] [--debug] [-h] [-f FILE] {test,generate,render,run,run-external,demo} ...

options:
  --verbose             Print detailed logging to the console
  --quiet               Print no logging to the console
  --debug               Print debugging output to the console
  -h, --help            Show this help message and exit
  -f FILE, --file FILE  Load commands from FILE (default 'Planofile' or '.planofile')

commands:
  {test,generate,render,run,run-external,demo}
    test                Test README generation and run the steps on Minikube
    generate            Generate README.md from the data in skewer.yaml
    render              Render README.html from the data in skewer.yaml
    run                 Run the example steps using Minikube
    run-external        Run the example steps against external clusters
    demo                Run the example steps and pause before cleaning up
~~~

## Updating a Skewer subrepo inside your example project

Use `git subrepo pull`:

    git subrepo pull --force subrepos/skewer

Some older versions of git-subrepo won't complete a force pull.  If
that happens, you can simply blow away your changes and get the latest
Skewer, using these commands:

    git subrepo clean subrepos/skewer
    git rm -rf subrepos/skewer/
    git commit -am "Temporarily remove the previous version of Skewer"
    git subrepo clone https://github.com/skupperproject/skewer subrepos/skewer

## Skewer YAML

The top level:

~~~ yaml
title:              # Your example's title (required)
subtitle:           # Your chosen subtitle (required)
github_actions_url: # The URL of your workflow (optional)
overview:           # Text introducing your example (optional)
prerequisites:      # Text describing prerequisites (optional, has default text)
sites:              # A map of named sites.  See below.
steps:              # A list of steps.  See below.
summary:            # Text to summarize what the user did (optional)
next_steps:         # Text linking to more examples (optional, has default text)
~~~

A **site**:

~~~ yaml
<site-name>:
  kubeconfig: <kubeconfig-file>  # (required)
  namespace: <namespace-name>    # (required)
~~~

A tilde (~) in the kubeconfig file path is replaced with a temporary
working directory during testing.

Example sites:

~~~ yaml
sites:
  east:
    kubeconfig: ~/.kube/config-east
    namespace: east
  west:
    kubeconfig: ~/.kube/config-west
    namespace: west
~~~

A **step**:

~~~ yaml
- title:            # The step title (required)
  preamble:         # Text before the commands (optional)
  commands:         # Named groups of commands.  See below.
  postamble:        # Text after the commands (optional)
~~~

An example step:

~~~ yaml
steps:
  - title: Expose the frontend service
    preamble: |
      We have established connectivity between the two namespaces and
      made the backend in `east` available to the frontend in `west`.
      Before we can test the application, we need external access to
      the frontend.

      Use `kubectl expose` with `--type LoadBalancer` to open network
      access to the frontend service.  Use `kubectl get services` to
      check for the service and its external IP address.
    commands:
      east: <list-of-commands>
      west: <list-of-commands>
~~~

Or you can use a named step from the library of standard steps:

~~~ yaml
- standard: configure_separate_console_sessions
~~~

The standard steps are defined in
[python/skewer.yaml](python/skewer.yaml).

You can override the `title`, `preamble`, `commands`, or `postamble`
field of a standard step by adding the field in addition to
`standard`:

~~~ yaml
- standard: cleaning_up
  commands:
    east:
     - run: skupper delete
     - run: kubectl delete deployment/database
    west:
     - run: skupper delete
~~~

The initial steps are usually standard ones.  There are also some
standard steps at the end.  You may be able to use something like
this:

~~~ yaml
steps:
  - standard: configure_separate_console_sessions
  - standard: access_your_clusters
  - standard: set_up_your_namespaces
  - standard: install_skupper_in_your_namespaces
  - standard: check_the_status_of_your_namespaces
  - standard: link_your_namespaces
  <your-custom-steps>
  - standard: test_the_application
  - standard: accessing_the_web_console
  - standard: cleaning_up
~~~

Note that the `link_your_namespaces` and `test_the_application` steps
are less generic than the other steps, so check that the text and
commands they produce are doing what you need.  If not, you'll need to
provide a custom step.

The step commands are separated into named groups corresponding to the
sites.  Each named group contains a list of command entries.  Each
command entry has a `run` field containing a shell command and other
fields for awaiting completion or providing sample output.

A **command**:

~~~ yaml
- run:              # A shell command (required)
  apply:            # Use this command only for "readme" or "test" (optional, default is both)
  output:           # Sample output to include in the README (optional)
~~~

Only the `run` and `output` fields are used in the README content.
The `output` field is used as sample output only, not for any kind of
testing.

The `apply` field is useful when you want the readme instructions to
be different from the test procedure, or you simply want to omit
something.

There is also a special `await` command you can use to pause for a
condition you require before going to the next step.  It is used only
for testing and does not impact the README.

~~~ yaml
- await:            # A resource or list of resources for which to await readiness (optional)
~~~

Example commands:

~~~ yaml
commands:
  east:
    - run: kubectl expose deployment/backend --port 8080 --type LoadBalancer
      output: |
        service/frontend exposed
  west:
    - await: service/backend
    - run: kubectl get service/backend
      output: |
        NAME          TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)         AGE
        backend       ClusterIP      10.102.112.121   <none>           8080/TCP        30s
~~~

## Demo mode

Skewer has a mode where it executes all the steps, but before cleaning
up and exiting, it pauses so you can inspect things.

It is enabled by setting the environment variable `SKEWER_DEMO` to any
value when you call `./plano run` or one of its variants.  You can
also use `./plano demo`, which sets the variable for you.
