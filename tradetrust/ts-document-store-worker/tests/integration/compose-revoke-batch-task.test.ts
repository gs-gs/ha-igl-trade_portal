import { wrapDocument } from '@govtechsg/open-attestation';
import { getBatchedRevokeEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { Batch, ComposeRevokeBatch } from 'src/tasks';
import {
  UnprocessedDocuments,
  BatchDocuments,
  UnprocessedDocumentsQueue
} from 'src/repos';
import {
  clearQueue,
  clearBucket,
  documentV2,
  generateDocumentsMap,
} from 'tests/utils';



describe('ComposeRevokeBatch integration test', ()=>{
  jest.setTimeout(100 * 1000);

  const config = getBatchedRevokeEnvConfig();
  const unprocessedDocuments = new UnprocessedDocuments(config);
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue(config);
  const batchDocuments = new BatchDocuments(config);

  beforeEach(async (done)=>{
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.BATCH_BUCKET_NAME);
    done();
  }, 1000 * 60);


  test('single document batch', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);
    const unwrappedDocumentsMap = generateDocumentsMap(5);
    const wrappedDocumentsMap = new Map<string, any>();
    for(let [key, body] of unwrappedDocumentsMap){
      body = wrapDocument(body);
      wrappedDocumentsMap.set(key, body);
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(body)});
    }
    const batch = new Batch();
    const composeRevokeBatch = new ComposeRevokeBatch({
      wallet,
      documentStore,
      batchDocuments,
      unprocessedDocuments,
      unprocessedDocumentsQueue,
      messageWaitTime: 10,
      messageVisibilityTimeout: 10,
      batchSizeBytes: 1,
      batchTimeSeconds: 10,
      attempts: 1,
      attemptsIntervalSeconds: 60,
      batch
    });
    await composeRevokeBatch.start();
  });


  test('invalid documents handling', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);

    const documents = new Map<string, any>();
    const revokedDocument = wrapDocument(documentV2({body:'revoked-document'}));
    await documentStore.revoke(`0x${revokedDocument.signature.targetHash}`);
    documents.set('revoked-document', revokedDocument);
    documents.set('non-json-document', 'non-json-document-body');
    documents.set('deleted-document', documentV2({body: 'deleted-document-body'}));
    documents.set('unwrapped-document', documentV2({body: 'regular-document-body'}));
    documents.set('invalid-document', {body: 'invalid-document-body'});
    documents.set('invalid-document-store-document', wrapDocument(documentV2({
      body: 'invalid-document-store-document-body',
      issuers:[
        {
          name: 'DEMO STORE',
          documentStore: '0x0000000000000000000000000000000000000000',
          identityProof: {
            type: 'DNS-TXT',
            location: 'tradetrust.io'
          }
        }
      ]
    })));
    documents.set('wrapped-document', wrapDocument(documentV2({body: 'wrapped-document-body'})));

    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
    }
    await unprocessedDocuments.delete({Key: 'deleted-document'});

    const batch = new Batch();
    const composeRevokeBatch = new ComposeRevokeBatch({
      wallet,
      documentStore,
      batchDocuments,
      unprocessedDocuments,
      unprocessedDocumentsQueue,
      messageWaitTime: 10,
      messageVisibilityTimeout: 10,
      batchSizeBytes: 1,
      batchTimeSeconds: 10,
      attempts: 1,
      attemptsIntervalSeconds: 60,
      batch
    });
    await composeRevokeBatch.start();
    expect(batch.unwrappedDocuments.size).toBe(0);
    expect(batch.wrappedDocuments.get('revoked-document')).toBeFalsy();
    expect(batch.wrappedDocuments.get('non-json-document')).toBeFalsy();
    expect(batch.wrappedDocuments.get('deleted-document')).toBeFalsy();
    expect(batch.wrappedDocuments.get('unwrapped-document')).toBeFalsy();
    expect(batch.wrappedDocuments.get('invalid-document')).toBeFalsy();
    expect(batch.wrappedDocuments.get('invalid-document-store-document')).toBeFalsy();
    expect(batch.wrappedDocuments.get('wrapped-document')).toBeTruthy();
  });
});
