import os
import time
import json
from unittest import mock
from string import Template
from src.config import Config
from src.worker import Worker


@mock.patch.dict(
    os.environ,
    {
        'WORKER_POLLING_MESSAGE_WAIT_TIME_SECONDS': '1',
        'BLOCKCHAIN_GAS_PRICE' : 'fast'
    }
)
def test(unprocessed_queue, unprocessed_bucket, issued_bucket, unwrap, wrap):
    config = Config.from_environ()
    document_store_address = config['DocumentStore']['Address']
    # overriding safe VisibilityTimeout
    config['Worker']['Polling']['VisibilityTimeout'] = 1
    queue_test_wait_time_seconds = config['Worker']['Polling']['VisibilityTimeout'] * 2
    with open('/document-store-worker/tests/data/document.v2.json', 'rt') as f:
        document_v2 = Template(f.read()).substitute(DocumentStoreAddress=document_store_address)
        document_v2 = json.loads(document_v2)
        wrapped_document_v2 = wrap(document_v2, '2.0')

    with open('/document-store-worker/tests/data/document.v3.json', 'rt') as f:
        document_v3 = Template(f.read()).substitute(DocumentStoreAddress=document_store_address)
        document_v3 = json.loads(document_v3)
        wrapped_document_v3 = wrap(document_v3, '3.0')
    worker = Worker(config)
    index = 1
    # checking both schema versions to test auto version definition
    for document in [document_v2, document_v3]:
        key = f'document-{index}'
        unprocessed_bucket.Object(key).put(Body=json.dumps(document))
        worker.poll()
        issued_document = json.load(issued_bucket.Object(key).get()['Body'])
        assert unwrap(issued_document) == document
        index += 1
        time.sleep(queue_test_wait_time_seconds)
    index = 1
    # checking both schema versions to test auto version definition for wrapped documents
    for document in [wrapped_document_v2, wrapped_document_v3]:
        key = f'wrapped-document-{index}'
        unprocessed_bucket.Object(key).put(Body=json.dumps(document))
        worker.poll()
        issued_document = json.load(issued_bucket.Object(key).get()['Body'])
        assert unwrap(issued_document) == unwrap(document)
        index += 1
        time.sleep(queue_test_wait_time_seconds)
    # check that all messages were processed
    assert not unprocessed_queue.receive_messages(
        WaitTimeSeconds=queue_test_wait_time_seconds,
        MaxNumberOfMessages=1,
        VisibilityTimeout=0
    )
