import os
import json


class Config:

    @staticmethod
    def load_singleline_file_value(filename, not_empty=True):
        with open(filename, 'rt') as f:
            value = None
            for line in f:
                if value is not None:
                    raise ValueError(f'{filename} must contain only a single line, found more')
                value = line
        value = value or ''
        value = value.replace('\n', '')
        if not_empty and len(value) == 0:
            raise ValueError(f'{filename} must not be empty')
        return value

    @staticmethod
    def load_json_file(filename):
        with open(filename, 'rt') as f:
            return json.load(f)

    @staticmethod
    def get_env_or_singleline_file_value(env_name, not_empty=True):
        env_value = os.environ[env_name]
        if os.path.isfile(env_value):
            return Config.load_singleline_file_value(env_value)
        elif env_value:
            return env_value
        else:
            raise ValueError(f'environment variable "{env_name}" must not be empty')

    @staticmethod
    def from_environ():
        # The worker relies on VisibilityTimeout to hide messages while it's processing them.
        worker_polling_visibility_timeout = int(os.environ.get('WORKER_POLLING_VISIBILITY_TIMEOUT', '60'))
        if worker_polling_visibility_timeout < 60:
            raise ValueError('WORKER_POLLING_VISIBILITY_TIMEOUT must be >= 60')
        worker_polling = {
            'IntervalSeconds': int(os.environ['WORKER_POLLING_INTERVAL_SECONDS']),
            'WaitTimeSeconds': int(os.environ['WORKER_POLLING_MESSAGE_WAIT_TIME_SECONDS']),
            'MaxNumberOfMessages': int(os.environ['WORKER_POLLING_MAX_NUMBER_OF_MESSAGES']),
            'VisibilityTimeout': worker_polling_visibility_timeout
        }

        open_attestation = {}
        open_attestation['Endpoint'] = Config.get_env_or_singleline_file_value(
            'OPEN_ATTESTATION_ENDPOINT',
            not_empty=True
        )

        blockchain = {
            'Endpoint': os.environ['BLOCKCHAIN_ENDPOINT']
        }

        document_store = {
            'Address': Config.get_env_or_singleline_file_value(
                'DOCUMENT_STORE_ADDRESS',
                not_empty=True
            ),
            'ABI': Config.load_json_file(os.environ['DOCUMENT_STORE_ABI'])['abi'],
            'Owner': {
                'PublicKey': os.environ['DOCUMENT_STORE_OWNER_PUBLIC_KEY'],
                'PrivateKey': os.environ['DOCUMENT_STORE_OWNER_PRIVATE_KEY']
            }
        }

        aws_config = {}
        if aws_endpoint_url := os.environ.get('AWS_ENDPOINT_URL'):
            aws_config['endpoint_url'] = aws_endpoint_url
        if aws_secret_access_key := os.environ.get('AWS_SECRET_ACCESS_KEY'):
            aws_config['aws_secret_access_key'] = aws_secret_access_key
        if aws_access_key_id := os.environ.get('AWS_ACCESS_KEY_ID'):
            aws_config['aws_access_key_id'] = aws_access_key_id
        if aws_region_name := os.environ.get('AWS_REGION_NAME') or os.environ.get('AWS_DEFAULT_REGION'):
            aws_config['region_name'] = aws_region_name

        queues = {
            'Unprocessed': os.environ['UNPROCESSED_QUEUE_URL']
        }
        buckets = {
            'Unprocessed': os.environ['UNPROCESSED_BUCKET_NAME'],
            'Issued': os.environ['ISSUED_BUCKET_NAME']
        }
        aws_resources = {'Queues': queues, 'Buckets': buckets}

        return {
            'Worker': {
                'Polling': worker_polling
            },
            'AWS': {
                'Config': aws_config,
                'Resources': aws_resources
            },
            'DocumentStore': document_store,
            'Blockchain': blockchain,
            'OpenAttestation': open_attestation
        }
