import os
import urllib
import requests
import boto3
import pytest


AWS_CONFIG = {
    'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
    'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
    'endpoint_url': os.environ['AWS_ENDPOINT_URL'],
    'region_name': os.environ['AWS_DEFAULT_REGION']
}

OPEN_ATTESTATION_ENDPOINT = os.environ['OPEN_ATTESTATION_ENDPOINT']
if os.path.isfile(OPEN_ATTESTATION_ENDPOINT):
    with open(OPEN_ATTESTATION_ENDPOINT, 'rt') as f:
        OPEN_ATTESTATION_ENDPOINT = f.read()


@pytest.fixture('function')
def bucket():
    def fixture(name):
        bucket = boto3.resource('s3', **AWS_CONFIG).Bucket(name)
        bucket.objects.all().delete()
        return bucket
    return fixture


@pytest.fixture('function')
def unprocessed_bucket(bucket):
    return bucket(os.environ['UNPROCESSED_BUCKET_NAME'])


@pytest.fixture('function')
def issued_bucket(bucket):
    return bucket(os.environ['ISSUED_BUCKET_NAME'])


@pytest.fixture('function')
def unprocessed_queue():
    queue = boto3.resource('sqs', **AWS_CONFIG).Queue(os.environ['UNPROCESSED_QUEUE_URL'])
    queue.purge()
    return queue


@pytest.fixture('session')
def unwrap():
    def func(wrapped_document):
        url = urllib.parse.urljoin(OPEN_ATTESTATION_ENDPOINT, 'document/unwrap')
        response = requests.post(url, json={
            'document': wrapped_document
        })
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(response.text)
    yield func


@pytest.fixture('session')
def wrap():
    def func(document, version):
        url = urllib.parse.urljoin(OPEN_ATTESTATION_ENDPOINT, 'document/wrap')
        response = requests.post(url, json={
            'document': document,
            'params': {
                'version': f'https://schema.openattestation.com/{version}/schema.json'
            }
        })
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(response.text)
    yield func
