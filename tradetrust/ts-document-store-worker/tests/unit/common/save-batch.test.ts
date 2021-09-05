import { IssuedDocuments, BatchDocuments } from 'src/repos';
import { Batch } from 'src/tasks/common/data';
import { SaveBatch } from 'src/tasks/common/save-batch';


class UnexpectedError extends Error{
  constructor(){
    super('Unexpected Error')
  }
}

class NoSuchKey extends Error{
  public code: string = 'NoSuchKey'
}


describe.only('SaveIssuedBatch task unit tests', ()=>{

  const createIssuedDocumentsRepoMock = ()=>{
    return {
      put: jest.fn()
    }
  }

  const createBatchDocumentsRepoMock = ()=>{
    return {
      delete: jest.fn()
    }
  }

  test('test retry errors', async ()=>{
    const issuedDocuments = createIssuedDocumentsRepoMock();
    const batchDocuments = createBatchDocumentsRepoMock();

    const batch = new Batch();

    batch.wrappedDocuments.set('document-1', {body: 'document-1-body', size: 0});
    batch.wrappedDocuments.set('document-2', {body: 'document-2-body', size: 0});


    issuedDocuments.put.mockReset();
    batchDocuments.delete.mockReset();

    // I=1 key=document-1
    issuedDocuments.put.mockRejectedValueOnce(new UnexpectedError());
    // I=2 key=document-1
    issuedDocuments.put.mockResolvedValueOnce(true);
    batchDocuments.delete.mockRejectedValueOnce(new UnexpectedError());
    // I=3 key=document-1
    issuedDocuments.put.mockResolvedValueOnce(true);
    batchDocuments.delete.mockResolvedValueOnce(true);
    // I=4 key=document-2
    issuedDocuments.put.mockResolvedValueOnce(true)
    batchDocuments.delete.mockRejectedValueOnce(new NoSuchKey());

    const saveIssuedBatch = new SaveBatch({
      processedDocuments: <IssuedDocuments><unknown>issuedDocuments,
      batchDocuments: <BatchDocuments><unknown>batchDocuments,
      batch,
      attempts: 10,
      attemptsIntervalSeconds: 1
    });
    await saveIssuedBatch.start();
    expect(issuedDocuments.put.mock.calls.length).toBe(3);
    expect(batchDocuments.delete.mock.calls.length).toBe(3);
    // I=1
    expect(issuedDocuments.put.mock.calls[0][0].Key).toBe('document-1');
    // I=2
    expect(issuedDocuments.put.mock.calls[1][0].Key).toBe('document-1');
    expect(batchDocuments.delete.mock.calls[0][0].Key).toBe('document-1');
    // I=3
    expect(batchDocuments.delete.mock.calls[1][0].Key).toBe('document-1');
    // I=4
    expect(issuedDocuments.put.mock.calls[2][0].Key).toBe('document-2');
    expect(batchDocuments.delete.mock.calls[2][0].Key).toBe('document-2');
  });

  test('test ran out of attempts', async ()=>{
    const attempts = 5;
    const issuedDocuments = createIssuedDocumentsRepoMock();
    const batchDocuments = createBatchDocumentsRepoMock();

    const batch = new Batch();

    batch.wrappedDocuments.set('document-1', {body: 'document-1-body', size: 0});
    batch.wrappedDocuments.set('document-2', {body: 'document-2-body', size: 0});


    issuedDocuments.put.mockReset();
    batchDocuments.delete.mockReset();
    issuedDocuments.put.mockRejectedValue(new UnexpectedError());

    const saveIssuedBatch = new SaveBatch({
      processedDocuments: <IssuedDocuments><unknown>issuedDocuments,
      batchDocuments: <BatchDocuments><unknown>batchDocuments,
      batch,
      attempts,
      attemptsIntervalSeconds: 1
    });
    try{
      await saveIssuedBatch.start();
    }catch(e){
      expect(e instanceof UnexpectedError).toBe(true);
      expect(issuedDocuments.put.mock.calls.length).toBe(attempts);
      expect(batchDocuments.delete.mock.calls.length).toBe(0);
    }

  });

})
