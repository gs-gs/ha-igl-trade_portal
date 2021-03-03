import { wrapDocument } from '@govtechsg/open-attestation';
import { getBatchedRevokeEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { Batch, ComposeRevokeBatch } from 'src/tasks';
import {
  InvalidDocuments,
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
  const invalidDocuments = new InvalidDocuments(config);

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
      invalidDocuments,
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
    const invalidDocumentStoreAddress = '0x0000000000000000000000000000000000000000';
    const invalidDocumentSignature = '0x0000000000000000000000000000000000000000';

    const documents = new Map<string, any>();
    const invalidSignatureDocument = wrapDocument(documentV2({body: 'invalid-signature'}))
    invalidSignatureDocument.signature.merkleRoot = invalidDocumentSignature;
    const revokedDocument = wrapDocument(documentV2({body:'revoked-document'}));
    await documentStore.revoke(`0x${revokedDocument.signature.targetHash}`);
    documents.set('invalid-signature-document', invalidSignatureDocument);
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
          documentStore: invalidDocumentStoreAddress,
          identityProof: {
            type: 'DNS-TXT',
            location: 'tradetrust.io'
          }
        }
      ]
    })));
    documents.set('wrapped-document', wrapDocument(documentV2({body: 'wrapped-document-body'})));

    for(let [key, document] of documents){
      if(typeof document !== 'string'){
        document = JSON.stringify(document);
      }
      await unprocessedDocuments.put({Key: key, Body: document});
    }
    await unprocessedDocuments.delete({Key: 'deleted-document'});

    const batch = new Batch();
    const composeRevokeBatch = new ComposeRevokeBatch({
      wallet,
      documentStore,
      batchDocuments,
      unprocessedDocuments,
      unprocessedDocumentsQueue,
      invalidDocuments,
      messageWaitTime: 10,
      messageVisibilityTimeout: 10,
      batchSizeBytes: 1,
      batchTimeSeconds: 10,
      attempts: 1,
      attemptsIntervalSeconds: 60,
      batch
    });
    await composeRevokeBatch.start();

    const checkInvalidDocument = async (key: string, reason: string)=>{
      expect(batch.wrappedDocuments.get(key)).toBeFalsy();
      const invalidDocumentReasonBody = JSON.parse((await invalidDocuments.get({Key: `${key}.reason.json`})).Body?.toString()??'{}');
      const expectedDocumentBody = documents.get(key);
      if(typeof expectedDocumentBody === 'string'){
        const invalidDocumentBody = (await invalidDocuments.get({Key: key})).Body?.toString();
        expect(invalidDocumentBody).toMatch(documents.get(key));
      }else{
        const invalidDocumentBody = JSON.parse((await invalidDocuments.get({Key: key})).Body?.toString()??'{}');
        expect(invalidDocumentBody).toEqual(documents.get(key));
      }
      expect(invalidDocumentReasonBody).toEqual({
        reason: reason
      })
    }


    expect(batch.unwrappedDocuments.size).toBe(0);
    expect(batch.wrappedDocuments.size).toBe(1);
    await checkInvalidDocument(
      'invalid-document-store-document',
      `Expected document store address to be "${documentStore.address}", got "${invalidDocumentStoreAddress}"`
    )
    await checkInvalidDocument(
      'non-json-document',
      'Document body is not a valid JSON'
    )
    await checkInvalidDocument(
      'unwrapped-document',
      'Invalid document schema'
    )
    await checkInvalidDocument(
      'invalid-document',
      'Invalid document schema'
    )
    await checkInvalidDocument(
      'invalid-signature-document',
      'Invalid document signature'
    )
    await checkInvalidDocument(
      'revoked-document',
      `Document 0x${documents.get('revoked-document').signature.targetHash} already revoked`
    )
    expect(batch.wrappedDocuments.get('deleted-document')).toBeFalsy();
    expect(batch.wrappedDocuments.get('wrapped-document')).toBeTruthy();
  });
});
