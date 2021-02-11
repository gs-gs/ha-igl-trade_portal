import { BatchDocuments } from 'src/repos';
import { RestoreBatch, Batch } from 'src/tasks';

class NoSuchKey extends Error{
  public code: string = 'NoSuchKey'
}

describe('RestoreBatch task unit tests',()=>{

  const createBatchDocumentsRepoMock = ()=>{
    return {
      list: jest.fn(),
      get: jest.fn()
    }
  }

  test('test retry mechanism', async ()=>{
    const batchDocuments = createBatchDocumentsRepoMock();
    batchDocuments.list
    .mockRejectedValueOnce(new Error('Unexpected Error'))
    .mockResolvedValue({
      Contents: [
        {
          Key: 'key-1',
          Size: 1
        },
        {
          Key: 'key-2',
          Size: 2,
        },
        {
          Key: 'key-3',
          Size: 3
        },
        {
          Key: 'key-4',
          Size: 4
        },
        {
          Key: 'key-5',
          Size: 5
        }
      ],
      ContinuationToken: undefined
    });
    batchDocuments.get
    .mockResolvedValueOnce({
      Body: JSON.stringify({body: 'document-body-1'})
    })
    .mockRejectedValueOnce(new Error('Unexpected Error'))
    .mockResolvedValueOnce({
      Body: JSON.stringify({body: 'document-body-2'})
    })
    .mockResolvedValueOnce({
      Body: JSON.stringify({body: 'document-body-3'})
    })
    .mockRejectedValueOnce(new NoSuchKey())
    .mockResolvedValueOnce({
      Body: 'not a valid json;;;ttt'
    });
    const batch = new Batch();
    const restoreBatch = new RestoreBatch({
      batch,
      batchDocuments: <BatchDocuments><unknown>batchDocuments,
      batchSizeBytes: 1024 * 1024 * 10,
      batchTimeSeconds: 10,
      attempts: 10,
      attemptsIntervalSeconds: 1,
    });
    await restoreBatch.start();
    const expectedDocuments = new Map<string, any>();
    expectedDocuments.set('key-1', {size: 1, body: {body: 'document-body-1'}});
    expectedDocuments.set('key-2', {size: 2, body: {body: 'document-body-2'}});
    expectedDocuments.set('key-3', {size: 3, body: {body: 'document-body-3'}});
    expect(batch.unwrappedDocuments.size).toBe(expectedDocuments.size);
    expect(batch.unwrappedDocuments).toEqual(expectedDocuments);
    // calls count including all retry attemps
    expect(batchDocuments.list.mock.calls.length).toBe(3);
    // one document was deleted before RestoreBatch task was able to add into a batch
    // one document wans't a valid json
    // one document throwed an unexpected error
    expect(batchDocuments.get.mock.calls.length).toBe(6);
  });

  test('ran out of attempts', async ()=>{
    const attempts = 3;
    const batchDocuments = createBatchDocumentsRepoMock();
    batchDocuments.list.mockRejectedValue(new Error('Unexpected Error'));
    const batch = new Batch();
    const restoreBatch = new RestoreBatch({
      batch,
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
