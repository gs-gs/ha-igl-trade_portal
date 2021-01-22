import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { wrapDocument } from '@govtechsg/open-attestation';
import { Wallet } from 'ethers';
import { documentV2 } from 'tests/utils';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { IssueBatch, Batch } from 'src/tasks';


describe('IssueBatch Task', ()=>{
  jest.setTimeout(1000 * 10);
  let documentStore: DocumentStore;
  let wallet: Wallet;
  beforeAll(async ()=>{
    wallet = connectWallet();
    documentStore = await connectDocumentStore(wallet);
  });
  test('issue test', async ()=>{
    const document = wrapDocument(documentV2({body: 'random document'}));
    const batch = new Batch();
    batch.merkleRoot = document.signature.merkleRoot;
    const issueBatch = new IssueBatch(wallet, documentStore, batch);
    await issueBatch.start();
    const isIssued = await documentStore.isIssued('0x'+batch.merkleRoot);
    expect(isIssued).toBe(true);
  });
});
