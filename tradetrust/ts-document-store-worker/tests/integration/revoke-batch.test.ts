import { wrapDocuments } from '@govtechsg/open-attestation';
import { getBatchedRevokeEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { Batch, RevokeBatch } from 'src/tasks';
import { documentV2 } from 'tests/utils';


describe('Revoke batch task integration test', ()=>{
  const config = getBatchedRevokeEnvConfig();
  jest.setTimeout(100 * 1000);
  test('test revoke', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);
    const batch = new Batch();
    const unwrappedDocuments = [{body: 'document-1'}, {body: 'document-2'}, {body: 'document-3'}].map(d=>documentV2(d))
    const wrappedDocuments = wrapDocuments(unwrappedDocuments);
    batch.wrappedDocuments.set('document-1', {body: wrappedDocuments[0], size: 0});
    batch.wrappedDocuments.set('document-2', {body: wrappedDocuments[1], size: 0});
    const revokeBatch = new RevokeBatch({
      wallet,
      documentStore,
      attempts: 1,
      attemptsIntervalSeconds: 60,
      transactionTimeoutSeconds: 60,
      transactionConfirmationThreshold: 1,
      batch
    })
    await revokeBatch.start();
    expect(await documentStore.isRevoked(`0x${wrappedDocuments[0].signature.targetHash}`)).toBe(true);
    expect(await documentStore.isRevoked(`0x${wrappedDocuments[1].signature.targetHash}`)).toBe(true);
    expect(await documentStore.isRevoked(`0x${wrappedDocuments[2].signature.targetHash}`)).toBe(false);
    try{
      await revokeBatch.start();
      // should throw an error before reaching expect
      expect(false).toBe(true);
    }catch(e){
      expect(e.message).toContain('Hash has been revoked previously');
    }
  });
})
