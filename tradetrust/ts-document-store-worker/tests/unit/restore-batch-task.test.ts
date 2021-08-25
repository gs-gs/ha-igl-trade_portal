import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import { getBatchedDocumentStoreTaskEnvConfig } from 'src/config';
import { BatchDocuments, InvalidDocuments } from 'src/repos';
import { Batch } from 'src/tasks/common/data';
import RestoreBatch from 'src/tasks/common/restore-batch';
import {
  generateDocumentsMap,
} from 'tests/utils';

class NoSuchKey extends Error{
  public code: string = 'NoSuchKey'
}

describe('RestoreBatch task unit tests',()=>{

  jest.setTimeout(10 * 1000);

  const createBatchDocumentsRepoMock = ()=>({
    list: jest.fn(),
    get: jest.fn(),
    delete: jest.fn().mockResolvedValue(true)
  })

  const createInvalidDocumentsRepoMock = ()=>({
    put: jest.fn().mockResolvedValue(true)
  })

  const config = getBatchedDocumentStoreTaskEnvConfig();

  const createDocumentStoreMock = ()=>({
    address: config.DOCUMENT_STORE_ADDRESS,
    isRevoked: jest.fn().mockResolvedValue(true)
  })


  test('test retry mechanism', async ()=>{
    const batchDocuments = createBatchDocumentsRepoMock();
    const invalidDocuments = createInvalidDocumentsRepoMock();
    const documentStore = createDocumentStoreMock();
    const documents = generateDocumentsMap(5);
    // LI=0
    batchDocuments.list.mockRejectedValueOnce(new Error('Unexpected Error'))
    // LI=1
    batchDocuments.list.mockResolvedValue({
      Contents: [
        {
          Key: 'document-key-0',
          Size: 1
        },
        {
          Key: 'document-key-1',
          Size: 2,
        },
        {
          Key: 'document-key-2',
          Size: 3
        },
        {
          Key: 'document-key-3',
          Size: 4
        },
        {
          Key: 'document-key-4',
          Size: 5
        }
      ],
      ContinuationToken: undefined
    });
    // LI=1 I=0
    batchDocuments.get
    .mockResolvedValueOnce({
      Body: JSON.stringify(documents.get('document-key-0'))
    })
    // LI=1 I=1
    .mockRejectedValueOnce(new Error('Unexpected Error'))
    // LI=1 I=2
    .mockResolvedValueOnce({
      Body: JSON.stringify(documents.get('document-key-1'))
    })
    // LI=1 I=3
    .mockResolvedValueOnce({
      Body: JSON.stringify(documents.get('document-key-2'))
    })
    // LI=1 I=4
    .mockRejectedValueOnce(new NoSuchKey())
    // LI=1 I=5
    .mockResolvedValueOnce({
      Body: 'not a valid json;;;ttt'
    });
    const batch = new Batch();
    const restoreBatch = new RestoreBatch({
      batch,
      wrapped: false,
      documentStore: <DocumentStore><unknown>documentStore,
      invalidDocuments: <InvalidDocuments><unknown>invalidDocuments,
      batchDocuments: <BatchDocuments><unknown>batchDocuments,
      batchSizeBytes: 1024 * 1024 * 10,
      batchTimeSeconds: 10,
      attempts: 10,
      attemptsIntervalSeconds: 1,
    });
    await restoreBatch.start();
    const expectedDocuments = new Map<string, any>();
    expectedDocuments.set('document-key-0', {size: 1, body: documents.get('document-key-0')});
    expectedDocuments.set('document-key-1', {size: 2, body: documents.get('document-key-1')});
    expectedDocuments.set('document-key-2', {size: 3, body: documents.get('document-key-2')});
    expect(batch.unwrappedDocuments.size).toBe(expectedDocuments.size);
    expect(batch.unwrappedDocuments).toEqual(expectedDocuments);
    // // calls count including all retry attemps
    expect(batchDocuments.list.mock.calls.length).toBe(3);
    // // one document was deleted before RestoreBatch task was able to add into a batch
    // // one document wans't a valid json
    // // one document throwed an unexpected error
    expect(batchDocuments.get.mock.calls.length).toBe(6);
  });

  test('ran out of attempts', async ()=>{
    const attempts = 3;
    const batchDocuments = createBatchDocumentsRepoMock();
    const invalidDocuments = createInvalidDocumentsRepoMock();
    const documentStore = createDocumentStoreMock();
    batchDocuments.list.mockRejectedValue(new Error('Unexpected Error'));
    const batch = new Batch();
    const restoreBatch = new RestoreBatch({
      batch,
      wrapped: false,
      documentStore: <DocumentStore><unknown>documentStore,
      invalidDocuments: <InvalidDocuments><unknown>invalidDocuments,
      batchDocuments: <BatchDocuments><unknown>batchDocuments,
      batchSizeBytes: 1024 * 1024 * 10,
      batchTimeSeconds: 10,
      attempts,
      attemptsIntervalSeconds: 1,
    });
    try{
      await restoreBatch.start();
    }catch(e){
      expect(e.message).toBe('Unexpected Error');
      expect(batchDocuments.list.mock.calls.length).toBe(attempts);
    }
  });
});
