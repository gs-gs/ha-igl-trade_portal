import { Wallet } from 'ethers';
import { DocumentStore } from '@govtechsg/document-store/src/contracts/DocumentStore';
import _ from 'lodash';
import {
  UnprocessedDocuments,
  UnprocessedDocumentsQueue,
  BatchDocuments,
  InvalidDocuments
} from 'src/repos';
// using ComposeIssueBatch because it's a child of ComposeBatch task
import ComposeIssueBatch from 'src/tasks/v2/compose-issue-batch';
import { Batch } from 'src/tasks/common/data';
import { getBatchedDocumentStoreTaskEnvConfig } from 'src/config';
import {
  documentV2
} from 'tests/utils';


class UnexpectedError extends Error{
  constructor(){
    super('Unexpected Error');
  }
}

class NoSuchKey extends Error{
  public code: string = 'NoSuchKey'
}

function SQSS3Event(s3Object: any){
  return {
    ReceiptHandle: 'ReceiptHandleValue',
    Body: JSON.stringify({
      Records: [
        {
          eventName: 'ObjectCreated:Put',
          s3: {
            object: s3Object
          }
        }
      ]
    })
  }
}


function S3ObjectResponse(s3Object: any){
  s3Object = _.cloneDeep(s3Object);
  s3Object.Body = JSON.stringify(s3Object.Body);
  return s3Object;
}


