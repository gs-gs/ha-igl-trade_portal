import {
  __unsafe__use__it__at__your__own__risks__wrapDocuments as wrapDocuments,
} from '@govtechsg/open-attestation';
import { connectWallet } from 'src/document-store';
import { getBatchedIssueEnvConfig } from 'src/config';
import { Batch } from 'src/tasks/common/data';
import { IssueBatch } from 'src/tasks/v3/issue-batch';
import { documentV3 } from 'tests/utils';


describe('IssueBatch Task V3', ()=>{
  beforeEach(()=>{
    jest.setTimeout(1000 * 60);
  })
  const config = getBatchedIssueEnvConfig();
  test('Issue', async ()=>{
    const wallet = await connectWallet(config);
    const batch = new Batch();
    const documents = [documentV3({}), documentV3({})];
    const wrappedDocuments = await wrapDocuments(documents);
    wrappedDocuments.forEach((v,i)=>batch.wrappedDocuments.set(`document-${i}`, {body: v, size: 0}));
    batch.merkleRoot = wrappedDocuments[0].openAttestationMetadata.proof.merkleRoot;
    const issueBatch = new IssueBatch({
      batch,
      signer: wallet
    });
    await issueBatch.start();
    for(let document of batch.wrappedDocuments.values()){
      expect(document.body).toHaveProperty('proof.key');
      expect(document.body).toHaveProperty('proof.signature');
    }
  });
})
