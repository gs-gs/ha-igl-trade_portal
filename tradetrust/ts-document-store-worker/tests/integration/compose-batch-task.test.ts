import config from 'src/config';
import { ComposeBatch } from 'src/tasks';
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
  beforeEach(async (done)=>{
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.BATCH_BUCKET_NAME);
    done();
  }, 1000 * 60);

  const unprocessedDocuments = new UnprocessedDocuments();
  const batchDocuments = new BatchDocuments();
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue();

  test('restore batch', async ()=>{
    const documentsCount = 20;
    const failedBatchDocumentsCount = 10;
    const documents = generateDocumentsMap(documentsCount);
    let documentIndex = 0;
    for(let [key, document] of documents){
      if(documentIndex < failedBatchDocumentsCount){
        await batchDocuments.put({Key: key, Body: JSON.stringify(document)});
      }else{
        await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
      }
      documentIndex++;
    }
    const composeBatch = new ComposeBatch(
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      5,
      1024 * 1024 * 1024,
      1,
      config.DOCUMENT_STORE_ADDRESS
    );
    const batch = await composeBatch.start();

    expect(documents.size).toEqual(batch.unwrappedDocuments.size);
    for(let [key, document] of documents){
      expect(document).toEqual(batch.unwrappedDocuments.get(key)?.body);
    }

  });


  test('batch backup', async ()=>{
    const documents = generateDocumentsMap(10);
    const composeBatch = new ComposeBatch(
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      5,
      1024 * 1024 * 1024,
      1,
      config.DOCUMENT_STORE_ADDRESS
    );
    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
    }
    const batch = await composeBatch.start();
    for(let [key, document] of documents){
      expect(document).toEqual(batch.unwrappedDocuments.get(key)?.body);
      const s3Object = await batchDocuments.get({Key: key});
      expect(document).toEqual(JSON.parse(s3Object.Body?.toString() || ''))
    }
  });


  test('invalid documents handling', async ()=>{
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
    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
    }
    await unprocessedDocuments.delete({Key: 'deleted-document'});
    const composeBatch = new ComposeBatch(
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      5,
      1024 * 1024 * 1024,
      1,
      config.DOCUMENT_STORE_ADDRESS
    );
    const batch = await composeBatch.start();
    expect(batch.unwrappedDocuments.get('non-json-document')).toBeFalsy();
    expect(batch.unwrappedDocuments.get('deleted-document')).toBeFalsy();
    expect(batch.unwrappedDocuments.get('invalid-document')).toBeFalsy();
    expect(batch.unwrappedDocuments.get('invalid-document-store-document')).toBeFalsy();
    expect(batch.unwrappedDocuments.get('regular-document')).toBeTruthy();
  });

  test('complete by time', async ()=>{

    const documents = generateDocumentsMap(10);
    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
    }

    const composeBatch = new ComposeBatch(
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      5,
      1024 * 1024 * 1024,
      1,
      config.DOCUMENT_STORE_ADDRESS
    )

    const batch = await composeBatch.start();

    const expectedBatchDocuments = Array.from<any>(documents.values());
    const resultingBatchDocuments = Array.from<any>(batch.unwrappedDocuments.values()).map(entry=>entry.body);

    expect(resultingBatchDocuments).toEqual(expectedBatchDocuments);
  });

  test('complete by size', async ()=>{

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

    const composeBatch = new ComposeBatch(
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      10,
      maxBatchSizeBytes,
      1,
      config.DOCUMENT_STORE_ADDRESS
    )
    const batch = await composeBatch.start();

    const expectedBatchDocuments = Array.from<any>(documents.values()).slice(0, expectedBatchDocumentsCount);
    const resultingBatchDocuments = Array.from<any>(batch.unwrappedDocuments.values()).map(entry=>entry.body);
    expect(resultingBatchDocuments).toEqual(expectedBatchDocuments);
  });
});
