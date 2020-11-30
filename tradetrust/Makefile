.PHONY: run
.ONESHELL:
run:
	@ docker-compose up --build --remove-orphans --renew-anon-volumes

.PHONY: run-on-servers
.ONESHELL:
run-on-servers:
	@ docker-compose -f docker-compose.servers.yml up --build --remove-orphans --renew-anon-volumes

.PHONY: run-testnet-test
.ONESHELL:
run-testnet-test:
	@ docker-compose -f docker-compose.testnet.yml up --build --remove-orphans --renew-anon-volumes

.PHONY: stop
.ONESHELL:
stop:
	@ docker-compose down

.PHONY: clean
.ONESHELL:
clean:
	@ docker-compose down --rmi all --volumes


.PHONY: build
.ONESHELL:
build:
	@ docker-compose build --no-cache


.PHONY: shell-document-store-api
.ONESHELL:
shell-document-store-api:
	@ docker-compose exec document-store-api /bin/bash


.PHONY: shell-document-store-contract
.ONESHELL:
shell-document-store-contract:
	@ docker-compose exec document-store-contract /bin/bash


.PHONY: shell-ganache-cli
.ONESHELL:
shell-ganache-cli:
	@ docker-compose exec ganache-cli /bin/sh


.PHONY: shell-localstack
.ONESHELL:
shell-localstack:
	@ docker-compose exec localstack /bin/sh


.PHONY: shell-open-attestation-api
.ONESHELL:
shell-open-attestation-api:
	@ docker-compose exec open-attestation-api /bin/bash


.PHONY: shell-open-attestation-verify-api
.ONESHELL:
shell-open-attestation-verify-api:
	@ docker-compose exec open-attestation-verify-api /bin/bash


.PHONY: shell-document-store-worker
.ONESHELL:
shell-document-store-worker:
	@ docker-compose exec document-store-worker /bin/bash


.PHONY: shell-monitoring
.ONESHELL:
shell-monitoring:
	@ docker-compose exec monitoring /bin/bash
