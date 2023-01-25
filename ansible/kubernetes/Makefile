.PHONY: setup
setup: ansible-requirements
	@echo "Deploying to kubernetes using currenct \$$KUBECONFIG ($$KUBECONFIG)"
	@echo ""
	ansible-playbook -i inventory.yml setup.yml
	@echo ""
	@echo To test the frontend service, run: \$$ kubectl -n west port-forward service/frontend 8080:8080
	@echo then open your browser and go to http://127.0.0.1:8080
	@echo ""
	@echo Press CTRL-C when done
	@echo ""
	@echo "Use: make teardown to clean up"

.PHONY: test
test:
	@echo "Validating Skupper network"
	@echo ""
	ansible-playbook -i inventory.yml test.yml

.PHONY: teardown
teardown:
	@echo "Cleaning up kubernetes using currenct \$$KUBECONFIG ($$KUBECONFIG)"
	@echo ""
	ansible-playbook -i inventory.yml teardown.yml

.PHONY: ansible-requirements
ansible-requirements:
	@echo "Installing ansible requirements"
	ansible-galaxy collection install -r ../requirements.yml
	@echo ""
