.PHONY: setup
setup: ansible-requirements
	@echo "Deploying to podman"
	@echo ""
	ansible-playbook -i inventory.yml setup.yml
	@echo ""
	@echo "To test the frontend service:"
	@echo "open your browser and go to http://<west_ip>:8080"
	@echo ""
	@echo "Use: make teardown to clean up"

.PHONY: test
test:
	@echo "Validating Skupper network"
	@echo ""
	ansible-playbook -i inventory.yml test.yml
	
.PHONY: teardown
teardown:
	@echo "Cleaning up podman"
	@echo ""
	ansible-playbook -i inventory.yml teardown.yml

.PHONY: ansible-requirements
ansible-requirements:
	@echo "Installing ansible requirements"
	ansible-galaxy collection install -r ../requirements.yml
	@echo ""
