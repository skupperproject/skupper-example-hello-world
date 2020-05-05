from plano import *

def check_environment():
    call("kubectl version --client --short")
    call("skupper --version")
    call("curl --version")

# Eventually Kubernetes will make this nicer:
# https://github.com/kubernetes/kubernetes/pull/87399
# https://github.com/kubernetes/kubernetes/issues/80828
# https://github.com/kubernetes/kubernetes/issues/83094
def wait_for_resource(group, name, namespace=None):
    namespace_option = ""

    if namespace is not None:
        namespace_option = f"-n {namespace}"

    notice(f"Waiting for {group}/{name} to be available")

    for i in range(180):
        sleep(1)

        if call_for_exit_code(f"kubectl {namespace_option} get {group}/{name}") == 0:
            break
    else:
        fail(f"Timed out waiting for {group}/{name}")

    if group == "deployment":
        try:
            call(f"kubectl {namespace_option} wait --for condition=available --timeout 180s {group}/{name}")
        except:
            call(f"kubectl {namespace_option} logs {group}/{name}")
            raise

def wait_for_connection(name, namespace=None):
    namespace_option = ""

    if namespace is not None:
        namespace_option = f"-n {namespace}"

    try:
        call(f"skupper check-connection --wait 180 {name}")
    except:
        call("kubectl logs deployment/skupper-router")
        raise

def get_ingress_ip(group, name, namespace=None):
    wait_for_resource(group, name, namespace=namespace)

    namespace_option = ""

    if namespace is not None:
        namespace_option = f"-n {namespace}"

    for i in range(180):
        sleep(1)

        if call_for_stdout(f"kubectl {namespace_option} get {group}/{name} -o jsonpath='{{.status.loadBalancer.ingress}}'") != "":
            break
    else:
        fail(f"Timed out waiting for ingress for {group}/{name}")

    return call_for_stdout(f"kubectl {namespace_option} get {group}/{name} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'")
