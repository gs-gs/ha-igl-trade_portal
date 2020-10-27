import os
import json
import tempfile
from unittest import mock
import pytest
from src.config import Config
from src.worker import Worker
from src.worker import DocumentError


def test_get_document_version():
    config = Config.from_environ()
    worker = Worker(config)

    document = {}
    with pytest.raises(DocumentError) as einfo:
        worker.get_document_version(document)
    assert str(einfo.value) == 'Document missing "version" field'
    document = {
        'version': 'badversionid'
    }
    with pytest.raises(DocumentError) as einfo:
        worker.get_document_version(document)
    assert str(einfo.value) == 'Unknown version id value "badversionid"'
    version = 'https://schema.openattestation.com/2.0/schema.json'
    document = {
        'version': version
    }
    assert worker.get_document_version(document) == version
    version = 'open-attestation/2.0'
    document = {
        'version': version
    }
    assert worker.get_document_version(document) == 'https://schema.openattestation.com/2.0/schema.json'
    version = 'https://schema.openattestation.com/3.0/schema.json'
    document = {
        'version': version
    }
    assert worker.get_document_version(document) == version
    version = 'open-attestation/3.0'
    document = {
        'version': version
    }
    assert worker.get_document_version(document) == 'https://schema.openattestation.com/3.0/schema.json'


def test_verify_document_store_address():
    config = Config.from_environ()
    worker = Worker(config)

    document_store_address = config['DocumentStore']['Address']
    version = 'https://schema.openattestation.com/2.0/schema.json'
    document = {
        'issuers': [
            {},
            {}
        ]
    }
    with pytest.raises(DocumentError) as einfo:
        worker.verify_document_store_address(document, version)
    assert str(einfo.value) == f'Document of version "{version}" with multiple issuers currently is not supported'
    document = {
        'issuers': [
            {}
        ]
    }
    with pytest.raises(DocumentError) as einfo:
        worker.verify_document_store_address(document, version)
    assert str(einfo.value) == 'Document store address not found in "issuers[0].documentStore"'
    document = {
        'issuers': [
            {
                'documentStore': 'baddocumentstoreaddress'
            }
        ]
    }
    expected = (
        f"Document's store address {document['issuers'][0]['documentStore']}"
        + f" is not equal to {config['DocumentStore']['Address']}"
    )
    with pytest.raises(DocumentError) as einfo:
        worker.verify_document_store_address(document, version)
    assert str(einfo.value) == expected
    document = {
        'issuers': [
            {
                'documentStore': document_store_address
            }
        ]
    }
    worker.verify_document_store_address(document, version)
    version = 'https://schema.openattestation.com/3.0/schema.json'

    document = {
        'proof': {
            'method': 'TOKEN_REGISTRY'
        }
    }
    with pytest.raises(DocumentError) as einfo:
        worker.verify_document_store_address(document, version)
    assert str(einfo.value) == (
        f'Document of version "{version}" '
        f'has unsupported "proof.method"="TOKEN_REGISTRY".'
        f'Expected "DOCUMENT_STORE"'
    )
    document = {
        'proof': {
            'method': 'DOCUMENT_STORE',
            'value': 'baddocumentstoreaddress'
        }
    }
    with pytest.raises(DocumentError) as einfo:
        worker.verify_document_store_address(document, version)
    with pytest.raises(DocumentError) as einfo:
        worker.verify_document_store_address(document, version)
    expected = (
        f"Document's store address {document['proof']['value']}"
        + f" is not equal to {config['DocumentStore']['Address']}"
    )
    assert str(einfo.value) == expected
    document = {
        'proof': {
            'method': 'DOCUMENT_STORE',
            'value': document_store_address
        }
    }
    worker.verify_document_store_address(document, version)


@mock.patch('src.worker.requests')
def test_validate_document_schema(requests):
    config = Config.from_environ()
    worker = Worker(config)

    document = {}
    version = 'documentversion'

    response = mock.MagicMock()
    requests.post.return_value = response

    response.status_code = 200
    response.text = 'Error text'
    response.json.return_value = {'msg': 'Wrapped document'}
    wrapped_document = worker.wrap_document(document, version)
    assert wrapped_document == response.json.return_value
    response.json.assert_called_once()
    requests.post.assert_called_once()
    requests.reset_mock()

    response.status_code = 400
    response.text = 'Error text'
    with pytest.raises(DocumentError) as einfo:
        worker.wrap_document(document, version)
    assert str(einfo.value) == response.text
    requests.post.assert_called_once()
    requests.reset_mock()

    response.status_code = 500
    response.text = 'Internal server error'
    with pytest.raises(RuntimeError) as einfo:
        worker.wrap_document(document, version)
    assert str(einfo.value) == response.text
    requests.post.assert_called_once()
    requests.reset_mock()


