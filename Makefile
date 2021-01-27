.PHONY: test
test:
	python3 scripts/test-minikube

.PHONY: demo
demo:
	SKUPPER_DEMO=1 python3 scripts/test-minikube

.PHONY: build-images
build-images:
	cd backend && make build
	cd frontend && make build

# Prerequisite: podman login quay.io
.PHONY: push-images
push-images: build-images
	cd backend && make push
	cd frontend && make push

.phony: clean
clean:
	rm -rf scripts/__pycache__
	rm -f README.html

README.html: README.md
	pandoc -o $@ $<
