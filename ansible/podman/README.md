# Hello World through Skupper on Podman

The artifacts provided here will prepare two Skupper sites running with Podman,
then it will run the `hello-world-frontend` application in the `west` site and
the `hello-world-backend` in the `east` site as podman containers connected to
a podman network named `helloworld`.

The `backend` container will be exposed at the `west` site by Skupper and the
`frontend` container will also be created and its port 8080 will be exposed in
the host machine.

## Connectivity

A Skupper site will be initialized for each IP/User through an SSH connection.
This sample expects that your current user is allowed to connect via SSH
with the respective IPs and the defined users using authorized keys.

Here is the default configuration (see: inventory.yml):

```yaml
    west_user: west
    west_ip: 192.168.124.1
    east_user: east
    east_ip: 192.168.124.1
```

Adjust as needed and make sure to copy your keys to the target users/ips.
You must use a valid IP address as it is used for ingress from the east site
to the west site.

Do not use localhost/127.0.0.1 as the IP addresses.

## Requirements

* SSH connection using authorized keys
* Podman v4+
* Skupper 1.3.0+ (binary) installed on the target machines
    ```
    The binary can also be installed by the skupper.network Ansible collection,
    by including the skupper_cli_install role.
    ```

## Deploying

```
make setup
```

## Verify

Run `make test` to verify your network.

## Teardown

Once you're done evaluating this example, just run: `make teardown` to
delete Skupper and the deployed containers from both sites.
