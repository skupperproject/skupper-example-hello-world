.phony: run
run: build
	scripts/run

.phony: build
build:
	cd backend && make build
	cd frontend && make build

.phony: clean
clean:
	rm -rf scripts/__pycache__

.phony: update-%
update-%:
	curl -sfo scripts/$*.py "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py"
