import json
from unittest import mock
import pytest
from web3.exceptions import TimeExhausted
from src.config import Config
from src.worker import Worker
from src.worker import fast_gas_price_strategy, medium_gas_price_strategy
from tests.data import DOCUMENT_V2_TEMPLATE


def connect_resources(self):
    self.web3 = mock.MagicMock()
    self.unprocessed_queue = mock.MagicMock()
    self.unprocessed_bucket = mock.MagicMock()
    self.issued_bucket = mock.MagicMock()
    self.document_store = mock.MagicMock()


@mock.patch('src.worker.Worker.connect_resources', connect_resources)
def test_initialization():
    config = Config.from_environ()
    config['Blockchain']['GasPrice'] = 'fast'

    worker = Worker(config)
    worker.web3.eth.setGasPriceStrategy.assert_called_once_with(fast_gas_price_strategy)
    assert worker.dynamic_gas_price_strategy
    assert worker.gas_price == worker.web3.eth.generateGasPrice()

    config['Blockchain']['GasPrice'] = 'medium'
    worker = Worker(config)
    worker.web3.eth.setGasPriceStrategy.assert_called_once_with(medium_gas_price_strategy)
    assert worker.dynamic_gas_price_strategy
    assert worker.gas_price == worker.web3.eth.generateGasPrice()

    config['Blockchain']['GasPrice'] = 6000000
    worker = Worker(config)
    assert not worker.dynamic_gas_price_strategy
    assert worker.gas_price == config['Blockchain']['GasPrice']
    worker.web3.eth.setGasPriceStrategy.assert_not_called()

    config['Blockchain']['GasPrice'] = 'slow'
    with pytest.raises(Exception) as einfo:
        worker = Worker(config)
    assert str(einfo.value) == 'Invalid gas price strategy:\'slow\''

    config['Blockchain']['GasPrice'] = None
    with pytest.raises(Exception) as einfo:
        worker = Worker(config)
    assert str(einfo.value) == 'Invalid gas price strategy:None'


@mock.patch('src.worker.Worker.connect_resources', connect_resources)
@mock.patch('src.worker.Worker.generate_gas_price')
@mock.patch('src.worker.Worker.load_unprocessed_document')
def test_gas_price_update(load_unprocessed_document, generate_gas_price):

    gas_price = 111
    generate_gas_price.return_value = gas_price

    config = Config.from_environ()
    config['Blockchain']['GasPrice'] = 'fast'
    config['Blockchain']['GasPriceRefreshRate'] = 2

    key = 'document-key'
    document = DOCUMENT_V2_TEMPLATE.substitute(DocumentStoreAddress=config['DocumentStore']['Address'])
    document = json.loads(document)
    load_unprocessed_document.return_value = key, document

    message = mock.Mock()
    message.body = json.dumps({'Records': [{}]})

    worker = Worker(config)

    worker.web3.eth.sendRawTransaction.return_value = b'transaction-hash'
    worker.web3.eth.waitForTransactionReceipt().status = 1
    assert worker.gas_price == gas_price

    # testing transaction timeout causing gas price increase
    generate_gas_price.reset_mock()
    worker.web3.eth.waitForTransactionReceipt.side_effect = TimeExhausted
    assert not worker.process_message(message)
    generate_gas_price.assert_not_called()
    assert worker.gas_price == int(gas_price * 1.1)

    # testing gas price refresh
    generate_gas_price.reset_mock()
    worker.web3.eth.waitForTransactionReceipt.side_effect = None
    for i in range(config['Blockchain']['GasPriceRefreshRate']):
        assert worker.process_message(message)
    generate_gas_price.assert_called_once()

    # testing no refresh on static gas price
    config['Blockchain']['GasPrice'] = 20
    worker = Worker(config)

    worker.web3.eth.sendRawTransaction.return_value = b'transaction-hash'
    worker.web3.eth.waitForTransactionReceipt().status = 1

    worker.web3.reset_mock()
    for i in range(config['Blockchain']['GasPriceRefreshRate']):
        assert worker.process_message(message)
    worker.web3.eth.generateGasPrice.assert_not_called()
