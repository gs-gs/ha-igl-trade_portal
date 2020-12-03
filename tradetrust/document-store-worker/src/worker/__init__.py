import json
import time
import urllib
import boto3
import requests
from web3 import Web3
from web3.gas_strategies.time_based import fast_gas_price_strategy, medium_gas_price_strategy

from src.loggers import logging

logger = logging.getLogger('WORKER')


OPEN_ATTESTATION_VERSION_ID_V2_FRAMEWORK = 'https://schema.openattestation.com/2.0/schema.json'
OPEN_ATTESTATION_VERSION_ID_V3_FRAMEWORK = 'https://schema.openattestation.com/3.0/schema.json'
OPEN_ATTESTATION_VERSION_ID_V2_SHORT = 'open-attestation/2.0'
OPEN_ATTESTATION_VERSION_ID_V3_SHORT = 'open-attestation/3.0'

DOCUMENT_STORE_PROOF_TYPE = 'DOCUMENT_STORE'


class DocumentError(Exception):
    pass


class Worker:

    def __init__(self, config=None):
        self.config = config
        self.eth_connect()
        self.unprocessed_queue_connect()
        self.unprocessed_bucket_connect()
        self.issued_bucket_connect()
        self.connect_to_contract()

    def eth_connect(self):
        logger.debug('eth_connect')
        self.web3 = Web3(Web3.HTTPProvider(self.config['Blockchain']['Endpoint']))

        logger.info(
            'Worker connected to blockchain node at %s, '
            'networkId:%s '
            'chainId:%s',
            self.config['Blockchain']['Endpoint'],
            self.web3.net.version,
            self.web3.eth.chainId
        )

        if self.config['Blockchain']['GasPrice'] is not None:
            if not self.config['Blockchain']['GasPrice'].isnumeric():
                gas_price_strategy = None
                if self.config['Blockchain']['GasPrice'] == 'fast':
                    gas_price_strategy = fast_gas_price_strategy

                if self.config['Blockchain']['GasPrice'] == 'medium':
                    gas_price_strategy = medium_gas_price_strategy

                if gas_price_strategy is None:
                    raise Exception("invalid gas price strategy")

                self.web3.eth.setGasPriceStrategy(gas_price_strategy)
                self.config['Blockchain']['GasPrice'] = self.web3.eth.generateGasPrice()

            else:
                self.config['Blockchain']['GasPrice'] = int(self.config['Blockchain']['GasPrice'])

            logger.info('Setting GasPrice price: %s wei', self.config['Blockchain']['GasPrice'])

    def unprocessed_queue_connect(self):
        logger.debug('unprocessed_queue_connect')
        config = self.config['AWS']['Config']
        queue_url = self.config['AWS']['Resources']['Queues']['Unprocessed']
        self.unprocessed_queue = boto3.resource('sqs', **config).Queue(queue_url)

    def _connect_to_bucket(self, bucket_name):
        config = self.config['AWS']['Config']
        return boto3.resource('s3', **config).Bucket(bucket_name)

    def unprocessed_bucket_connect(self):
        logger.debug('unprocessed_bucket_connect')
        self.unprocessed_bucket = self._connect_to_bucket(self.config['AWS']['Resources']['Buckets']['Unprocessed'])

    def issued_bucket_connect(self):
        logger.debug('issued_bucket_connect')
        self.issued_bucket = self._connect_to_bucket(self.config['AWS']['Resources']['Buckets']['Issued'])

    def connect_to_contract(self):
        logger.debug('connect_to_contract')
        self.document_store = self.web3.eth.contract(
            self.config['DocumentStore']['Address'],
            abi=self.config['DocumentStore']['ABI']
        )

    # this operation also validates document schema
    def wrap_document(self, document, version):
        if not isinstance(document, dict):
            raise Exception("a dict must be passed to the wrap_document")
        is_wrapped = (
            "data" in document
            and "signature" in document
        )
        if is_wrapped:
            raise Exception("The document is already wrapped")
        logger.debug('wrap_document')
        url = urllib.parse.urljoin(
            self.config['OpenAttestation']['Endpoint'], 'document/wrap'
        )
        payload = {
            'document': document,
            'params': {
                'version': version
            }
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            raise DocumentError(response.text)
        else:
            raise RuntimeError(response.text)

    def unwrap_document(self, document, version):
        logger.debug('unwrap_document')
        if not isinstance(document, dict):
            raise Exception("a dict must be passed to the unwrap_document")
        is_wrapped = (
            "data" in document
            and "signature" in document
        )
        if not is_wrapped:
            raise Exception("The document must be wrapped to unwrap it")
        url = urllib.parse.urljoin(
            self.config['OpenAttestation']['Endpoint'], 'document/unwrap'
        )
        payload = {
            'document': document,
            'params': {
                'version': version
            }
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            raise DocumentError(response.text)
        else:
            raise RuntimeError(response.text)

    def _create_issue_document_transaction(self, wrapped_document):
        logger.debug('create_issue_document_transaction')
        public_key = self.config['DocumentStore']['Owner']['PublicKey']
        private_key = self.config['DocumentStore']['Owner']['PrivateKey']
        nonce = self.web3.eth.getTransactionCount(public_key, 'pending')
        transaction = {
            'from': public_key,
            'nonce': nonce
        }

        if self.config['Blockchain']['GasPrice'] is not None:
            transaction['gasPrice'] = self.config['Blockchain']['GasPrice']

        merkleRoot = wrapped_document['signature']['merkleRoot']
        unsigned_transaction = self.document_store.functions.issue(merkleRoot).buildTransaction(transaction)
        signed_transaction = self.web3.eth.account.sign_transaction(unsigned_transaction, private_key=private_key)
        tx_hash = self.web3.eth.sendRawTransaction(signed_transaction.rawTransaction)
        logger.info('[%s] documentStore.issue(%s) %s', Web3.toHex(tx_hash), merkleRoot, unsigned_transaction)
        return tx_hash

    def _wait_for_transaction_receipt(self, tx_hash):
        logger.debug('wait_for_transaction_receipt')
        return self.web3.eth.waitForTransactionReceipt(tx_hash, self.config['Blockchain']['ReceiptTimeout'])

    def issue_document(self, wrapped_document):
        logger.debug('issue_document')
        tx_hash = self._create_issue_document_transaction(wrapped_document)
        receipt = self._wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            raise RuntimeError(json.dumps(Web3.toJSON(receipt)))

    def load_unprocessed_document(self, event):
        logger.info("Loading unprocessed document %s...", event['s3']['object']['key'])
        key = event['s3']['object']['key']
        document = json.load(self.unprocessed_bucket.Object(key).get()['Body'])
        return key, document

    def get_document_version(self, document):
        logger.debug('get_document_version')
        try:
            version = document['version']
            if version not in [
                OPEN_ATTESTATION_VERSION_ID_V2_FRAMEWORK,
                OPEN_ATTESTATION_VERSION_ID_V3_FRAMEWORK,
                OPEN_ATTESTATION_VERSION_ID_V2_SHORT,
                OPEN_ATTESTATION_VERSION_ID_V3_SHORT
            ]:
                raise DocumentError(f'Unknown version id value "{version}"')
            if version == OPEN_ATTESTATION_VERSION_ID_V2_SHORT:
                return OPEN_ATTESTATION_VERSION_ID_V2_FRAMEWORK
            if version == OPEN_ATTESTATION_VERSION_ID_V3_SHORT:
                return OPEN_ATTESTATION_VERSION_ID_V3_FRAMEWORK
            return version
        except KeyError as e:
            raise DocumentError('Document missing "version" field') from e

    def verify_document_store_address(self, document, version):
        logger.debug('verify_document_store_address')
        v2 = OPEN_ATTESTATION_VERSION_ID_V2_FRAMEWORK
        v3 = OPEN_ATTESTATION_VERSION_ID_V3_FRAMEWORK
        if version == v2:
            issuers = document['issuers']
            if len(issuers) > 1:
                raise DocumentError(f'Document of version "{v2}" with multiple issuers currently is not supported')
            try:
                document_store_address = issuers[0]['documentStore']
            except KeyError as e:
                raise DocumentError('Document store address not found in "issuers[0].documentStore"') from e
        elif version == v3:
            version = OPEN_ATTESTATION_VERSION_ID_V3_FRAMEWORK
            proof = document['proof']
            proof_method = proof['method']
            if proof_method != DOCUMENT_STORE_PROOF_TYPE:
                raise DocumentError(
                    f'Document of version "{v3}" '
                    f'has unsupported "proof.method"="{proof_method}".'
                    f'Expected "{DOCUMENT_STORE_PROOF_TYPE}"'
                )
            document_store_address = proof['value']
        if self.config['DocumentStore']['Address'] != document_store_address:
            raise DocumentError(
                f"Document's store address {document_store_address} "
                f"is not equal to {self.config['DocumentStore']['Address']}"
            )

    def put_document(self, key, wrapped_document):
        logger.debug('put_document')
        body = json.dumps(wrapped_document).encode('utf-8')
        content_length = len(body)
        self.issued_bucket.Object(key).put(
            Body=body,
            ContentLength=content_length
        )

    def process_message(self, message):
        logger.debug('process_message')
        event = json.loads(message.body)
        for record in event['Records']:
            try:
                key, document = self.load_unprocessed_document(record)
                version = self.get_document_version(document)

                is_wrapped = (
                    "data" in document
                    and "signature" in document
                )

                if not is_wrapped:
                    logger.info("Document is not wrapped, wrapping it...")
                    wrapped_document = self.wrap_document(document, version)
                else:
                    logger.info("Document is wrapped, unwrapping it to access business data...")
                    wrapped_document = document.copy()
                    document = self.unwrap_document(document, version)
                self.verify_document_store_address(document, version)
                self.issue_document(wrapped_document)
                self.put_document(key, wrapped_document)
                return True
            except DocumentError as e:
                logger.exception(e)
                return True
            except Exception as e:
                logger.exception(e)
                return False

    def _receive_messages(self):
        # logger.debug('receive_messages')
        return self.unprocessed_queue.receive_messages(
            WaitTimeSeconds=self.config['Worker']['Polling']['WaitTimeSeconds'],
            MaxNumberOfMessages=self.config['Worker']['Polling']['MaxNumberOfMessages'],
            VisibilityTimeout=self.config['Worker']['Polling']['VisibilityTimeout']
        )

    def poll(self):
        # logger.debug('poll')
        for message in self._receive_messages():
            if self.process_message(message):
                logger.debug('message.delete')
                message.delete()
                logger.info("Message has been processed sucessfully")

    def start(self):  # pragma: no cover
        polling_interval = self.config['Worker']['Polling']['IntervalSeconds']
        logger.info("Starting the worker with polling_interval %s", polling_interval)


        while True:
            self.poll()
            time.sleep(polling_interval)
