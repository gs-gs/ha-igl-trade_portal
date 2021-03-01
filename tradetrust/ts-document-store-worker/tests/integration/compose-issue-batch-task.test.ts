import { getBatchedDocumentStoreTaskEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { Batch, ComposeIssueBatch } from 'src/tasks';
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

describe('ComposeBatch Task', ()=>{
  jest.setTimeout(1000 * 100);
  const config = getBatchedDocumentStoreTaskEnvConfig();
  beforeEach(async (done)=>{
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.BATCH_BUCKET_NAME);
    done();
  }, 1000 * 60);

  const unprocessedDocuments = new UnprocessedDocuments(config);
  const batchDocuments = new BatchDocuments(config);
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue(config);


  test('batch backup', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);
    const documents = generateDocumentsMap(10);
    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
    }


    const batch = new Batch();
    const composeBatch = new ComposeIssueBatch({
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      batchTimeSeconds: 5,
      batchSizeBytes: 1024 * 1024 * 1024,
      messageWaitTime: 1,
      messageVisibilityTimeout: 60,
      wallet: wallet,
      documentStore: documentStore,
      attempts: 1,
      attemptsIntervalSeconds: 1,
      batch
    });
    await composeBatch.start();

    for(let [key, document] of documents){
      expect(document).toEqual(batch.unwrappedDocuments.get(key)?.body);
      const s3Object = await batchDocuments.get({Key: key});
      expect(document).toEqual(JSON.parse(s3Object.Body?.toString() || ''))
    }
  });


  test('invalid documents handling', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);

    const documents = new Map<string, any>();
    documents.set('non-json-document', 'non-json-document-body');
    documents.set('deleted-document', documentV2({body: 'deleted-document-body'}));
    documents.set('regular-document', documentV2({body: 'regular-document-body'}));
    documents.set('invalid-document', {body: 'invalid-document-body'});
    documents.set('invalid-document-store-document', documentV2({
      body: 'invalid-document-store-document-body',
      issuers:[
        {
          name: 'DEMO STORE',
          documentStore: 'invalid-document-store-address',
          identityProof: {
            type: 'DNS-TXT',
            location: 'tradetrust.io'
          }
        }
      ]
    }));
    // adding the document and modifying its event to set invalid etag
    await unprocessedDocuments.put({Key: 'invalid-etag-document', Body: JSON.stringify(documentV2({body: 'invalid-etag-body-1'}))});
    const invalidETagDocumentPutEvent: any = await unprocessedDocumentsQueue.get();
    invalidETagDocumentPutEvent.Body = JSON.parse(invalidETagDocumentPutEvent.Body);
    invalidETagDocumentPutEvent.Body.Records[0].s3.object.eTag = 'invalid-etag';
    await unprocessedDocumentsQueue.delete({ReceiptHandle: invalidETagDocumentPutEvent.ReceiptHandle});
    await unprocessedDocumentsQueue.post({MessageBody: JSON.stringify(invalidETagDocumentPutEvent.Body)});

    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
    }
    await unprocessedDocuments.delete({Key: 'deleted-document'});
    const batch = new Batch();
    const composeBatch = new ComposeIssueBatch({
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      batchTimeSeconds: 5,
      batchSizeBytes: 1024 * 1024 * 1024,
      messageWaitTime: 1,
      messageVisibilityTimeout: 60,
      wallet: wallet,
      documentStore: documentStore,
      batch
    });
    await composeBatch.start();
    expect(batch.wrappedDocuments.size).toBe(0);
    expect(batch.unwrappedDocuments.get('non-json-document')).toBeFalsy();
    expect(batch.unwrappedDocuments.get('deleted-document')).toBeFalsy();
    expect(batch.unwrappedDocuments.get('invalid-document')).toBeFalsy();
    expect(batch.unwrappedDocuments.get('invalid-document-store-document')).toBeFalsy();
    expect(batch.unwrappedDocuments.get('invalid-etag-document')).toBeFalsy();
    expect(batch.unwrappedDocuments.get('regular-document')).toBeTruthy();
  });

  test('complete by time', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);

    const documents = generateDocumentsMap(10);
    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
    }
    const batch = new Batch();
    const composeBatch = new ComposeIssueBatch({
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      batchTimeSeconds: 5,
      batchSizeBytes: 1024 * 1024 * 1024,
      messageWaitTime: 1,
      messageVisibilityTimeout: 60,
      wallet: wallet,
      documentStore: documentStore,
      batch
    });

    await composeBatch.start();

    const expectedBatchDocuments = Array.from<any>(documents.values());
    const resultingBatchDocuments = Array.from<any>(batch.unwrappedDocuments.values()).map(entry=>entry.body);

    expect(resultingBatchDocuments).toEqual(expectedBatchDocuments);
  });

  test('complete by size', async ()=>{
    const wallet = await connectWallet(config);
    const documentStore = await connectDocumentStore(config, wallet);

    const documentsCount = 20;
    const expectedBatchDocumentsCount = 10;
    let maxBatchSizeBytes = 0;
    const documents = generateDocumentsMap(documentsCount)

    let documentIndex = 0;
    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
      if(documentIndex < expectedBatchDocumentsCount){
        maxBatchSizeBytes += (await unprocessedDocuments.get({Key:key})).ContentLength??0;
      }
      documentIndex++;
    }
    const batch = new Batch();
    const composeBatch = new ComposeIssueBatch({
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      batchTimeSeconds: 10,
      batchSizeBytes: maxBatchSizeBytes,
      messageWaitTime: 1,
      messageVisibilityTimeout: 60,
      wallet: wallet,
      documentStore: documentStore,
      batch
    });
    await composeBatch.start();

    const expectedBatchDocuments = Array.from<any>(documents.values()).slice(0, expectedBatchDocumentsCount);
    const resultingBatchDocuments = Array.from<any>(batch.unwrappedDocuments.values()).map(entry=>entry.body);
    expect(resultingBatchDocuments).toEqual(expectedBatchDocuments);
  });
});
