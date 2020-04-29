.phony: test
test:
	python3 scripts/test-minikube

.phony: demo
demo:
	SKUPPER_DEMO=1 scripts/test-minikube

.phony: build-images
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

.phony: update-%
update-%:
	curl -sfo scripts/$*.py "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py"
