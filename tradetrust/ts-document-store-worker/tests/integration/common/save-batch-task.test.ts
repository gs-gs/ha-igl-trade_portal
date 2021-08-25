import { getBatchedIssueEnvConfig } from 'src/config';
import { IssuedDocuments, BatchDocuments } from 'src/repos';
import { Batch } from 'src/tasks/common/data';
import SaveBatch from 'src/tasks/common/save-batch';
import { wrapDocuments } from '@govtechsg/open-attestation';
import { clearBucket, documentV2 } from "tests/utils";

describe('SaveBatch Task', ()=>{

  jest.setTimeout(1000 * 100);
  const config = getBatchedIssueEnvConfig();
  beforeEach(async (done)=>{
    await clearBucket(config.BATCH_BUCKET_NAME);
    await clearBucket(config.ISSUED_BUCKET_NAME);
    done();
  }, 1000 * 60);

  const issuedDocuments = new IssuedDocuments(config);
  const batchDocuments = new BatchDocuments(config);

  test('save batch documents', async ()=>{
    const batch = new Batch();
    const documents = new Map<string, any>();
    for(let documentIndex = 0; documentIndex < 10; documentIndex++){
      const key = `document-${documentIndex}`;
      const body = `document-body-${documentIndex}`;
      const document = documentV2({body})
      const documentString = JSON.stringify(document);
      await batchDocuments.put({Key:key, Body: documentString});
      documents.set(key, document);
    }
    const wrappedDocuments = wrapDocuments(Array.from<any>(documents.values()));
    const wrappedDocumentsKeys = Array.from<string>(documents.keys());
    for(let documentIndex = 0; documentIndex < wrappedDocumentsKeys.length; documentIndex++){
      batch.wrappedDocuments.set(wrappedDocumentsKeys[documentIndex], { body: wrappedDocuments[documentIndex], size: 0});
    }
    const saveIssuedBatch = new SaveBatch({
      processedDocuments: issuedDocuments,
      batchDocuments,
      batch,
      attempts: 1,
      attemptsIntervalSeconds: 1
    });
    await saveIssuedBatch.start();
    for(let [key, document] of batch.wrappedDocuments){
        const issuedDocumentS3Object = await issuedDocuments.get({Key: key});
        const issuedDocument = JSON.parse(issuedDocumentS3Object!.Body!.toString());
        expect(issuedDocument).toEqual(document.body);
        try{
          await batchDocuments.get({Key:key})
        }catch(e){
          expect(e.code).toBe('NoSuchKey')
        }
    }
  })
});
