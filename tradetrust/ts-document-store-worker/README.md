# README

This is a typescript project. It consists of two workers designed to work as ECS tasks. They're designed to efficiently issue/revoke documents using OA document store and OA framework.

Workflow(Batched Issue worker):
1. Restore batch. Restores a failed batch from a batch backup bucket. Restores unwrapped documents. It doesn't perform checks on a data the bucket contains because it assumes the data is valid because only Compose batch task can put data into it after validation.
1. Compose batch. A batch has two conditions determining that composition is done: size or time. The size based composition is a safeguard designed to prevent out of memory errors for the worker, this condition will complete batch composition when size of the unwrapped documents reaches certain limit. It's recomended to set maximum size to 25% of memory reserves because the worker also needs to store wrapped versions of the document which are larger than their unwrapped counterparts. The time based condition will complete batch when it reaches certain time limit from the moment when batch composition started. This stage also performs validation of the documents and saves validated documents in the backup bucket that can be used by Restore batch task.
1. Wrap batch. All documents that were composed into a batch will be wrapped to obtain common merkleRoot that allows issuing all of them using a single ```DocumentStore.issue``` operation.
1. Issue wrapped documents. At this stage a common merkleRoot will be issued. This stage has several special mechanisms to make it as smooth as possible:
  1. Automatic gas price adjustment up to a specified limit. Transaction can timeout on the ethereum blockchain network, this mechanism allows replacing transactions that took too long, preventing stuck state of the whole system. But it will never set a price higher than the specified limit, that will be used as a last maximum gas price to send a transaction after which worker will continue waiting until the transaction completes.
  1. Retry mechanisms that will prevent full restart from unexpected ethereum errors that can happen. Basically, if for some reason during any ethereum related operation the worker receives an unexpected error, it will try again specified number of times with a specified time interval. This mechanism gives an ability to not discard a whole wrapped batch if some network/blockchain node related error occurred.
1. Save batch. At this stage, processed documents will be saved into a specified bucket, and the batch backup will be cleared.

Workflow(Batched Revoke worker):
1. Restore batch. Same as in Batched Issue worker, but restores wrapped documents.
1. Compose batch. Same as in Batched Issue worker, but it uses wrapped versions of the documents instead of raw. Also, while batched(bulk) issue is not required, we need to set ```BATCH_SIZE_BYTES=1```. This way batch will be completed as soon as it receives the first document.
1. Revoke batch. Same as in Batched Issue worker, but instead of ```DocumentStore.issue``` it uses ```DocumentStore.bulkRevoke``` operation.
1. Save batch. Same as in Batched Issue worker.

So, overall after all of these stages successfully passed, documents from an unprocessed documents bucket will be deleted, and their wrapped and issued counterparts will be saved into the issued documents bucket.

## HOW TO RUN
1. ```make run-ts-worker```
1. ```make shell-document-store-worker```
    1. ```npm run start-batched-issue-worker``` - to compile and start Batched Issue worker
    1. ```npm run start-batched-revoke-worker``` - to compile and start Batched Revoke worker
    1. ```npm run test``` - to test and collect coverage

## BATCHED ISSUE WORKER SETTINGS(ENV):
```yaml
  # container / batched-issue-worker
  # container - for docker development
  # batched-issue-worker - for production run
  CONTAINER_MODE: container

  # string pointing to a blockchain node API endpoint
  BLOCKCHAIN_ENDPOINT: http://tradetrust-ganache-cli:8585

  AWS_ENDPOINT_URL: http://tradetrust-localstack:10001
  # for development purposes AWS_ACCESS_KEY_ID
  AWS_ACCESS_KEY_ID: access
  # for development purposes AWS_SECRET_ACCESS_KEY
  AWS_SECRET_ACCESS_KEY: secretaccess
  # for development purposes AWS_REGION
  AWS_REGION: us-east-1

  # filename containing document store address string or document store address string
  DOCUMENT_STORE_ADDRESS: /document-store-contract/addresses/DocumentStore.local.dev.address
  # kms base64 allowed as in libtrustbridge
  DOCUMENT_STORE_OWNER_PRIVATE_KEY: "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"

  UNPROCESSED_QUEUE_URL: http://tradetrust-localstack:10001/queue/unprocessed
  UNPROCESSED_BUCKET_NAME: unprocessed
  ISSUED_BUCKET_NAME: issued
  BATCH_BUCKET_NAME: batch

  # integer 0 <= MESSAGE_WAIT_TIME <= 20
  MESSAGE_WAIT_TIME: 10
  # integer 0 <= MESSAGE_VISIBILITY_TIMEOUT <= 43200
  MESSAGE_VISIBILITY_TIMEOUT: 60
  TRANSACTION_TIMEOUT_SECONDS: 600
  TRANSACTION_CONFIRMATION_THRESHOLD: 1

  # integer 0 < GAS_PRICE_LIMIT_GWEI
  GAS_PRICE_LIMIT_GWEI: 200
  # float 1.1 <= GAS_PRICE_MULTIPLIER
  # values < 1.1 will produce underpriced transaction errors
  GAS_PRICE_MULTIPLIER: 1.2
  # integer 0 < BATCH_SIZE_BYTES
  # 100 MB
  BATCH_SIZE_BYTES: 104857600
  # integer 0 < BATCH_TIME_SECONDS
  # 10 minutes
  BATCH_TIME_SECONDS: 600
  # number of attempts and interval between them in case of an unexpected error in RestoreBatch task
  # integer 1 <= RESTORE_ATTEMPTS
  RESTORE_ATTEMPTS: 10
  # integer 1 <= RESTORE_ATTEMPTS_INTERVAL_SECONDS
  RESTORE_ATTEMPTS_INTERVAL_SECONDS: 60
  # number of attempts and interval between them in case of an unexpected error in ComposeBatch task
  # integer 1 <= COMPOSE_ATTEMPTS
  COMPOSE_ATTEMPTS: 10
  # integer 1 <= COMPOSE_ATTEMPTS_INTERVAL_SECONDS
  COMPOSE_ATTEMPTS_INTERVAL_SECONDS: 60
  # number of attempts and interval between them in case of an unexpected error in SaveIssuedBatch task
  # integer 1 <= SAVE_ATTEMPTS
  SAVE_ATTEMPTS: 10
  # integer 1 <= SAVE_ATTEMPTS_INTERVAL_SECONDS
  SAVE_ATTEMPTS_INTERVAL_SECONDS: 60
  # number of attempts and interval between them in case of an unexpected error in IssueBatch task
  # integer 1 <= ISSUE_ATTEMPTS
  ISSUE_ATTEMPTS: 10
  # integer 1 <= ISSUE_ATTEMPTS_INTERVAL_SECONDS
  ISSUE_ATTEMPTS_INTERVAL_SECONDS: 60
```

