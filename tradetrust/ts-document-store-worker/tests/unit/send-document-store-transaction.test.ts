import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { BigNumber, Wallet, utils } from 'ethers';
// using IssueBatch task because it's a child of SendDocumentStoreTransaction
import { IssueBatch, Batch } from 'src/tasks';

const GAS_PRICE = utils.parseUnits('20', 'gwei');
const GAS = BigNumber.from(100000);
const GAS_PRICE_MULTIPLIER = 1.2;


describe('SendDocumentStoreBatchTransaction task unit tests', ()=>{
  jest.setTimeout(1000 * 60);

  function mulGasPrice(gasPriceWei: BigNumber, gasPriceMultiplier: number){
    const gasPriceEtherMultiplied = parseFloat(utils.formatEther(gasPriceWei)) * gasPriceMultiplier;
    return utils.parseEther(gasPriceEtherMultiplied.toFixed(18));
  }

  let documentStore:any;
  let wallet: any;

  beforeEach(()=>{
    wallet = {
      estimateGas: jest.fn().mockResolvedValue(GAS),
      getGasPrice: jest.fn().mockImplementation(async ()=>utils.parseUnits('20', 'gwei')),
      getTransactionCount: jest.fn().mockResolvedValue(1),
      sendTransaction: jest.fn(),
      provider: {
        waitForTransaction:jest.fn()
      }
    };
    documentStore = {
      populateTransaction: {
        issue: jest.fn().mockImplementation(async ()=>({data: 'transaction data'}))
      }
    };
  })

  test('timeout and hash duplication errors', async ()=>{
    wallet.provider.waitForTransaction.mockReset();
    wallet.provider.waitForTransaction
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockResolvedValueOnce({blockHash:'transaction hash'});
    wallet.sendTransaction.mockReset();
    wallet.sendTransaction
    .mockResolvedValueOnce({hash: '0x0000'})
    .mockResolvedValueOnce({hash: '0x0001'});
    documentStore.populateTransaction.issue.mockReset();
    documentStore.populateTransaction.issue
    .mockResolvedValueOnce({data:'documentIssueData'})
    .mockRejectedValueOnce(new Error('Only hashes that have not been issued can be issued'));

    const batch = new Batch();
    batch.merkleRoot = '0000000000000000000000000000000';
    const issueBatch = new IssueBatch({
      wallet: <Wallet><unknown>wallet,
      documentStore: <DocumentStore><unknown>documentStore,
      batch
    });
    await issueBatch.start();
    // first time transaction times out, second time is successful
    // second attempt to create a new transaction fails because
    // the previous one was added into blockchain
    // therefore a new one is not created and instead task waits
    // for confirmations for the previous one
    expect(wallet.provider.waitForTransaction.mock.calls.length).toBe(2);
    expect(wallet.provider.waitForTransaction.mock.calls[0][0]).toBe('0x0000');
    expect(wallet.provider.waitForTransaction.mock.calls[1][0]).toBe('0x0000');
  });

  test('timeout error', async ()=>{
    wallet.provider.waitForTransaction.mockReset();
    wallet.provider.waitForTransaction
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockResolvedValueOnce({blockHash:'transaction hash'});
    wallet.sendTransaction.mockReset();
    wallet.sendTransaction
    .mockResolvedValueOnce({hash: '0x0000'})
    .mockResolvedValueOnce({hash: '0x0001'});
    documentStore.populateTransaction.issue.mockReset();
    documentStore.populateTransaction.issue
    .mockResolvedValue({data:'documentIssueData'});

    const batch = new Batch();
    batch.merkleRoot = '0000000000000000000000000000000';
    const issueBatch = new IssueBatch({
      wallet: <Wallet><unknown>wallet,
      documentStore: <DocumentStore><unknown>documentStore,
      batch
    });
    await issueBatch.start();
    // first time transaction times out, second time is successful
    expect(wallet.provider.waitForTransaction.mock.calls.length).toBe(2);
    expect(wallet.provider.waitForTransaction.mock.calls[0][0]).toBe('0x0000');
    expect(wallet.provider.waitForTransaction.mock.calls[1][0]).toBe('0x0001');
  });

  test('gas price increase', async ()=>{
    wallet.provider.waitForTransaction.mockReset();
    wallet.provider.waitForTransaction
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockResolvedValueOnce({blockHash:'transaction hash'});
    wallet.sendTransaction.mockReset();
    wallet.sendTransaction
    .mockResolvedValueOnce({hash: '0x0000'})
    .mockResolvedValueOnce({hash: '0x0001'})
    .mockResolvedValueOnce({hash: '0x0002'})
    .mockResolvedValueOnce({hash: '0x0003'});
    const batch = new Batch();
    batch.merkleRoot = '0000000000000000000000000000000';
    const issueBatch = new IssueBatch({
      wallet: <Wallet><unknown>wallet,
      documentStore: <DocumentStore><unknown>documentStore,
      batch,
      gasPriceMultiplier: GAS_PRICE_MULTIPLIER
    });

    await issueBatch.start();
    // only fourth transaction passes, gas price multiplier = 1.2 ^ 3
    expect(wallet.provider.waitForTransaction.mock.calls.length).toBe(4);
    expect(wallet.provider.waitForTransaction.mock.calls[0][0]).toBe('0x0000');
    expect(wallet.provider.waitForTransaction.mock.calls[1][0]).toBe('0x0001');
    expect(wallet.provider.waitForTransaction.mock.calls[2][0]).toBe('0x0002');
    expect(wallet.provider.waitForTransaction.mock.calls[3][0]).toBe('0x0003');
    const gasPrice: BigNumber = wallet.sendTransaction.mock.calls[3][0].gasPrice;
    const expectedGasPrice = mulGasPrice(GAS_PRICE, Math.pow(GAS_PRICE_MULTIPLIER, 3));
    expect(gasPrice.eq(expectedGasPrice)).toBe(true)
  });

  test('gas price limit reached', async ()=>{
    wallet.provider.waitForTransaction.mockReset();
    wallet.provider.waitForTransaction
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockResolvedValueOnce({blockHash:'transaction hash'});
    wallet.sendTransaction.mockReset();
    wallet.sendTransaction
    .mockResolvedValueOnce({hash: '0x0000'})
    .mockResolvedValueOnce({hash: '0x0001'})
    .mockResolvedValueOnce({hash: '0x0002'})
    .mockResolvedValueOnce({hash: '0x0003'});

    const batch = new Batch();
    batch.merkleRoot = '0000000000000000000000000000000';
    const gasPriceMultiplier = 1.3;
    const gasPriceLimit = 40;
    const issueBatch = new IssueBatch({
      wallet: <Wallet><unknown>wallet,
      documentStore: <DocumentStore><unknown>documentStore,
      gasPriceLimitGwei: gasPriceLimit,
      gasPriceMultiplier: gasPriceMultiplier,
      transactionConfirmationThreshold: 10,
      transactionTimeoutSeconds: 180,
      attempts: 10,
      attemptsIntervalSeconds: 60,
      batch,
    });
    await issueBatch.start();

    function compareGasPrices(index: number){
      const expectedGasPrice = mulGasPrice(GAS_PRICE, Math.pow(gasPriceMultiplier, index));
      expect(<BigNumber>wallet.sendTransaction.mock.calls[index][0].gasPrice.eq(expectedGasPrice)).toBe(true);
    }

    expect(wallet.sendTransaction.mock.calls.length).toBe(4);
    expect(wallet.provider.waitForTransaction.mock.calls.length).toBe(4);
    // timeout
    compareGasPrices(0);
    expect(wallet.provider.waitForTransaction.mock.calls[0][0]).toBe('0x0000');
    // timeout
    compareGasPrices(1);
    expect(wallet.provider.waitForTransaction.mock.calls[1][0]).toBe('0x0001');
    // timeout
    compareGasPrices(2);
    expect(wallet.provider.waitForTransaction.mock.calls[2][0]).toBe('0x0002');
    // confirmed transaction, gas price set to max
    expect(<BigNumber>wallet.sendTransaction.mock.calls[3][0].gasPrice.eq(utils.parseUnits(gasPriceLimit.toString(), 'gwei'))).toBe(true);
    expect(wallet.provider.waitForTransaction.mock.calls[3][0]).toBe('0x0003');
  });


  test('gas price limit reached, gas limit is underpaid', async ()=>{
    wallet.provider.waitForTransaction.mockReset();
    wallet.provider.waitForTransaction
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockResolvedValueOnce({blockHash:'transaction hash'});
    wallet.sendTransaction.mockReset();
    wallet.sendTransaction
    .mockResolvedValueOnce({hash: '0x0000'})
    .mockResolvedValueOnce({hash: '0x0001'})
    .mockRejectedValueOnce(new Error('replacement transaction underpriced'))
    .mockResolvedValueOnce({hash: '0x0002'})
    .mockResolvedValueOnce({hash: '0x0003'});
    const batch = new Batch();
    batch.merkleRoot = '0000000000000000000000000000000';
    const gasPriceMultiplier = 1.5;
    const gasPriceLimit = 40;
    const issueBatch = new IssueBatch({
      wallet: <Wallet><unknown>wallet,
      documentStore: <DocumentStore><unknown>documentStore,
      gasPriceLimitGwei: gasPriceLimit,
      gasPriceMultiplier: gasPriceMultiplier,
      transactionConfirmationThreshold: 10,
      transactionTimeoutSeconds: 180,
      attempts: 10,
      attemptsIntervalSeconds: 60,
      batch,
    });
    await issueBatch.start();

    function compareGasPrices(index: number){
      const expectedGasPrice = mulGasPrice(GAS_PRICE, Math.pow(gasPriceMultiplier, index));
      console.log({
        expectedGasPrice: utils.formatUnits(expectedGasPrice, 'gwei'),
        gasPrice: utils.formatUnits(wallet.sendTransaction.mock.calls[index][0].gasPrice, 'gwei')
      })
      expect(<BigNumber>wallet.sendTransaction.mock.calls[index][0].gasPrice.eq(expectedGasPrice)).toBe(true);
    }

    expect(wallet.sendTransaction.mock.calls.length).toBe(3);
    expect(wallet.provider.waitForTransaction.mock.calls.length).toBe(5);
    // timeout
    compareGasPrices(0);
    expect(wallet.provider.waitForTransaction.mock.calls[0][0]).toBe('0x0000');
    // timeout
    compareGasPrices(1);
    expect(wallet.provider.waitForTransaction.mock.calls[1][0]).toBe('0x0001');
    // timeout
    // new transaction is not created, because max possible gas price raise UnderpricedTransactionError
    expect(wallet.provider.waitForTransaction.mock.calls[2][0]).toBe('0x0001');
    // timeout
    // new transaction is not created, because max possible gas price raise UnderpricedTransactionError
    expect(wallet.provider.waitForTransaction.mock.calls[3][0]).toBe('0x0001');
    // transaction confirmed
    // new transaction is not created, because max possible gas price raise UnderpricedTransactionError
    expect(wallet.provider.waitForTransaction.mock.calls[4][0]).toBe('0x0001');
  });


  test('max attempts reached', async ()=>{
    wallet.provider.waitForTransaction.mockReset();
    wallet.provider.waitForTransaction
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockResolvedValueOnce({blockHash:'transaction hash'});

    wallet.sendTransaction.mockReset();
    wallet.sendTransaction.mockRejectedValue(new Error('Totally unexpected error'));

    const batch = new Batch();
    batch.merkleRoot = '0000000000000000000000000000000';
    const gasPriceMultiplier = 1.3;
    const gasPriceLimit = 40;
    const attempts = 10;
    const attemptsIntervalSeconds = 1;
    const issueBatch = new IssueBatch({
      wallet: <Wallet><unknown>wallet,
      documentStore: <DocumentStore><unknown>documentStore,
      gasPriceLimitGwei: gasPriceLimit,
      gasPriceMultiplier: gasPriceMultiplier,
      transactionConfirmationThreshold: 10,
      transactionTimeoutSeconds: 180,
      attempts: attempts,
      attemptsIntervalSeconds: attemptsIntervalSeconds,
      batch,
    });
    try{
      await issueBatch.start();
    }catch(e){
      expect(e.message).toBe('Totally unexpected error');
    }
    expect(wallet.sendTransaction.mock.calls.length).toBe(attempts);
    expect(wallet.provider.waitForTransaction.mock.calls.length).toBe(0);
  });

  test('state restoration after a failed attempt', async ()=>{
    wallet.provider.waitForTransaction.mockReset();
    wallet.provider.waitForTransaction
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockRejectedValueOnce(new Error('timeout exceeded'))
    .mockResolvedValueOnce({blockHash:'transaction hash'})
    wallet.sendTransaction.mockReset();
    wallet.sendTransaction
    .mockResolvedValueOnce({hash: '0x0000'})
    .mockResolvedValueOnce({hash: '0x0001'})
    .mockRejectedValueOnce(new Error('Totally unexpected error'))
    .mockResolvedValueOnce({hash: '0x0002'})

    const batch = new Batch();
    batch.merkleRoot = '0000000000000000000000000000000';
    const gasPriceMultiplier = 1.3;
    const gasPriceLimit = 40;
    const attempts = 10;
    const attemptsIntervalSeconds = 1;
    const issueBatch = new IssueBatch({
      wallet: <Wallet><unknown>wallet,
      documentStore: <DocumentStore><unknown>documentStore,
      gasPriceLimitGwei: gasPriceLimit,
      gasPriceMultiplier: gasPriceMultiplier,
      transactionConfirmationThreshold: 10,
      transactionTimeoutSeconds: 180,
      attempts: attempts,
      attemptsIntervalSeconds: attemptsIntervalSeconds,
      batch,
    });
    await issueBatch.start();
    expect(wallet.sendTransaction.mock.calls.length).toBe(4);
    expect(wallet.provider.waitForTransaction.mock.calls.length).toBe(3);
    // state is restored from the failed
    let expectedGasPrice = mulGasPrice(GAS_PRICE, Math.pow(gasPriceMultiplier, 2));
    expect(<BigNumber>wallet.sendTransaction.mock.calls[2][0].gasPrice.eq(expectedGasPrice)).toBe(true);
    expect(<BigNumber>wallet.sendTransaction.mock.calls[3][0].gasPrice.eq(expectedGasPrice)).toBe(true);
  });

});
