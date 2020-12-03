import os
import boto3
from web3 import Web3

cloudwatch = boto3.client('cloudwatch', endpoint_url=os.environ.get('AWS_ENDPOINT_URL'))


def account_balance(event, context):
    HTTP_BLOCKCHAIN_ENDPOINT = os.environ['HTTP_BLOCKCHAIN_ENDPOINT']
    DIMENSION_VALUE = ACCOUNT_ADDRESS = os.environ['ACCOUNT_ADDRESS']
    DIMENSION_NAME = 'Address Id'
    METRIC_NAME = 'Balance'
    METRIC_NAMESPACE = 'Ethereum/Wallet'

    web3 = Web3(Web3.HTTPProvider(HTTP_BLOCKCHAIN_ENDPOINT))

    balance = web3.fromWei(web3.eth.getBalance(ACCOUNT_ADDRESS), 'ether')

    cloudwatch.put_metric_data(
        Namespace=METRIC_NAMESPACE,
        MetricData=[
            {
                'MetricName': METRIC_NAME,
                'Dimensions': [
                    {
                        'Name': DIMENSION_NAME,
                        'Value': DIMENSION_VALUE
                    }
                ],
                'Value': balance
            }
        ]
    )
    return {'Balance': float(balance)}


def account_pending_transactions(event, context):
    HTTP_BLOCKCHAIN_ENDPOINT = os.environ['HTTP_BLOCKCHAIN_ENDPOINT']
    DIMENSION_VALUE = ACCOUNT_ADDRESS = os.environ['ACCOUNT_ADDRESS']
    DIMENSION_NAME = 'Address Id'
    METRIC_NAME = 'PendingTransactions'
    METRIC_NAMESPACE = 'Ethereum/Wallet'

    web3 = Web3(Web3.HTTPProvider(HTTP_BLOCKCHAIN_ENDPOINT))
    confirmed_transactions = web3.eth.getTransactionCount(ACCOUNT_ADDRESS, block_identifier='latest')
    all_transactions = web3.eth.getTransactionCount(ACCOUNT_ADDRESS, block_identifier='pending')
    pending_transactions = all_transactions - confirmed_transactions

    cloudwatch.put_metric_data(
        Namespace=METRIC_NAMESPACE,
        MetricData=[
            {
                'MetricName': METRIC_NAME,
                'Dimensions': [
                    {
                        'Name': DIMENSION_NAME,
                        'Value': DIMENSION_VALUE
                    }
                ],
                'Value': pending_transactions
            }
        ]
    )
    return {'PendingTransactions': pending_transactions}


def ethereum_node_chain_id(event, context):
    DIMENSION_VALUE = HTTP_BLOCKCHAIN_ENDPOINT = os.environ['HTTP_BLOCKCHAIN_ENDPOINT']
    DIMENSION_NAME = 'Api Endpoint Hostname'
    METRIC_NAME = 'ChainId'
    METRIC_NAMESPACE = 'Ethereum/Node'

    web3 = Web3(Web3.HTTPProvider(HTTP_BLOCKCHAIN_ENDPOINT))

    chain_id = web3.eth.chainId

    cloudwatch.put_metric_data(
        Namespace=METRIC_NAMESPACE,
        MetricData=[
            {
                'MetricName': METRIC_NAME,
                'Dimensions': [
                    {
                        'Name': DIMENSION_NAME,
                        'Value': DIMENSION_VALUE
                    }
                ],
                'Value': chain_id
            }
        ]
    )
    return {'ChainId': chain_id}


def ethereum_node_network_id(event, context):
    DIMENSION_VALUE = HTTP_BLOCKCHAIN_ENDPOINT = os.environ['HTTP_BLOCKCHAIN_ENDPOINT']
    DIMENSION_NAME = 'Api Endpoint Hostname'
    METRIC_NAME = 'NetworkId'
    METRIC_NAMESPACE = 'Ethereum/Node'

    web3 = Web3(Web3.HTTPProvider(HTTP_BLOCKCHAIN_ENDPOINT))

    network_id = int(web3.net.version)

    cloudwatch.put_metric_data(
        Namespace=METRIC_NAMESPACE,
        MetricData=[
            {
                'MetricName': METRIC_NAME,
                'Dimensions': [
                    {
                        'Name': DIMENSION_NAME,
                        'Value': DIMENSION_VALUE
                    }
                ],
                'Value': network_id
            }
        ]
    )
    return {'NetworkId': network_id}
