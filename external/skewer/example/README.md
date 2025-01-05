<!-- NOTE: This file is generated from skewer.yaml.  Do not edit it directly. -->

# Skupper Hello World

[![main](https://github.com/skupperproject/skewer/actions/workflows/main.yaml/badge.svg)](https://github.com/skupperproject/skewer/actions/workflows/main.yaml)

#### A minimal HTTP application deployed across Kubernetes clusters using Skupper

This example is part of a [suite of examples][examples] showing the
different ways you can use [Skupper][website] to connect services
across cloud providers, data centers, and edge sites.

[website]: https://skupper.io/
[examples]: https://skupper.io/examples/index.html

#### Contents

* [Overview](#overview)
* [Prerequisites](#prerequisites)
* [Step 1: Access your Kubernetes clusters](#step-1-access-your-kubernetes-clusters)
* [Step 2: Install Skupper on your Kubernetes clusters](#step-2-install-skupper-on-your-kubernetes-clusters)
* [Step 3: Deploy the frontend and backend](#step-3-deploy-the-frontend-and-backend)
* [Step 4: Create your sites](#step-4-create-your-sites)
* [Step 5: Link your sites](#step-5-link-your-sites)
* [Step 6: Fail on demand](#step-6-fail-on-demand)
* [Step 7: Fail as expected](#step-7-fail-as-expected)
* [Step 8: Expose the backend service](#step-8-expose-the-backend-service)
* [Step 9: Access the frontend service](#step-9-access-the-frontend-service)
* [Cleaning up](#cleaning-up)
* [Summary](#summary)
* [Next steps](#next-steps)
* [About this example](#about-this-example)

## Overview

An overview

## Prerequisites

* Access to at least one Kubernetes cluster, from [any provider you
  choose][kube-providers].

* The `kubectl` command-line tool, version 1.15 or later
  ([installation guide][install-kubectl]).

* The `skupper` command-line tool, version 2.0 or later.  On Linux
  or Mac, you can use the install script (inspect it
  [here][cli-install-script]) to download and extract the command:

  ~~~ shell
  curl https://skupper.io/install.sh | sh -s -- --version 2.0.0-preview-2
  ~~~

  See [Installing the Skupper CLI][cli-install-docs] for more
  information.

[kube-providers]: https://skupper.io/start/kubernetes.html
[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[cli-install-script]: https://github.com/skupperproject/skupper-website/blob/main/input/install.sh
[cli-install-docs]: https://skupper.io/install/

## Step 1: Access your Kubernetes clusters

Skupper is designed for use with multiple Kubernetes clusters.
The `skupper` and `kubectl` commands use your
[kubeconfig][kubeconfig] and current context to select the cluster
and namespace where they operate.

[kubeconfig]: https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/

This example uses multiple cluster contexts at once. The
`KUBECONFIG` environment variable tells `skupper` and `kubectl`
which kubeconfig to use.

For each cluster, open a new terminal window.  In each terminal,
set the `KUBECONFIG` environment variable to a different path and
log in to your cluster.

_**West:**_

~~~ shell
export KUBECONFIG=~/.kube/config-west
<provider-specific login command>
~~~

_**East:**_

~~~ shell
export KUBECONFIG=~/.kube/config-east
<provider-specific login command>
~~~

**Note:** The login procedure varies by provider.  See the
documentation for yours:

* [Minikube](https://skupper.io/start/minikube.html#cluster-access)
* [Amazon Elastic Kubernetes Service (EKS)](https://skupper.io/start/eks.html#cluster-access)
* [Azure Kubernetes Service (AKS)](https://skupper.io/start/aks.html#cluster-access)
* [Google Kubernetes Engine (GKE)](https://skupper.io/start/gke.html#cluster-access)
* [IBM Kubernetes Service](https://skupper.io/start/ibmks.html#cluster-access)
* [OpenShift](https://skupper.io/start/openshift.html#cluster-access)

## Step 2: Install Skupper on your Kubernetes clusters

Using Skupper on Kubernetes requires the installation of the
Skupper custom resource definitions (CRDs) and the Skupper
controller.

For each cluster, use `kubectl apply` with the Skupper
installation YAML to install the CRDs and controller.

_**West:**_

~~~ shell
kubectl apply -f https://skupper.io/v2/install.yaml
~~~

_**East:**_

~~~ shell
kubectl apply -f https://skupper.io/v2/install.yaml
~~~

## Step 3: Deploy the frontend and backend

This example runs the frontend and the backend in separate
Kubernetes namespaces, on different clusters.

For each cluster, use `kubectl create namespace` and `kubectl
config set-context` to create the namespace you wish to use and
set the namespace on your current context.

Then, use `kubectl create deployment` to deploy the frontend in
West and the backend in East.

_**West:**_

~~~ shell
kubectl create namespace west
kubectl config set-context --current --namespace west
kubectl create deployment frontend --image quay.io/skupper/hello-world-frontend
~~~

_**East:**_

~~~ shell
kubectl create namespace east
kubectl config set-context --current --namespace east
kubectl create deployment backend --image quay.io/skupper/hello-world-backend --replicas 3
~~~

## Step 4: Create your sites

A Skupper _site_ is a location where your application workloads
are running.  Sites are linked together to form a network for your
application.

For each namespace, use `skupper site create` with a site name of
your choice.  This creates the site resource and deploys the
Skupper router to the namespace.

**Note:** If you are using Minikube, you need to [start minikube
tunnel][minikube-tunnel] before you run `skupper site create`.

<!-- XXX Explain enabling link acesss on one of the sites -->

[minikube-tunnel]: https://skupper.io/start/minikube.html#running-minikube-tunnel

_**West:**_

~~~ shell
skupper site create west --enable-link-access --timeout 2m
~~~

_Sample output:_

~~~ console
$ skupper site create west --enable-link-access --timeout 2m
Waiting for status...
Site "west" is configured. Check the status to see when it is ready
~~~

_**East:**_

~~~ shell
skupper site create east --timeout 2m
~~~

_Sample output:_

~~~ console
$ skupper site create east --timeout 2m
Waiting for status...
Site "east" is configured. Check the status to see when it is ready
~~~

You can use `skupper site status` at any time to check the status
of your site.

## Step 5: Link your sites

A Skupper _link_ is a channel for communication between two sites.
Links serve as a transport for application connections and
requests.

Creating a link requires the use of two Skupper commands in
conjunction: `skupper token issue` and `skupper token redeem`.
The `skupper token issue` command generates a secret token that
can be transferred to a remote site and redeemed for a link to the
issuing site.  The `skupper token redeem` command uses the token
to create the link.

**Note:** The link token is truly a *secret*.  Anyone who has the
token can link to your site.  Make sure that only those you trust
have access to it.

First, use `skupper token issue` in West to generate the token.
Then, use `skupper token redeem` in East to link the sites.

_**West:**_

~~~ shell
skupper token issue ~/secret.token
~~~

_Sample output:_

~~~ console
$ skupper token issue ~/secret.token
Waiting for token status ...

Grant "west-cad4f72d-2917-49b9-ab66-cdaca4d6cf9c" is ready
Token file /run/user/1000/skewer/secret.token created

Transfer this file to a remote site. At the remote site,
create a link to this site using the "skupper token redeem" command:

	skupper token redeem <file>

The token expires after 1 use(s) or after 15m0s.
~~~

_**East:**_

~~~ shell
skupper token redeem ~/secret.token
~~~

_Sample output:_

~~~ console
$ skupper token redeem ~/secret.token
Waiting for token status ...
Token "west-cad4f72d-2917-49b9-ab66-cdaca4d6cf9c" has been redeemed
You can now safely delete /run/user/1000/skewer/secret.token
~~~

If your terminal sessions are on different machines, you may need
to use `scp` or a similar tool to transfer the token securely.  By
default, tokens expire after a single use or 15 minutes after
being issued.

## Step 6: Fail on demand

_**West:**_

~~~ shell
if [ -n "${SKEWER_FAIL}" ]; then expr 1 / 0; fi
~~~

## Step 7: Fail as expected

_**West:**_

~~~ shell
expr 1 / 0
~~~

## Step 8: Expose the backend service

We now have our sites linked to form a Skupper network, but no
services are exposed on it.

Skupper uses _listeners_ and _connectors_ to expose services
across sites inside a Skupper network.  A listener is a local
endpoint for client connections, configured with a routing key.  A
connector exists in a remote site and binds a routing key to a
particular set of servers.  Skupper routers forward client
connections from local listeners to remote connectors with
matching routing keys.

In West, use the `skupper listener create` command to create a
listener for the backend.  In East, use the `skupper connector
create` command to create a matching connector.

_**West:**_

~~~ shell
skupper listener create backend 8080
~~~

_Sample output:_

~~~ console
$ skupper listener create backend 8080
Waiting for create to complete...
Listener "backend" is ready
~~~

_**East:**_

~~~ shell
skupper connector create backend 8080
~~~

_Sample output:_

~~~ console
$ skupper connector create backend 8080
Waiting for create to complete...
Connector "backend" is ready
~~~

The commands shown above use the name argument, `backend`, to also
set the default routing key and pod selector.  You can use the
`--routing-key` and `--selector` options to set specific values.

<!-- You can also use `--workload` -- more convenient! -->

## Step 9: Access the frontend service

In order to use and test the application, we need external access
to the frontend.

Use `kubectl port-forward` to make the frontend available at
`localhost:8080`.

_**West:**_

~~~ shell
kubectl port-forward deployment/frontend 8080:8080
~~~

You can now access the web interface by navigating to
[http://localhost:8080](http://localhost:8080) in your browser.

## Cleaning up

To remove Skupper and the other resources from this exercise, use
the following commands:

And more!

_**West:**_

~~~ shell
skupper site delete --all
kubectl delete deployment/frontend
~~~

_**East:**_

~~~ shell
skupper site delete --all
kubectl delete deployment/backend
~~~

## Summary

More summary

## Next steps

Check out the other [examples][examples] on the Skupper website.

More steps

## About this example

This example was produced using [Skewer][skewer], a library for
documenting and testing Skupper examples.

[skewer]: https://github.com/skupperproject/skewer

Skewer provides utility functions for generating the README and
running the example steps.  Use the `./plano` command in the project
root to see what is available.

To quickly stand up the example using Minikube, try the `./plano demo`
command.
