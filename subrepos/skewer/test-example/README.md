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
* [Step 1: Configure separate console sessions](#step-1-configure-separate-console-sessions)
* [Step 2: Access your clusters](#step-2-access-your-clusters)
* [Step 3: Set up your namespaces](#step-3-set-up-your-namespaces)
* [Step 4: Install Skupper in your namespaces](#step-4-install-skupper-in-your-namespaces)
* [Step 5: Check the status of your namespaces](#step-5-check-the-status-of-your-namespaces)
* [Step 6: Link your namespaces](#step-6-link-your-namespaces)
* [Step 7: Deploy the frontend and backend services](#step-7-deploy-the-frontend-and-backend-services)
* [Step 8: Expose the backend service](#step-8-expose-the-backend-service)
* [Step 9: Expose the frontend service](#step-9-expose-the-frontend-service)
* [Step 10: Test the application](#step-10-test-the-application)
* [Summary](#summary)
* [Cleaning up](#cleaning-up)
* [Next steps](#next-steps)

## Overview

This example is a very simple multi-service HTTP application that can
be deployed across multiple Kubernetes clusters using Skupper.

It contains two services:

* A backend service that exposes an `/api/hello` endpoint.  It
  returns greetings of the form `Hello from <pod-name>
  (<request-count>)`.

* A frontend service that accepts HTTP requests, calls the backend
  to fetch new greetings, and serves them to the user.

With Skupper, you can place the backend in one cluster and the
frontend in another and maintain connectivity between the two
services without exposing the backend to the public internet.

<img src="images/entities.svg" width="640"/>

## Prerequisites

* The `kubectl` command-line tool, version 1.15 or later
  ([installation guide][install-kubectl])

* The `skupper` command-line tool, the latest version ([installation
  guide][install-skupper])

* Access to at least one Kubernetes cluster, from any provider you
  choose

[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[install-skupper]: https://skupper.io/install/index.html

## Step 1: Configure separate console sessions

Skupper is designed for use with multiple namespaces, typically on
different clusters.  The `skupper` command uses your
[kubeconfig][kubeconfig] and current context to select the namespace
where it operates.

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

Console for _west_:

~~~ shell
export KUBECONFIG=~/.kube/config-west
~~~

Console for _east_:

~~~ shell
export KUBECONFIG=~/.kube/config-east
~~~

## Step 2: Access your clusters

The methods for accessing your clusters vary by Kubernetes provider.
Find the instructions for your chosen providers and use them to
authenticate and configure access for each console session.  See the
following links for more information:

* [Minikube](https://skupper.io/start/minikube.html)
* [Amazon Elastic Kubernetes Service (EKS)](https://skupper.io/start/eks.html)
* [Azure Kubernetes Service (AKS)](https://skupper.io/start/aks.html)
* [Google Kubernetes Engine (GKE)](https://skupper.io/start/gke.html)
* [IBM Kubernetes Service](https://skupper.io/start/ibmks.html)
* [OpenShift](https://skupper.io/start/openshift.html)
* [More providers](https://kubernetes.io/partners/#kcsp)

## Step 3: Set up your namespaces

Use `kubectl create namespace` to create the namespaces you wish to
use (or use existing namespaces).  Use `kubectl config set-context` to
set the current namespace for each session.

Console for _west_:

~~~ shell
kubectl create namespace west
kubectl config set-context --current --namespace west
~~~

Console for _east_:

~~~ shell
kubectl create namespace east
kubectl config set-context --current --namespace east
~~~

## Step 4: Install Skupper in your namespaces

The `skupper init` command installs the Skupper router and service
controller in the current namespace.  Run the `skupper init` command
in each namespace.

[minikube-tunnel]: https://skupper.io/start/minikube.html#running-minikube-tunnel

**Note:** If you are using Minikube, [you need to start `minikube
tunnel`][minikube-tunnel] before you install Skupper.

Console for _west_:

~~~ shell
skupper init
~~~

Console for _east_:

~~~ shell
skupper init --ingress none
~~~

Here we are using `--ingress none` in one of the namespaces simply to
make local development with Minikube easier.  (It's tricky to run two
Minikube tunnels on one host.)  The `--ingress none` option is not
required if your two namespaces are on different hosts or on public
clusters.

## Step 5: Check the status of your namespaces

Use `skupper status` in each console to check that Skupper is
installed.

Console for _west_:

~~~ shell
skupper status
~~~

Console for _east_:

~~~ shell
skupper status
~~~

You should see output like this for each namespace:

~~~
Skupper is enabled for namespace "<namespace>" in interior mode. It is not connected to any other sites. It has no exposed services.
The site console url is: http://<address>:8080
The credentials for internal console-auth mode are held in secret: 'skupper-console-users'
~~~

As you move through the steps below, you can use `skupper status` at
any time to check your progress.

## Step 6: Link your namespaces

Creating a link requires use of two `skupper` commands in conjunction,
`skupper token create` and `skupper link create`.

The `skupper token create` command generates a secret token that
signifies permission to create a link.  The token also carries the
link details.  Then, in a remote namespace, The `skupper link create`
command uses the token to create a link to the namespace that
generated it.

**Note:** The link token is truly a *secret*.  Anyone who has the
token can link to your namespace.  Make sure that only those you trust
have access to it.

First, use `skupper token create` in one namespace to generate the
token.  Then, use `skupper link create` in the other to create a link.

Console for _west_:

~~~ shell
skupper token create ~/west.token
~~~

Console for _east_:

~~~ shell
skupper link create ~/west.token
skupper link status --wait 30
~~~

If your console sessions are on different machines, you may need to
use `scp` or a similar tool to transfer the token.

## Step 7: Deploy the frontend and backend services

Use `kubectl create deployment` to deploy the frontend service
in `west` and the backend service in `east`.

Console for _west_:

~~~ shell
kubectl create deployment hello-world-frontend --image quay.io/skupper/hello-world-frontend
~~~

Console for _east_:

~~~ shell
kubectl create deployment hello-world-backend --image quay.io/skupper/hello-world-backend
~~~

## Step 8: Expose the backend service

We now have two namespaces linked to form a Skupper network, but
no services are exposed on it.  Skupper uses the `skupper
expose` command to select a service from one namespace for
exposure on all the linked namespaces.

Use `skupper expose` to expose the backend service to the
frontend service.

Console for _east_:

~~~ shell
skupper expose deployment/hello-world-backend --port 8080
~~~

Sample output:

~~~
NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)          AGE
hello-world-backend    ClusterIP      10.106.92.175    <none>           8080/TCP         1m31s
~~~

## Step 9: Expose the frontend service

We have established connectivity between the two namespaces and
made the backend in `east` available to the frontend in `west`.
Before we can test the application, we need external access to
the frontend.

Use `kubectl expose` with `--type LoadBalancer` to open network
access to the frontend service.  Use `kubectl get services` to
check for the service and its external IP address.

Console for _west_:

~~~ shell
kubectl expose deployment/hello-world-frontend --port 8080 --type LoadBalancer
kubectl get services
~~~

Sample output:

~~~
$ kubectl expose deployment/hello-world-frontend --port 8080 --type LoadBalancer
service/hello-world-frontend exposed

$ kubectl get services
NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)                           AGE
hello-world-backend    ClusterIP      10.102.112.121   <none>           8080/TCP                          30s
hello-world-frontend   LoadBalancer   10.98.170.106    10.98.170.106    8080:30787/TCP                    2s
skupper                LoadBalancer   10.101.101.208   10.101.101.208   8080:31494/TCP                    82s
skupper-router         LoadBalancer   10.110.252.252   10.110.252.252   55671:32111/TCP,45671:31193/TCP   86s
skupper-router-local   ClusterIP      10.96.123.13     <none>           5671/TCP                          86s
~~~

## Step 10: Test the application

Look up the external URL and use `curl` to send a request.

Console for _west_:

~~~ shell
curl $(kubectl get service hello-world-frontend -o jsonpath='http://{.status.loadBalancer.ingress[0].ip}:8080/')
~~~

Sample output:

~~~
I am the frontend.  The backend says 'Hello from hello-world-backend-869cd94f69-wh6zt (1)'.
~~~

**Note:** If the embedded `kubectl get` command fails to get the
IP address, you can find it manually by running `kubectl get
services` and looking up the external IP of the
`hello-world-frontend` service.

## Summary

This example locates the frontend and backend services in different
namespaces, on different clusters.  Ordinarily, this means that they
have no way to communicate unless they are exposed to the public
internet.

Introducing Skupper into each namespace allows us to create a virtual
application network that can connect services in different clusters.
Any service exposed on the application network is represented as a
local service in all of the linked namespaces.

The backend service is located in `east`, but the frontend service
in `west` can "see" it as if it were local.  When the frontend
sends a request to the backend, Skupper forwards the request to the
namespace where the backend is running and routes the response back to
the frontend.

<img src="images/sequence.svg" width="640"/>

## Cleaning up

To remove Skupper and the other resources from this exercise, use the
following commands.

Console for _west_:

~~~ shell
skupper delete
kubectl delete service/hello-world-frontend
kubectl delete deployment/hello-world-frontend
~~~

Console for _east_:

~~~ shell
skupper delete
kubectl delete deployment/hello-world-backend
~~~

## Next steps

Check out the other [examples][examples] on the Skupper website.
