import config from '../src/config';
import { ComposeBatch } from '../src/tasks';
import {
  UnprocessedDocuments,
  BatchDocuments,
  UnprocessedDocumentsQueue
} from '../src/repos';
import {
  clearQueue,
  clearBucket,
  documentV2,
} from './utils';

jest.setTimeout(1000 * 60);

describe('ComposeBatch Task', ()=>{
  beforeEach(async ()=>{
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.BATCH_BUCKET_NAME);
  });

  const unprocessedDocuments = new UnprocessedDocuments();
  const batchDocuments = new BatchDocuments();
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue();

  test('complete by time', async ()=>{

    const documents = new Map<string, any>();
    for(let documentIndex = 0; documentIndex < 10; documentIndex++){
      const key = `document-${documentIndex}`;
      const body = `document-body-${documentIndex}`;
      const document = documentV2({body});
      documents.set(key, document);
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
    }

    const composeBatch = new ComposeBatch(
      unprocessedDocuments,
      batchDocuments,
      unprocessedDocumentsQueue,
      10,
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

    const documents = new Map<string, any>();
    const expectedBatchDocumentsCount = 10;
    let maxBatchSizeBytes = 0;

    for(let documentIndex = 0; documentIndex < 20; documentIndex++){
      const key = `document-${documentIndex}`;
      const body = `document-body-${documentIndex}`;
      const document = documentV2({body});
      documents.set(key, document);
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)});
      if(documentIndex < expectedBatchDocumentsCount){
        maxBatchSizeBytes += (await unprocessedDocuments.get({Key:key})).ContentLength??0;
      }
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
