import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { wrapDocument } from '@govtechsg/open-attestation';
import { Wallet } from 'ethers';
import { documentV2 } from 'tests/utils';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { IssueBatch, Batch } from 'src/tasks';


describe('IssueBatch Task', ()=>{
  jest.setTimeout(1000 * 100);
  let wallet: Wallet;
  let documentStore: DocumentStore;
  beforeAll(async (done)=>{
    wallet = await connectWallet();
    documentStore = await connectDocumentStore(wallet);
    done();
  }, 1000 * 60);

  test('issue test', async ()=>{
    const document = wrapDocument(documentV2({body: 'random document'}));
    const batch = new Batch();
    batch.merkleRoot = document.signature.merkleRoot;
    const issueBatch = new IssueBatch({
      wallet,
      documentStore,
      batch,
      gasPriceLimitGwei: 200,
      gasPriceMultiplier: 1.2,
      transactionConfirmationThreshold: 1,
      transactionTimeoutSeconds: 180,
      attempts: 1,
      attemptsIntervalSeconds: 1
    });
    await issueBatch.start();
    const isIssued = await documentStore.isIssued('0x'+batch.merkleRoot);
    expect(isIssued).toBe(true);
  });
});
