import {
  wrapDocument as wrapDocumentV2,
  __unsafe__use__it__at__your__own__risks__wrapDocument as wrapDocumentV3
} from '@govtechsg/open-attestation';
import { OpenAttestationVersion as Version } from 'src/constants';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { getBatchedRevokeEnvConfig } from 'src/config';
import { Batch } from 'src/tasks/common/data';
import { RevokeBatch } from 'src/tasks/common/revoke-batch';
import {
  generateDocumentsMapV2,
  generateDocumentsMapV3,
} from 'tests/utils';


describe('RevokeBatch Task', ()=>{
  const config = getBatchedRevokeEnvConfig();

  beforeEach(()=>{
    jest.setTimeout(1000 * 60);
  });

  const TEST_PARAMS = [
    {
      version: Version.V2,
      generateDocumentsMap: generateDocumentsMapV2,
      wrapDocument: async (document: any)=>wrapDocumentV2(document),
      getSignature: (document: any)=>document.signature.targetHash
    },
    {
      version: Version.V3,
      generateDocumentsMap: generateDocumentsMapV3,
      wrapDocument: async (document: any)=>await wrapDocumentV3(document),
      getSignature: (document: any)=>document.proof.targetHash
    }
  ]

  describe.each(TEST_PARAMS)('Revoke', ({
    version,
    generateDocumentsMap,
    wrapDocument,
    getSignature
  })=>{
    test(version, async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);
      const batch = new Batch();
      const documents = generateDocumentsMap(3);
      const wrappedDocuments = new Map<string, any>();
      for(let [key, document] of documents){wrappedDocuments.set(key, await wrapDocument(document))}
      batch.wrappedDocuments.set('document-key-0', {size: 0, body: wrappedDocuments.get('document-key-0')});
      batch.wrappedDocuments.set('document-key-1', {size: 0, body: wrappedDocuments.get('document-key-1')});
      const revokeBatch = new RevokeBatch({
        version,
        wallet,
        documentStore,
        attempts: 1,
        attemptsIntervalSeconds: 60,
        transactionTimeoutSeconds: 60,
        transactionConfirmationThreshold: 1,
        batch
      });
      await revokeBatch.start();
      const expectRevoked = async (key: string, status: boolean)=>{
        expect(await documentStore.isRevoked(`0x${getSignature(wrappedDocuments.get(key))}`)).toBe(status);
      }
      await expectRevoked('document-key-0', true);
      await expectRevoked('document-key-1', true);
      await expectRevoked('document-key-2', false);
      try{
        await revokeBatch.start();
        // should throw an error before reaching expect
        expect(false).toBe(true);
      }catch(e){
        expect(e.message).toContain('Hash has been revoked previously');
      }
    });
  });
})
