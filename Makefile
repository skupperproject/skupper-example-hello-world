# The run script requires that python3-flask and -requests are installed

.phony: run
run: build
	scripts/run

.phony: build
build:
	cd backend && make build
	cd frontend && make build

.phony: test
test:
#	scripts/test-minikube-one-cluster
	scripts/test-minikube-two-clusters

# Prerequisite: podman login quay.io
.PHONY: push
push: build
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
