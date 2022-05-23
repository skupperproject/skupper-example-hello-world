# Skewer

[![main](https://github.com/skupperproject/skewer/actions/workflows/main.yaml/badge.svg)](https://github.com/skupperproject/skewer/actions/workflows/main.yaml)

A library for documenting and testing Skupper examples

A `skewer.yaml` file describes the steps and commands to achieve an
objective using Skupper.  Skewer takes the `skewer.yaml` file as input
and produces a `README.md` file and a test routine as output.

## An example example

[Example `skewer.yaml` file](test-example/skewer.yaml)

[Example `README.md` output](test-example/README.md)

[Example generate and test functions](test-example/Planofile)

## Setting up Skewer for your own example

Add the Skewer code as a subrepo in your project:

    cd project-dir/
    git subrepo clone https://github.com/skupperproject/skewer subrepos/skewer

Symlink the Skewer libraries into your `python` directory:

    mkdir -p python
    ln -s ../subrepos/skewer/python/skewer.strings python/skewer.strings
    ln -s ../subrepos/skewer/python/skewer.py python/skewer.py
    ln -s ../subrepos/skewer/python/plano.py python/plano.py

Symlink the `plano` command into the root of your project.  Copy the
example `Planofile` there as well:

    ln -s subrepos/skewer/plano
    cp subrepos/skewer/test-example/Planofile .

Use your editor to create a `skewer.yaml` file:

     emacs skewer.yaml

Run the `./plano` command to see what you can do: generate the
README and test your example.

     ./plano

## Installing Git Subrepo on Fedora

    dnf install git-subrepo

## Updating a Skewer subrepo inside your example project

Usually this will do what you want:

    git subrepo pull subrepos/skewer

If you made changes to the Skewer subrepo, the command above will ask
you to perform a merge.  You can use the procedure that the subrepo
tooling offers, but if you'd prefer to simply blow away your changes
and get the latest Skewer, you can use the following procedure:

    git subrepo clean subrepos/skewer
    git rm -rf subrepos/skewer/
    git commit -am "Temporarily remove the previous version of Skewer"
    git subrepo clone https://github.com/skupperproject/skewer subrepos/skewer

You should also be able to use `git subrepo pull --force`, to achieve
the same, but it didn't work with my version of Git Subrepo.

## Skewer YAML

The top level:

~~~ yaml
title:               # Your example's title (required)
subtitle:            # Your chosen subtitle (required)
github_actions_url:  # The URL of your workflow (optional)
overview:            # Text introducing your example (optional)
prerequisites:       # Text describing prerequisites (optional)
sites:               # A map of named sites.  See below.
steps:               # A list of steps.  See below.
summary:             # Text to summarize what the user did (optional)
cleaning_up:         # A special step for cleaning up (optional)
next_steps:          # Text linking to more examples (optional)
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
title:      # The step title (required)
preamble:   # Text before the commands (optional)
commands:   # Named groups of commands.  See below.
postamble:  # Text after the commands (optional)
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

Or you can use a named, canned step from the library of standard
steps:

~~~ yaml
standard: configure_separate_console_sessions
~~~

The initial steps are usually standard ones, so you may be able to use
this:

~~~ yaml
steps:
  - standard: configure_separate_console_sessions
  - standard: access_your_clusters
  - standard: set_up_your_namespaces
  - standard: install_skupper_in_your_namespaces
  - standard: check_the_status_of_your_namespaces
  - standard: link_your_namespaces
  [...]
~~~

The step commands are separated into named groups corresponding to the
sites.  Each named group contains a list of command entries.  Each
command entry has a `run` field containing a shell command and other
fields for awaiting completion or providing sample output.

A **command**:

~~~ yaml
run:                # A shell command (optional)
apply:              # Use this command only for "readme" or "test" (optional, default is both)
output:             # Sample output to include in the README (optional)
await:              # A resource or list of resources for which to await readiness (optional)
~~~

Only the `run` and `output` fields are used in the README content.
The `output` field is used as sample output only, not for any kind of
testing.

The `apply` field is useful when you want the readme instructions to
be different from the test procedure, or you simply want to omit
something.

The `await` field is often used by itself to pause for a condition you
require before going to the next step.  It is used only for testing
and does not impact the README.

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

Skewer has boilerplate strings for a lot of cases.  You can see what's
there in the `skewer.strings` file.  To include a string, use the
`!string` directive.

~~~ yaml
next_steps: !string next_steps
~~~
