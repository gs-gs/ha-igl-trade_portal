# README

## Description

This project contains several key components of Tradetrust system excluding ones that oriented towards integrability of their system components. Here we're using components directly without a need of Tradetrust helpers. We're not using Tradetrust helpers not because they're bad or useless, but because the function that they do can be easily done by developers without a need to integrate Tradetrust helpers into the project.

## Components

1. `document-store-contract` - This is a development container used to deploy open-attestation document store to ganache blockchain emulator.
1. `document-store-worker` - This is the worker used to convert raw JSON documents put into a specified input bucket to open-attestation format and then issue them on a specified document store contract. After all, the issued document version stored at a specified output bucket. Currently works only with documents that already have the valid open-attestation schema of version 3. WIP.
1. `ganache-cli` - This is a blockchain emulator.
1. `localstack` - This is a AWS emulator.
1. `open-attestation-api` -  This is REST API wrapper of the open-attestation framework. The framework written in Typescript therefore we decided to wrap it into `aws-serverless-express` to make it usable by any language of our choice, currently it's a Python.
1. `open-attestation-verify-api` - This is REST API wrapper of oa-verify library. Also wrapped into `aws-serverless-express`.

## Production components description

### Document store worker

The document store worker uses S3 buckets to store and retrieve raw and issued JSON documents.
The document store worker reacts on PUT event that's emitted by a specified input bucket. It expects the event to be posted into a specified event queue. The queue is chosen as events proxy because it's a generally very versatile way of managing events for workers. The worker uses `open-attestation-api` serverless implementation to wrap documents.
To work with a document store contract the worker requires the contract `abi`, `address`  and the contract owner `public-key(address)`, `private key` to create and sign `document_store.issue(document)` operation transactions.

### How it works

1. document-store-worker listens to messages in the UNPROCESSED_QUEUE_URL where notifications about PUT events from the UNPROCESSED_BUCKET_NAME arrive
1. After message is received document-store-worker parses event to get a key of a document
1. document-store-worker loads the document from the input bucket (UNPROCESSED_BUCKET_NAME)
1. The document version is read from from the file (`version` key of the root json namespace)
1. The document is wrapped using `open-attestation-api` and previously obtained version id (if not wrapped yet)
1. If the document is valid continue, otherwise stop and delete the message from the queue.
1. Issue the wrapped document on a specified document store contract.
1. Put the wrapped document on a specified output bucket.
1. If any unexpected error occurred stop execution, but not delete the message
in case if error was caused by temporary reasons

The worker configured using environment variables:

1. `SENTRY_DSN`
1. `SENTRY_RELEASE`
1. `SENTRY_ENVIRONMENT`
1. `AWS_ENDPOINT_URL`
1. `AWS_ACCESS_KEY_ID`
1. `AWS_SECRET_ACCESS_KEY`
1. `AWS_DEFAULT_REGION`
1. `CONTAINER_MODE`

    * `production` - run the worker in production mode, without debug logs and tests.
    * `development` - run the worker in development mode, start with tests and exit if they fail, then start worker process with debug logs enabled.
    * `container` - run as container without starting worker process(wait indefinitely)

1. `OPEN_ATTESTATION_ENDPOINT` - `open-attestation-api` endpoint URL or file containing the endpoint URL.
1. `BLOCKCHAIN_ENDPOINT` - blockchain endpoint URL. Infura URL can be used.
1. `DOCUMENT_STORE_ABI` - path to a file JSON containing the document store contract `abi`. `abi` must be located at `.["abi"]`.
1. `DOCUMENT_STORE_ADDRESS` - path to single line text file containing the document store contract address.
1. `DOCUMENT_STORE_OWNER_PUBLIC_KEY` - the document store creator wallet address
1. `DOCUMENT_STORE_OWNER_PRIVATE_KEY` - the document store creator wallet private key
1. `UNPROCESSED_QUEUE_URL` - `unprocessed` bucket events proxy queue
1. `UNPROCESSED_BUCKET_NAME` - input bucket name
1. `ISSUED_BUCKET_NAME` - output bucket name
1. `WORKER_POLLING_INTERVAL_SECONDS` - interval between worker's `poll` operations
1. `WORKER_POLLING_MAX_NUMBER_OF_MESSAGES` - max number of messages received during single `poll` operation.
1. `WORKER_POLLING_MESSAGE_WAIT_TIME_SECONDS` - time `poll` operation waits for message(s) to appear in the queue
1. `WORKER_POLLING_VISIBILITY_TIMEOUT` - how long message remains invisible after `poll` operation retrieved it from the queue. Time measured in seconds. Minimal/default value is `60`

### Testing

```bash
    cd tradetrust
    make run
    ## Wait until `localstack` finishes resource deployment.
    make shell-document-store-worker
    make test-debug
    ##You'll see test results along with some debug messages describing the workflow.
```

### Open attestation API

Serverless(`api gateway` + `lamda`) open attestation framework REST API wrapper.
It's running using 2 appoaches: local setups of ApiGw+Lambda or just a normal Express app started and listening port 9090. To use ApiGw one you shoudln't rely on the output from the container and just read the `localstack/oa-api.endpoint` file and see the endpoint there. Add `document/wrap` for example to use it. In case of 9090 port it's `http://localhost:9090/document/wrap` and in case of ApiGw approach you should ssh to the container first and then use the `{endpoint}document/wrap` url (or add localstack to some network and access it from there).

Example of the python script doing it (get the valid document format from the test folder)

```python
    #!/usr/bin/env python
    from pprint import pprint
    import requests

    doc_value = {
        "reference": "SERIAL_NUMBER_123",
        "name": "Singapore Driving Licence",
        ...
    }

    resp = requests.post(
        "http://localhost:9090/document/wrap",
        json={
            "document": doc_value,
        }
    )

    pprint(resp.json())
```

[API Specification](open-attestation-api/api.yml)

### Open attestation verify API

Just like `open-attestation-api` has two modes to run: `server`, Serverless(`api gateway` + `lamda`). In the server mode it is listening on `localhost:9091`.

#### Configuration(ENV)

1. `ETHEREUM_PROVIDER` - `cloudflare` or `infura`. NOTE: `cloudflare` only works with `mainnet`.
1. `INFURA_API_KEY` - used to connect to infura node when `infura` provider is used.
1. `ETHEREUM_NETWORK` - used to specify network that is used to look for smart contracts. Values: `mainnet`, `ropsten`, etc. Default: `ropsten`.

[API Specification](open-attestation-verify-api/api.yml)