@mock.patch('src.worker.Web3.toJSON')
@mock.patch('src.worker.Worker._create_issue_document_transaction')
@mock.patch('src.worker.Worker._wait_for_transaction_receipt')
def test_issue_document_transaction_error(_wait_for_transaction_receipt, _create_issue_document_transaction, toJSON):
    config = Config.from_environ()
    worker = Worker(config)
    wrapped_document = {}

    tx_hash = 'hash'
    receipt = mock.MagicMock
    receipt.status = 0
    toJSON.return_value = {'receipt': {'id': 1}}
    _create_issue_document_transaction.return_value = tx_hash
    _wait_for_transaction_receipt.return_value = receipt
    with pytest.raises(RuntimeError) as einfo:
        worker.issue_document(wrapped_document)
    assert str(einfo.value) == json.dumps(toJSON.return_value)
    _create_issue_document_transaction.assert_called_once_with(wrapped_document)
    _wait_for_transaction_receipt.assert_called_once_with(tx_hash)
    toJSON.assert_called_once_with(receipt)


@mock.patch('src.worker.Worker.load_unprocessed_document')
@mock.patch('src.worker.Worker.get_document_version')
@mock.patch('src.worker.Worker.wrap_document')
@mock.patch('src.worker.Worker.verify_document_store_address')
@mock.patch('src.worker.Worker.issue_document')
@mock.patch('src.worker.Worker.put_document')
def test_process_message_error(
    put_document,
    issue_document,
    verify_document_store_address,
    wrap_document,
    get_document_version,
    load_unprocessed_document
):
    config = Config.from_environ()
    worker = Worker(config)

    message = mock.MagicMock()
    message.body = {
        'Records': [
            {}
        ]
    }
    message.body = json.dumps(message.body)
    document = mock.MagicMock()
    key = mock.MagicMock()
    load_unprocessed_document.return_value = (key, document)

    wrap_document.side_effect = DocumentError('Mock Expected')

    assert worker.process_message(message)

    load_unprocessed_document.assert_called_once()
    get_document_version.assert_called_once()
    wrap_document.assert_called_once()
    verify_document_store_address.assert_not_called()
    issue_document.assert_not_called()
    put_document.assert_not_called()

    load_unprocessed_document.reset_mock()
    get_document_version.reset_mock()
    wrap_document.reset_mock()
    verify_document_store_address.reset_mock()
    issue_document.reset_mock()
    put_document.reset_mock()

    wrap_document.side_effect = None
    issue_document.side_effect = RuntimeError('Mock Unexpected')

    assert not worker.process_message(message)


def test_config_error():
    with mock.patch.dict(os.environ, {'WORKER_POLLING_VISIBILITY_TIMEOUT': '0'}):
        with pytest.raises(ValueError) as einfo:
            Config.from_environ()
        assert str(einfo.value) == 'WORKER_POLLING_VISIBILITY_TIMEOUT must be >= 60'


def test_config_load_file_values():
    tmp_dir = tempfile.mkdtemp()
    filename = os.path.join(tmp_dir, 'singleline_file_value_test')

    def update_file(value):
        with open(filename, 'wt+') as f:
            f.write(value)

    value = 'hello world'
    update_file(value)
    assert Config.load_singleline_file_value(filename) == value

    value = 'hello world\n'
    update_file(value)
    assert Config.load_singleline_file_value(filename) == 'hello world'

    value = ''
    update_file(value)
    assert Config.load_singleline_file_value(filename, not_empty=False) == ''

    value = '\n'
    update_file(value)
    assert Config.load_singleline_file_value(filename, not_empty=False) == ''

    value = 'hello world\n\n'
    update_file(value)
    with pytest.raises(ValueError) as einfo:
        Config.load_singleline_file_value(filename)
    assert str(einfo.value) == f'{filename} must contain only a single line, found more'

    value = ''
    update_file(value)
    with pytest.raises(ValueError) as einfo:
        Config.load_singleline_file_value(filename)
    assert str(einfo.value) == f'{filename} must not be empty'

    value = '\n'
    update_file(value)
    with pytest.raises(ValueError) as einfo:
        Config.load_singleline_file_value(filename)
    assert str(einfo.value) == f'{filename} must not be empty'

    env_name = 'VARIABLE_NAME'
    value = 'test_value'

    with mock.patch.dict(os.environ, {env_name: filename}):
        update_file(value)
        assert Config.get_env_or_singleline_file_value(env_name) == Config.load_singleline_file_value(filename)

    with mock.patch.dict(os.environ, {env_name: value}):
        update_file(value + value)
        assert Config.get_env_or_singleline_file_value(env_name) != Config.load_singleline_file_value(filename)
        assert Config.get_env_or_singleline_file_value(env_name) == value

    with mock.patch.dict(os.environ, {env_name: ''}):
        with pytest.raises(ValueError) as einfo:
            Config.get_env_or_singleline_file_value(env_name, not_empty=True)
        assert str(einfo.value) == f'environment variable "{env_name}" must not be empty'

    value = '{"msg": "Hello world"}'
    update_file(value)
    assert Config.load_json_file(filename) == {'msg': 'Hello world'}