## BATCHED REVOKE WORKER SETTINGS(ENV):
```yaml
  # container / batched-revoke-worker
  # container - for docker development
  # batched-revoke-worker - for production run
  CONTAINER_MODE: container

  # string pointing to a blockchain node API endpoint
  BLOCKCHAIN_ENDPOINT: http://tradetrust-ganache-cli:8585

  AWS_ENDPOINT_URL: http://tradetrust-localstack:10001
  # for development purposes AWS_ACCESS_KEY_ID
  AWS_ACCESS_KEY_ID: access
  # for development purposes AWS_SECRET_ACCESS_KEY
  AWS_SECRET_ACCESS_KEY: secretaccess
  # for development purposes AWS_REGION
  AWS_REGION: us-east-1

  # filename containing document store address string or document store address string
  DOCUMENT_STORE_ADDRESS: /document-store-contract/addresses/DocumentStore.local.dev.address
  # kms base64 allowed as in libtrustbridge
  DOCUMENT_STORE_OWNER_PRIVATE_KEY: "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"

  UNPROCESSED_QUEUE_URL: http://tradetrust-localstack:10001/queue/unprocessed
  UNPROCESSED_BUCKET_NAME: unprocessed
  REVOKED_BUCKET_NAME: revoked
  BATCH_BUCKET_NAME: batch

  # integer 0 <= MESSAGE_WAIT_TIME <= 20
  MESSAGE_WAIT_TIME: 10
  # integer 0 <= MESSAGE_VISIBILITY_TIMEOUT <= 43200
  MESSAGE_VISIBILITY_TIMEOUT: 60
  TRANSACTION_TIMEOUT_SECONDS: 600
  TRANSACTION_CONFIRMATION_THRESHOLD: 1

  # integer 0 < GAS_PRICE_LIMIT_GWEI
  GAS_PRICE_LIMIT_GWEI: 200
  # float 1.1 <= GAS_PRICE_MULTIPLIER
  # values < 1.1 will produce underpriced transaction errors
  GAS_PRICE_MULTIPLIER: 1.2
  # integer 0 < BATCH_SIZE_BYTES
  # 1 Byte, batch will be completed after it received a single file
  BATCH_SIZE_BYTES: 1
  # integer 0 < BATCH_TIME_SECONDS
  # 10 minutes
  BATCH_TIME_SECONDS: 600
  # number of attempts and interval between them in case of an unexpected error in RestoreBatch task
  # integer 1 <= RESTORE_ATTEMPTS
  RESTORE_ATTEMPTS: 10
  # integer 1 <= RESTORE_ATTEMPTS_INTERVAL_SECONDS
  RESTORE_ATTEMPTS_INTERVAL_SECONDS: 60
  # number of attempts and interval between them in case of an unexpected error in ComposeBatch task
  # integer 1 <= COMPOSE_ATTEMPTS
  COMPOSE_ATTEMPTS: 10
  # integer 1 <= COMPOSE_ATTEMPTS_INTERVAL_SECONDS
  COMPOSE_ATTEMPTS_INTERVAL_SECONDS: 60
  # number of attempts and interval between them in case of an unexpected error in SaveIssuedBatch task
  # integer 1 <= SAVE_ATTEMPTS
  SAVE_ATTEMPTS: 10
  # integer 1 <= SAVE_ATTEMPTS_INTERVAL_SECONDS
  SAVE_ATTEMPTS_INTERVAL_SECONDS: 60
  # number of attempts and interval between them in case of an unexpected error in IssueBatch task
  # integer 1 <= REVOKE_ATTEMPTS
  REVOKE_ATTEMPTS: 10
  # integer 1 <= REVOKE_ATTEMPTS_INTERVAL_SECONDS
  REVOKE_ATTEMPTS_INTERVAL_SECONDS: 60
```
