from skewer import *

def run_test(west_kubeconfig, east_kubeconfig):
    link_token = make_temp_file()

    with working_env(KUBECONFIG=west_kubeconfig):
        run("kubectl create namespace west")
        run("kubectl config set-context --current --namespace west")
        run("kubectl create deployment hello-world-frontend --image quay.io/skupper/hello-world-frontend")

        run("skupper init")

    with working_env(KUBECONFIG=east_kubeconfig):
        run("kubectl create namespace east")
        run("kubectl config set-context --current --namespace east")
        run("kubectl create deployment hello-world-backend --image quay.io/skupper/hello-world-backend")

        run("skupper init --ingress none")

    with working_env(KUBECONFIG=west_kubeconfig):
        await_resource("deployment", "skupper-service-controller")
        await_resource("deployment", "skupper-router")
        await_resource("deployment", "hello-world-frontend")

        run("skupper status")
        run(f"skupper token create {link_token}")

    with working_env(KUBECONFIG=east_kubeconfig):
        await_resource("deployment", "skupper-service-controller")
        await_resource("deployment", "skupper-router")
        await_resource("deployment", "hello-world-backend")

        run("skupper status")
        run(f"skupper link create {link_token} --name east-west")

        await_link("east-west")

        run("skupper expose deployment/hello-world-backend --port 8080")

    with working_env(KUBECONFIG=west_kubeconfig):
        run("kubectl expose deployment/hello-world-frontend --port 8080 --type LoadBalancer")

        await_resource("service", "hello-world-backend")

        frontend_ip = get_ingress_ip("service", "hello-world-frontend")
        frontend_url = f"http://{frontend_ip}:8080/"

    # XXX Replace this with a wait operation when it's available
    sleep(30)

    try:
        for i in range(10):
            run(f"curl -f {frontend_url}")
    except:
        with working_env(KUBECONFIG=east_kubeconfig):
            run("kubectl logs deployment/hello-world-backend")

        with working_env(KUBECONFIG=west_kubeconfig):
            run("kubectl logs deployment/hello-world-frontend")

        raise

    if "SKUPPER_DEMO" in ENV:
        with working_env(KUBECONFIG=west_kubeconfig):
            console_ip = get_ingress_ip("service", "skupper-controller")
            console_url = f"http://{console_ip}:8080/"
            password_data = call("kubectl get secret skupper-console-users -o jsonpath='{.data.admin}'")
            password = base64_decode(password_data).decode("ascii")

        print()
        print("Demo time!")
        print()
        print(f"West kubeconfig: export KUBECONFIG={west_kubeconfig}")
        print(f"East kubeconfig: export KUBECONFIG={east_kubeconfig}")
        print(f"Frontend URL: {frontend_url}")
        print(f"Console URL: {console_url}")
        print("User: admin")
        print(f"Password: {password}")
        print()

        while input("Are you done (yes)? ") != "yes":
            pass

    with working_env(KUBECONFIG=east_kubeconfig):
        run("skupper delete")
        run("kubectl delete deployment/hello-world-backend")

    with working_env(KUBECONFIG=west_kubeconfig):
        run("skupper delete")
        run("kubectl delete deployment/hello-world-frontend")
