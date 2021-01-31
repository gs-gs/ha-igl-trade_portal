import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { BigNumber, Wallet, utils } from 'ethers';
import { IssueBatch, Batch } from 'src/tasks';

const GAS_PRICE = BigNumber.from(20000);
const GAS = BigNumber.from(100000);
const GAS_PRICE_MULTIPLIER = 1.2;


describe('IssueBatch tast unit tests', ()=>{
  jest.setTimeout(1000 * 60);

  const documentStore = {
    populateTransaction: {
      issue: jest.fn()
    }
  };

  const wallet = {
    estimateGas: jest.fn().mockReturnValue(new Promise(resolve=>resolve(GAS))),
    getGasPrice: jest.fn().mockReturnValue(new Promise(resolve=>resolve(GAS_PRICE))),
    getTransactionCount: jest.fn().mockReturnValue(new Promise(resolve=>resolve(1))),
    sendTransaction: jest.fn(),
    provider: {
      waitForTransaction:jest.fn()
    }
  };

  test('timeout and hash duplication errors', async ()=>{
    wallet.provider.waitForTransaction.mockReset();
    (
      wallet.provider.waitForTransaction
      .mockReturnValueOnce(new Promise(()=>{throw new Error('timeout exceeded')}))
      .mockReturnValueOnce(new Promise((resolve)=>resolve({blockHash:'transaction hash'})))
    )
    wallet.sendTransaction.mockReset();
    (
      wallet.sendTransaction
      .mockReturnValueOnce(new Promise(resolve=>resolve({hash: '0x0000'})))
      .mockReturnValueOnce(new Promise(resolve=>resolve({hash: '0x0001'})))
    )
    documentStore.populateTransaction.issue.mockReset();
    (
      documentStore.populateTransaction.issue
      .mockReturnValueOnce(new Promise(resolve=>resolve({data:'documentIssueData'})))
      .mockReturnValueOnce(new Promise(()=>{throw new Error('Only hashes that have not been issued can be issued')}))
    )

    const batch = new Batch();
    batch.merkleRoot = '0000000000000000000000000000000';
    const issueBatch = new IssueBatch(<Wallet><unknown>wallet, <DocumentStore><unknown>documentStore, batch);
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
    (
      wallet.provider.waitForTransaction
      .mockReturnValueOnce(new Promise(()=>{throw new Error('timeout exceeded')}))
      .mockReturnValueOnce(new Promise((resolve)=>resolve({blockHash:'transaction hash'})))
    )
    wallet.sendTransaction.mockReset();
    (
      wallet.sendTransaction
      .mockReturnValueOnce(new Promise(resolve=>resolve({hash: '0x0000'})))
      .mockReturnValueOnce(new Promise(resolve=>resolve({hash: '0x0001'})))
    )
    documentStore.populateTransaction.issue.mockReset();
    (
      documentStore.populateTransaction.issue
      .mockReturnValue(new Promise(resolve=>resolve({data:'documentIssueData'})))
    )

    const batch = new Batch();
    batch.merkleRoot = '0000000000000000000000000000000';
    const issueBatch = new IssueBatch(<Wallet><unknown>wallet, <DocumentStore><unknown>documentStore, batch);
    await issueBatch.start();
    // first time transaction times out, second time is successful
    expect(wallet.provider.waitForTransaction.mock.calls.length).toBe(2);
    expect(wallet.provider.waitForTransaction.mock.calls[0][0]).toBe('0x0000');
    expect(wallet.provider.waitForTransaction.mock.calls[1][0]).toBe('0x0001');
  });

  test('gas price increase', async ()=>{
    wallet.provider.waitForTransaction.mockReset();
    (
      wallet.provider.waitForTransaction
      .mockReturnValueOnce(new Promise(()=>{throw new Error('timeout exceeded')}))
      .mockReturnValueOnce(new Promise(()=>{throw new Error('timeout exceeded')}))
      .mockReturnValueOnce(new Promise(()=>{throw new Error('timeout exceeded')}))
      .mockReturnValueOnce(new Promise((resolve)=>resolve({blockHash:'transaction hash'})))
    )
    wallet.sendTransaction.mockReset();
    (
      wallet.sendTransaction
      .mockReturnValueOnce(new Promise(resolve=>resolve({hash: '0x0000'})))
      .mockReturnValueOnce(new Promise(resolve=>resolve({hash: '0x0001'})))
      .mockReturnValueOnce(new Promise(resolve=>resolve({hash: '0x0002'})))
      .mockReturnValueOnce(new Promise(resolve=>resolve({hash: '0x0003'})))
    )
    documentStore.populateTransaction.issue.mockReset();
    (
      documentStore.populateTransaction.issue
      .mockReturnValue(new Promise(resolve=>resolve({data:'documentIssueData'})))
    )
    const batch = new Batch();
    batch.merkleRoot = '0000000000000000000000000000000';
    const issueBatch = new IssueBatch(
      <Wallet><unknown>wallet,
      <DocumentStore><unknown>documentStore,
      batch,
      GAS_PRICE_MULTIPLIER
    );
    await issueBatch.start();
    // only fourth transaction passes, gas price multiplier = 1.2 ^ 3
    expect(wallet.provider.waitForTransaction.mock.calls.length).toBe(4);
    expect(wallet.provider.waitForTransaction.mock.calls[0][0]).toBe('0x0000');
    expect(wallet.provider.waitForTransaction.mock.calls[1][0]).toBe('0x0001');
    expect(wallet.provider.waitForTransaction.mock.calls[2][0]).toBe('0x0002');
    expect(wallet.provider.waitForTransaction.mock.calls[3][0]).toBe('0x0003');
    const gasPrice: BigNumber = wallet.sendTransaction.mock.calls[3][0].gasPrice;
    const expectedGasPrice = utils.parseEther((parseFloat(utils.formatEther(GAS_PRICE)) * Math.pow(GAS_PRICE_MULTIPLIER, 3)).toFixed(18));
    expect(gasPrice.eq(expectedGasPrice)).toBeTruthy()
  });

});
