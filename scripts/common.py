from plano import *

def check_environment():
    def check_program(program):
        if which(program) is None:
            raise PlanoException(f"Required program {program} is not available")

    check_program("minikube")
    check_program("kubectl")
    check_program("skupper")
    check_program("curl")

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

def get_ingress_ip(service):
    wait_for_resource("service", service)

    for i in range(60):
        sleep(1)

        if call_for_stdout(f"kubectl get service/{service} -o jsonpath='{{.status.loadBalancer.ingress}}'") != "":
            break
    else:
        fail(f"Timed out waiting for ingress for {service}")

    return call_for_stdout(f"kubectl get service/{service} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'")
