# Hello World through Skupper on Kubernetes

The artifacts provided here will prepare your cluster, based on your
current $KUBECONFIG environment variable, by creating the namespaces,
deploying the HTTP application, initializing and linking the two Skupper
sites, then placing the `backend` Skupper service in the `west` namespace,
so that it is reachable for the `frontend` application.

## Deploying

```
make setup
```

## Verify

Run `make test` to verify your network.

## Teardown

Once you're done evaluating this example, just run: `make teardown` to
delete Skupper and remove the `east` and `west` namespaces.

## Customizing to use distinct clusters

If you look at the `inventory.yml` file, it has two hosts defined
(representing the two Skupper sites). You can simply place a `kubeconfig`
variable in each host (close to the `namespace`), then the scenario can be
deployed in different clusters.

Still in the inventory file, you will see that the `east` has a link defined
to the `west` site, so if you're going to use multiple clusters, make sure
that the `west` site is reachable from the `east` site, otherwise the link
won't be established.
