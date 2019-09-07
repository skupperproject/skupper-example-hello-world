IMAGE := quay.io/skupper/hello-world-backend

.PHONY: build
build:
	podman build -t ${IMAGE} .

.PHONY: run
run: build
	podman run -p 8080:8080 ${IMAGE}

# Prerequisite: podman login quay.io
.PHONY: push
push: build
	podman push -q ${IMAGE}