describe('ComposeBatch task unit tests', ()=>{
  jest.setTimeout(100 * 1000);
  const config = getBatchedDocumentStoreTaskEnvConfig();
  const createUnprocessedDocumentsQueueMock = ()=>{
    return {
      get: jest.fn(),
      delete: jest.fn()
    }
  }
  const createDocumentsRepoMock = ()=>{
    return {
      get: jest.fn(),
      delete: jest.fn(),
      put: jest.fn()
    }
  }

  const createInvalidDocumentsMock = ()=>{
    return {
      put: jest.fn()
    }
  }

  const createDocumentStoreMock = ()=>{
    return {
      address: config.DOCUMENT_STORE_ADDRESS
    }
  }

  const createWalletMock = ()=>{
    return {}
  }

  test('ran out of attempts', async ()=>{
    const documentStore = createDocumentStoreMock();
    const wallet = createWalletMock();
    const unprocessedDocuments = createDocumentsRepoMock();
    const batchDocuments = createDocumentsRepoMock();
    const unprocessedDocumentsQueue = createUnprocessedDocumentsQueueMock();
    const invalidDocuments = createInvalidDocumentsMock();
    const attempts = 4;

    unprocessedDocumentsQueue.get.mockRejectedValue(new Error('Unexpected Error'));

    const batch = new Batch();
    const composeBatch = new ComposeIssueBatch({
      invalidDocuments: <InvalidDocuments><unknown>invalidDocuments,
      unprocessedDocuments: <UnprocessedDocuments><unknown>unprocessedDocuments,
      unprocessedDocumentsQueue: <UnprocessedDocumentsQueue><unknown>unprocessedDocumentsQueue,
      batchDocuments: <BatchDocuments><unknown>batchDocuments,
      batch,
      batchSizeBytes: 1024 * 1024 * 10,
      batchTimeSeconds: 10,
      attempts,
      attemptsIntervalSeconds: 1,
      messageWaitTime: 1,
      messageVisibilityTimeout: 60,
      wallet: <Wallet>wallet,
      documentStore: <DocumentStore>documentStore
    })

    try{
      await composeBatch.start();
    }catch(e){
      expect(e.message).toBe('Unexpected Error');
      expect(unprocessedDocumentsQueue.get.mock.calls.length).toBe(attempts);
    }

  });

  test('retry errors', async ()=>{
    const documentStore = createDocumentStoreMock();
    const wallet = createWalletMock();
    const unprocessedDocuments = createDocumentsRepoMock();
    const batchDocuments = createDocumentsRepoMock();
    const unprocessedDocumentsQueue = createUnprocessedDocumentsQueueMock();
    const invalidDocuments = createInvalidDocumentsMock();
    const attempts = 10;


    // I=1
    unprocessedDocumentsQueue.get.mockRejectedValueOnce(new UnexpectedError());


    // I=2
    unprocessedDocumentsQueue.get.mockResolvedValueOnce(SQSS3Event({
      key: 'document-1'
    }))
    unprocessedDocuments.get.mockRejectedValueOnce(new UnexpectedError())


    // I=3
    unprocessedDocumentsQueue.get.mockResolvedValueOnce(SQSS3Event({
      key: 'document-1'
    }))
    unprocessedDocuments.get.mockResolvedValueOnce(S3ObjectResponse({
      ContentLength: 1,
      Body: documentV2({body: 'document-1-body'})
    }))
    batchDocuments.put.mockRejectedValueOnce(new UnexpectedError())


    // I=4
    unprocessedDocumentsQueue.get.mockResolvedValueOnce(SQSS3Event({
      key: 'document-1'
    }))
    unprocessedDocuments.get.mockResolvedValueOnce(S3ObjectResponse({
      ContentLength: 1,
      Body: documentV2({body: 'document-1-body'})
    }))
    batchDocuments.put.mockResolvedValueOnce(true);
    unprocessedDocuments.delete.mockRejectedValueOnce(new UnexpectedError());


    // I=5
    unprocessedDocumentsQueue.get.mockResolvedValueOnce(SQSS3Event({
      key: 'document-1'
    }))
    unprocessedDocuments.get.mockResolvedValueOnce(S3ObjectResponse({
      ContentLength: 1,
      Body: documentV2({body: 'document-1-body'})
    }))
    batchDocuments.put.mockResolvedValueOnce(true);
    unprocessedDocuments.delete.mockResolvedValueOnce(true);
    unprocessedDocumentsQueue.delete.mockRejectedValueOnce(new UnexpectedError());


    // I=6
    unprocessedDocumentsQueue.get.mockResolvedValueOnce(SQSS3Event({
      key: 'document-1'
    }));
    unprocessedDocuments.get.mockRejectedValueOnce(new NoSuchKey());
    unprocessedDocumentsQueue.delete.mockResolvedValueOnce(true);


    // I=7
    unprocessedDocumentsQueue.get.mockResolvedValueOnce(SQSS3Event({
      key: 'document-2'
    }))
    unprocessedDocuments.get.mockResolvedValueOnce(S3ObjectResponse({
      ContentLength: 2,
      Body: documentV2({body: 'document-2-body'})
    }))
    batchDocuments.put.mockResolvedValueOnce(true);
    unprocessedDocuments.delete.mockResolvedValueOnce(true);
    unprocessedDocumentsQueue.delete.mockResolvedValueOnce(true);
    // I=8
    unprocessedDocumentsQueue.get.mockResolvedValueOnce({
      ReceiptHandle: 'ReceiptHandleValue',
      Body: 'Invalid JSON string'
    })
    // I=9
    unprocessedDocumentsQueue.get.mockResolvedValueOnce({
      ReceiptHandle: 'ReceiptHandleValue',
      Body: JSON.stringify({
        Records: []
      })
    })
    // I=9
    unprocessedDocumentsQueue.get.mockResolvedValueOnce({
      ReceiptHandle: 'ReceiptHandleValue',
      Body: JSON.stringify({
        Records: [
          {
            eventName: 'ObjectCreated:Put',
            s3: {
              key: 'document-3',
              size: 3
            }
          },
          {
            eventName: 'ObjectCreated:Put',
            s3: {
              key: 'document-4',
              size: 4
            }
          }
        ]
      })
    })
    // I=10
    unprocessedDocumentsQueue.get.mockResolvedValueOnce({
      ReceiptHandle: 'ReceiptHandleValue',
      Body: JSON.stringify({
        Records: [
          {
            eventName: 'ObjectDeleted:Delete',
            s3: {
              key: 'document-3',
              size: 3
            }
          },
        ]
      })
    })
    // I > 10
    // to not hang with infinite loop performance issues
    unprocessedDocumentsQueue.get.mockImplementation(async function({WaitTimeSeconds}:{WaitTimeSeconds: number}){
      await new Promise(r=>setTimeout(r, WaitTimeSeconds));
      return null;
    });


    const batch = new Batch();
    const composeBatch = new ComposeIssueBatch({
      invalidDocuments: <InvalidDocuments><unknown>invalidDocuments,
      unprocessedDocuments: <UnprocessedDocuments><unknown>unprocessedDocuments,
      unprocessedDocumentsQueue: <UnprocessedDocumentsQueue><unknown>unprocessedDocumentsQueue,
      batchDocuments: <BatchDocuments><unknown>batchDocuments,
      batch,
      batchSizeBytes: 1024 * 1024 * 10,
      batchTimeSeconds: 20,
      attempts,
      attemptsIntervalSeconds: 1,
      messageWaitTime: 1,
      messageVisibilityTimeout: 60,
      wallet: <Wallet>wallet,
      documentStore: <DocumentStore>documentStore
    });
    await composeBatch.start();
  });
});
