IMAGE := quay.io/skupper/hello-world-frontend

.PHONY: build
build:
	podman build -t ${IMAGE} .

.PHONY: run
run: build
	podman run -p 8080:8080 ${IMAGE}

.PHONY: debug
debug: build
	podman run -p 8080:8080 -it ${IMAGE} /bin/bash

# Prerequisite: podman login quay.io
.PHONY: push
push: build
	podman push -q ${IMAGE}
