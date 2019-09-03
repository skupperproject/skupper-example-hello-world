.phony: run
run:
	scripts/run

.phony: clean
clean:
	rm -rf scripts/__pycache__

.phony: update-%
update-%:
	curl -sfo scripts/$*.py "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py"
