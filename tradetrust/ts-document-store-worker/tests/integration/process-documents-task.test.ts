import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { getData } from '@govtechsg/open-attestation';
import {
  UnprocessedDocuments,
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocumentsQueue
} from 'src/repos';
import config from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { ProcessDocuments } from 'src/tasks';
import { clearQueue, clearBucket, generateDocumentsMap } from 'tests/utils';

describe('Test', ()=>{

  jest.setTimeout(1000 * 60);

  const documentsCount = 20;
  const documents = generateDocumentsMap(documentsCount);

  const unprocessedDocuments = new UnprocessedDocuments();
  const batchDocuments = new BatchDocuments();
  const issuedDocuments = new IssuedDocuments();
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue();

  const wallet = connectWallet();
  let documentStore: DocumentStore;

  beforeEach(async ()=>{
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.BATCH_BUCKET_NAME);
    await clearBucket(config.ISSUED_BUCKET_NAME);
    documentStore = await connectDocumentStore(wallet);
  })

  test('test complete by size', async ()=>{

    const expectedBatchDocuments = Array.from<[string, any]>(documents.entries()).slice(0, 10);
    for(let [key, document] of documents){
      await unprocessedDocuments.put({Key: key, Body: JSON.stringify(document)})
    }
    let maxBatchSizeBytes: number = 0;
    for(let [key] of expectedBatchDocuments){
      let documentS3Object = await unprocessedDocuments.get({Key: key})
      maxBatchSizeBytes += documentS3Object.ContentLength!;
    }

    const processDocuments = new ProcessDocuments(
      unprocessedDocuments,
      batchDocuments,
      issuedDocuments,
      unprocessedDocumentsQueue,
      wallet,
      documentStore,
      1,
      maxBatchSizeBytes,
      60
    );

    await processDocuments.next();

    const signatures = Array<string>();

    for(let [key, document] of expectedBatchDocuments){
      const issuedDocumentS3Object = await issuedDocuments.get({Key: key});
      const issuedDocument = JSON.parse(issuedDocumentS3Object.Body!.toString());
      signatures.push(issuedDocument.signature.merkleRoot);
      const unwrappedIssuedDocument = getData(issuedDocument);
      expect(unwrappedIssuedDocument).toEqual(document);
    }
    expect(signatures.every(signature=> signature == signatures[0])).toBe(true);
  });
})
