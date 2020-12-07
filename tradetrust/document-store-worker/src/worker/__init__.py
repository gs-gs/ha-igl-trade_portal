import json
import time
import urllib
import boto3
import requests
from web3 import Web3
from web3.exceptions import TimeExhausted
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


class TransactionTimeoutException(Exception):
    pass


class Worker:

    def __init__(self, config=None):
        self.config = config

        self.connect_resources()

        self.set_gas_price_strategy()
        self.update_gas_price()

    def connect_resources(self):
        self.connect_blockchain_node()
        self.connect_unprocessed_queue()
        self.connect_unprocessed_bucket()
        self.connect_issued_bucket()
        self.connect_contract()

    def connect_blockchain_node(self):
        logger.debug('connect_blockchain_node')
        self.web3 = Web3(Web3.HTTPProvider(self.config['Blockchain']['Endpoint']))

        logger.info(
            'Worker connected to blockchain node at %s, '
            'networkId:%s '
            'chainId:%s',
            self.config['Blockchain']['Endpoint'],
            self.web3.net.version,
            self.web3.eth.chainId
        )

    def set_gas_price_strategy(self):
        logger.debug('set_gas_price_strategy')
        gas_price_config = self.config['Blockchain']['GasPrice']

        self.dynamic_gas_price_strategy = False

        # static gas price strategy
        try:
            self.gas_price = int(gas_price_config)
            logger.info('gas price strategy=static, price=%s', self.gas_price)
            return
        except (ValueError, TypeError):
            pass

        # fast time based strategy, 60 sec per transaction
        if gas_price_config == 'fast':
            self.dynamic_gas_price_strategy = True
            self.web3.eth.setGasPriceStrategy(fast_gas_price_strategy)
            logger.info('gas price strategy=fast(60sec), price=dynamic')
        # medium time based strategy, 5 min per transaction
        elif gas_price_config == 'medium':
            self.dynamic_gas_price_strategy = True
            self.web3.eth.setGasPriceStrategy(medium_gas_price_strategy)
            logger.info('gas price strategy=medium(5min), price=dynamic')
        else:
            raise Exception(f'Invalid gas price strategy:{repr(gas_price_config)}')
        return gas_price_config

    def update_gas_price(self):
        logger.debug('update_gas_price')
        # update gas price only if gas price strategy is set
        if self.dynamic_gas_price_strategy:
            self.gas_price = self.web3.eth.generateGasPrice()
        self.transactions_count = 1
        logger.info('gas price=%s', 'default' if self.gas_price is None else self.gas_price)
        logger.debug('transactions count reset')

    def refresh_gas_price(self):
        logger.debug('refresh_gas_price')
        if self.transactions_count % self.config['Blockchain']['GasPriceRefreshRate'] == 0:
            self.update_gas_price()
            logger.debug('gas price refreshed')

    def connect_unprocessed_queue(self):
        logger.debug('connect_unprocessed_queue')
        config = self.config['AWS']['Config']
        queue_url = self.config['AWS']['Resources']['Queues']['Unprocessed']
        self.unprocessed_queue = boto3.resource('sqs', **config).Queue(queue_url)

    def _connect_to_bucket(self, bucket_name):
        config = self.config['AWS']['Config']
        return boto3.resource('s3', **config).Bucket(bucket_name)

    def connect_unprocessed_bucket(self):
        logger.debug('connect_unprocessed_bucket')
        self.unprocessed_bucket = self._connect_to_bucket(self.config['AWS']['Resources']['Buckets']['Unprocessed'])

    def connect_issued_bucket(self):
        logger.debug('connect_issued_bucket')
        self.issued_bucket = self._connect_to_bucket(self.config['AWS']['Resources']['Buckets']['Issued'])

    def connect_contract(self):
        logger.debug('connect_contract')
        self.document_store = self.web3.eth.contract(
            self.config['DocumentStore']['Address'],
            abi=self.config['DocumentStore']['ABI']
        )

    # this operation also validates document schema
    def wrap_document(self, document, version):
        if not isinstance(document, dict):
            raise Exception("a dict must be passed to the wrap_document")
        is_wrapped = "data" in document and "signature" in document
        if is_wrapped:
            raise Exception("The document is already wrapped")
        logger.debug('wrap_document')
        url = urllib.parse.urljoin(self.config['OpenAttestation']['Endpoint'], 'document/wrap')
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

    def verify_document_signature(self, wrapped_document):
        logger.debug('verify_document_signature')
        if not isinstance(wrapped_document, dict):
            raise Exception("a dict must be passed to verify signature")
        is_wrapped = "data" in wrapped_document and "signature" in wrapped_document
        if not is_wrapped:
            raise Exception("The document is not wrapped")
        url = urllib.parse.urljoin(self.config['OpenAttestation']['Endpoint'], 'document/verify/signature')
        payload = {
            'document': wrapped_document,
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            if not response.json()['valid']:
                raise DocumentError('Document signature is invalid')
        elif response.status_code == 400:
            raise DocumentError(response.text)
        else:
            raise RuntimeError(response.text)

    def is_issued_document(self, wrapped_document):
        logger.debug('is_issued_document')
        return self.document_store.functions.isIssued(wrapped_document['signature']['merkleRoot']).call()

    def create_issue_document_transaction(self, wrapped_document):
        logger.debug('create_issue_document_transaction')
        public_key = self.config['DocumentStore']['Owner']['PublicKey']
        private_key = self.config['DocumentStore']['Owner']['PrivateKey']
        # excluding pending transactions to not cause transactions replication
        # this way duplicate transactions will just cancel each other
        nonce = self.web3.eth.getTransactionCount(public_key, 'latest')
        transaction = {
            'from': public_key,
            'nonce': nonce
        }

        transaction['gasPrice'] = self.gas_price
        merkleRoot = wrapped_document['signature']['merkleRoot']
        unsigned_transaction = self.document_store.functions.issue(merkleRoot).buildTransaction(transaction)
        signed_transaction = self.web3.eth.account.sign_transaction(unsigned_transaction, private_key=private_key)
        tx_hash = self.web3.eth.sendRawTransaction(signed_transaction.rawTransaction)
        logger.info('[%s] documentStore.issue(%s) %s', Web3.toHex(tx_hash), merkleRoot, unsigned_transaction)
        return tx_hash

    def wait_for_transaction_receipt(self, tx_hash):
        logger.debug('wait_for_transaction_receipt')
        try:
            return self.web3.eth.waitForTransactionReceipt(tx_hash, self.config['Blockchain']['ReceiptTimeout'])
        except TimeExhausted as e:
            raise TransactionTimeoutException() from e

    def issue_document(self, wrapped_document):
        logger.debug('issue_document')
        tx_hash = self.create_issue_document_transaction(wrapped_document)
        receipt = self.wait_for_transaction_receipt(tx_hash)
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

                is_wrapped = "data" in document and "signature" in document

                if not is_wrapped:
                    logger.info("Document is not wrapped, wrapping it...")
                    wrapped_document = self.wrap_document(document, version)
                else:
                    logger.info("Document is wrapped, unwrapping it to access business data...")
                    wrapped_document = document.copy()
                    document = self.unwrap_document(document, version)
                    self.verify_document_signature(wrapped_document)
                    # This is used to fix potential rare error when a stuck pending transaction
                    # gets mined before a higher-priced one which causes a wrapped document to hang forever
                    # in the unprocessed bucket because it's already issued
                    logger.info("Checking issuance status")
                    if self.is_issued_document(wrapped_document):
                        logger.info("The document already issued, moving to issued bucket")
                        self.verify_document_store_address(document, version)
                        self.put_document(key, wrapped_document)
                        return True
                    logger.info('The document is not issued, continuing normally')
                self.verify_document_store_address(document, version)
                self.refresh_gas_price()
                self.issue_document(wrapped_document)
                self.put_document(key, wrapped_document)
                self.transactions_count += 1
                return True
            except DocumentError as e:
                logger.exception(e)
                return True
            except TransactionTimeoutException:
                # next transaction will replace this one using actual gas price because of the same nonce value
                logger.warn('Transaction timed out, updating gas price.')
                self.update_gas_price()
                return False
            except Exception as e:
                logger.exception(e)
                return False

    def receive_messages(self):
        # logger.debug('receive_messages')
        return self.unprocessed_queue.receive_messages(
            WaitTimeSeconds=self.config['Worker']['Polling']['WaitTimeSeconds'],
            MaxNumberOfMessages=self.config['Worker']['Polling']['MaxNumberOfMessages'],
            VisibilityTimeout=self.config['Worker']['Polling']['VisibilityTimeout']
        )

    def poll(self):
        # logger.debug('poll')
        for message in self.receive_messages():
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
