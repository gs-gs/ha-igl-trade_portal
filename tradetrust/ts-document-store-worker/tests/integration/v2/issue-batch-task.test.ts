import { wrapDocument } from '@govtechsg/open-attestation';
import { getBatchedDocumentStoreTaskEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { Batch } from 'src/tasks/common/data';
import IssueBatch from 'src/tasks/v2/issue-batch';
import { documentV2 } from 'tests/utils';


describe('IssueBatch Task', ()=>{
  jest.setTimeout(1000 * 100);
  const config = getBatchedDocumentStoreTaskEnvConfig();
  test('issue test', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);
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
