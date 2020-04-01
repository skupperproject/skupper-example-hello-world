from plano import *

def run_test(west_kubeconfig, east_kubeconfig):
    connection_token = make_temp_file()

    with working_env(KUBECONFIG=west_kubeconfig):
        call("kubectl create namespace west")
        call("kubectl config set-context --current --namespace west")
        call("kubectl create deployment hello-world-frontend --image quay.io/skupper/hello-world-frontend")

        call("skupper init")

    with working_env(KUBECONFIG=east_kubeconfig):
        call("kubectl create namespace east")
        call("kubectl config set-context --current --namespace east")
        call("kubectl create deployment hello-world-backend --image quay.io/skupper/hello-world-backend")

        call("skupper init --edge")

    with working_env(KUBECONFIG=west_kubeconfig):
        wait_for_resource("deployment", "skupper-proxy-controller")
        wait_for_resource("deployment", "skupper-router")
        wait_for_resource("deployment", "hello-world-frontend")

        call("skupper status")
        call(f"skupper connection-token {connection_token}")

    with working_env(KUBECONFIG=east_kubeconfig):
        wait_for_resource("deployment", "skupper-proxy-controller")
        wait_for_resource("deployment", "skupper-router")
        wait_for_resource("deployment", "hello-world-backend")

        call("skupper status")
        call(f"skupper connect {connection_token} --connection-name east-west")

        try:
            call("skupper check-connection --wait 60 east-west")
        except:
            with working_env(KUBECONFIG=east_kubeconfig):
                call("kubectl logs deployment/skupper-router")

            with working_env(KUBECONFIG=west_kubeconfig):
                call("kubectl logs deployment/skupper-router")

            raise

        call("skupper expose deployment hello-world-backend --port 8080 --protocol http")

    with working_env(KUBECONFIG=west_kubeconfig):
        call("kubectl expose deployment/hello-world-frontend --port 8080 --type LoadBalancer")

        wait_for_resource("service", "hello-world-backend")

        ip = get_ingress_ip("hello-world-frontend")
        url = f"http://{ip}:8080/"

    try:
        call(f"curl -f {url}")
    except:
        with working_env(KUBECONFIG=east_kubeconfig):
            call("kubectl logs deployment/hello-world-backend")
            call("kubectl logs deployment/hello-world-backend-proxy")

        with working_env(KUBECONFIG=west_kubeconfig):
            call("kubectl logs deployment/hello-world-frontend")
            call("kubectl logs deployment/hello-world-backend-proxy")

        raise

    with working_env(KUBECONFIG=east_kubeconfig):
        call("skupper delete")
        call("kubectl delete service/hello-world-backend")
        call("kubectl delete deployment/hello-world-backend")

    with working_env(KUBECONFIG=west_kubeconfig):
        call("skupper delete")
        call("kubectl delete deployment/hello-world-frontend")

def check_environment():
    call("kubectl version")
    call("skupper version")
    call("curl --version")

# Eventually Kubernetes will make this nicer:
# https://github.com/kubernetes/kubernetes/pull/87399
# https://github.com/kubernetes/kubernetes/issues/80828
# https://github.com/kubernetes/kubernetes/issues/83094
def wait_for_resource(group, name):
    notice(f"Waiting for {group}/{name} to be available")

    for i in range(60):
        sleep(1)

        if call_for_exit_code(f"kubectl get {group}/{name}") == 0:
            break
    else:
        fail(f"Timed out waiting for {group}/{name}")

    if group == "deployment":
        try:
            call(f"kubectl wait --for condition=available --timeout 60s {group}/{name}")
        except:
            call(f"kubectl logs {group}/{name}")
            raise

def get_ingress_ip(service_name):
    wait_for_resource("service", service_name)

    for i in range(60):
        sleep(1)

        if call_for_stdout(f"kubectl get service/{service_name} -o jsonpath='{{.status.loadBalancer.ingress}}'") != "":
            break
    else:
        fail(f"Timed out waiting for ingress for {service_name}")

    return call_for_stdout(f"kubectl get service/{service_name} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'")
