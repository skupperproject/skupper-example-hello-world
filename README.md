# Skupper Hello World

<!-- [![Build Status](https://travis-ci.org/skupperproject/skupper-example-xxx.svg?branch=master)](https://travis-ci.org/skupperproject/skupper-example-xxx) -->

A minimal HTTP application using [Skupper](https://skupper.io/)

* [Overview](#overview)
* [Prerequisites](#prerequisites)
* [Step 1: Set up your namespaces](#step-1-set-up-your-namespaces)
* [Step 2: Connect your namespaces](#step-2-connect-your-namespaces)
* [Step 3: Deploy the backend and frontend services](#step-3-deploy-the-backend-and-frontend-services)
* [Step 4: Expose the backend service on the Skupper network](#step-4-expose-the-backend-service-on-the-skupper-network)
* [Step 5: Test the application](#step-5-test-the-application)
* [Cleaning up](#cleaning-up)
* [Next steps](#next-steps)

## Overview

This example is a very simple multi-service HTTP application that can
be deployed across multiple Kubernetes clusters using Skupper.

It contains two services:

* A backend service that exposes an `/api/hello` endpoint.
* A frontend service that accepts HTTP requests and returns a
  greeting.

To process a request, the frontend calls the backend to fetch a new
greeting.

## Prerequisites

* The `kubectl` command-line tool, version 1.15 or later ([installation guide](https://kubernetes.io/docs/tasks/tools/install-kubectl/))
* The `skupper` command-line tool, the latest version ([installation guide](file:///home/jross/code/skupper-website/output/start/index.html#step-1-install-the-skupper-command-line-tool-in-your-environment))
* Two Kubernetes namespaces, from any providers you choose, on any clusters you choose

## Step 1: Set up your namespaces

Console for namespace 1:

    export KUBECONFIG=$HOME/.kube/config-ns1
    <login-command-for-your-provider>
    kubectl create namespace ns1
    kubectl config set-context --current --namespace ns1
    skupper init

Console for namespace 2:

    export KUBECONFIG=$HOME/.kube/config-ns2
    <login-command-for-your-provider>
    kubectl create namespace ns2
    kubectl config set-context --current --namespace ns2
    skupper init

See [Getting started with Skupper](https://skupper.io/start/) for more
information about setting up namespaces.

## Step 2: Connect your namespaces

Namespace 1:

    skupper connection-token $HOME/secret.yaml

Namespace 2:

    skupper connect $HOME/secret.yaml

## Step 3: Deploy the backend and frontend services

Namespace 1:

    kubectl create deployment hello-world-backend --image quay.io/skupper/hello-world-backend
    kubectl expose deployment/hello-world-backend --port 8080

Namespace 2:

    kubectl create deployment hello-world-frontend --image quay.io/skupper/hello-world-frontend
    kubectl expose deployment/hello-world-frontend --port 8080 --type LoadBalancer

## Step 4: Expose the backend service on the Skupper network

Namespace 1:

    kubectl annotate service/hello-world-backend skupper.io/proxy=http

Namespace 2:

    $ kubectl get services
    NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)          AGE
    [...]
    hello-world-backend    ClusterIP      10.106.92.175    <none>           8080/TCP         11h
    hello-world-frontend   LoadBalancer   10.111.133.137   10.111.133.137   8080:31313/TCP   6m31s
    [...]

## Step 5: Test the application

Namespace 2:

    curl $(kubectl get service/hello-world-frontend -o jsonpath='http://{.status.loadBalancer.ingress[0].ip}:{.spec.ports[0].port}/')

Sample output:

    I am the frontend.  The backend says 'Hello 1'.

## Cleaning up

Namespace 1:

    skupper delete
    kubectl delete service/hello-world-backend
    kubectl delete deployment/hello-world-backend

Namespace 2:

    skupper delete
    kubectl delete service/hello-world-frontend
    kubectl delete deployment/hello-world-frontend

## Next steps

 - [Try our minimal example for TCP-based communication](https://github.com/skupperproject/skupper-example-tcp-echo)
 - [Find more examples](https://skupper.io/examples/)
