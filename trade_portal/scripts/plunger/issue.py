import sys
import os
import json
from web3 import Web3
from web3.gas_strategies.time_based import fast_gas_price_strategy


def main(argv):
    public_key = os.getenv('PUBLIC_KEY')
    private_key = os.getenv('PRIVATE_KEY')
    contract_address = os.getenv('CONTRACT_ADDRESS')
    ethereum_node_url = os.getenv('ETHEREUM_NODE_URL')

    merkle_root = argv[0]

    with open('DocumentStore.json', 'rt') as f:
        contract_abi = json.load(f)['abi']

    web3 = Web3(Web3.HTTPProvider(ethereum_node_url))
    web3.eth.setGasPriceStrategy(fast_gas_price_strategy)

    nonce = web3.eth.getTransactionCount(public_key)

    document_store = web3.eth.contract(
        contract_address,
        abi=contract_abi
    )

    transaction = {
        'from': public_key,
        'nonce': nonce,
        'gasPrice': web3.eth.generateGasPrice()
    }

    unsigned_transaction = document_store.functions.issue(
        merkle_root).buildTransaction(transaction)
    signed_transaction = web3.eth.account.sign_transaction(
        unsigned_transaction, private_key=private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_transaction.rawTransaction)
    print('[%s] documentStore.issue(%s) %s', Web3.toHex(
        tx_hash), merkle_root, unsigned_transaction)


if __name__ == "__main__":
    main(sys.argv[1:])
