import { IssuedDocuments, BatchDocuments } from 'src/repos';
import { SaveIssuedBatch, Batch } from 'src/tasks';


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

  test('test errors', async ()=>{
    const issuedDocuments = createIssuedDocumentsRepoMock();
    const batchDocuments = createBatchDocumentsRepoMock();
    class NoSuchKey extends Error{
      public code: string = 'NoSuchKey'
    }

    batchDocuments.delete.mockReset();
    (
      batchDocuments.delete
      .mockResolvedValueOnce(true)
      .mockResolvedValueOnce(true)
      .mockRejectedValueOnce('batchDocuments.delete unexpected error')
      .mockResolvedValueOnce(true)
      .mockRejectedValueOnce(new NoSuchKey())
      .mockResolvedValueOnce(true)
      .mockResolvedValueOnce(true)
    )
    issuedDocuments.put.mockReset();
    (
      issuedDocuments.put
      .mockResolvedValueOnce(true)
      .mockResolvedValueOnce(true)
      .mockResolvedValueOnce(true)
      .mockRejectedValueOnce(new Error('issuedDocuments.put unexpected error'))
      .mockResolvedValueOnce(true)
      .mockResolvedValueOnce(true)
    )
    const batch = new Batch();
    for(let i = 0; i < 5; i++){
      const key = `document-key-${i}`
      const body = { body: `document-body-${i}` }
      batch.wrappedDocuments.set(key, body);
    }
    const saveIssuedBatch = new SaveIssuedBatch({
      issuedDocuments: <IssuedDocuments><unknown>issuedDocuments,
      batchDocuments: <BatchDocuments><unknown>batchDocuments,
      batch,
      attempts: 10,
      attemptsIntervalSeconds: 1
    });
    await saveIssuedBatch.start();
    // each document saved/deleted only once, calls.length = 5 documents + 1 unexpected error
    // NoSuchKey error treated as succesful deletion but with a warning message
    expect(batchDocuments.delete.mock.calls.length).toBe(6);
    expect(issuedDocuments.put.mock.calls.length).toBe(6);
    // workflow check
    expect(issuedDocuments.put.mock.calls[0][0].Key).toEqual('document-key-0');
    expect(batchDocuments.delete.mock.calls[0][0]).toEqual({Key: 'document-key-0'});

    expect(issuedDocuments.put.mock.calls[1][0].Key).toEqual('document-key-1');
    expect(batchDocuments.delete.mock.calls[1][0]).toEqual({Key: 'document-key-1'});

    // unexpected delete error
    expect(issuedDocuments.put.mock.calls[2][0].Key).toEqual('document-key-2');
    expect(batchDocuments.delete.mock.calls[2][0]).toEqual({Key: 'document-key-2'});

    // repeat previos failed operation
    expect(batchDocuments.delete.mock.calls[3][0]).toEqual({Key: 'document-key-2'});

    // unexpeced saving error, delete not called
    expect(issuedDocuments.put.mock.calls[3][0].Key).toEqual('document-key-3');

    // repeat previos failed operation
    expect(issuedDocuments.put.mock.calls[4][0].Key).toEqual('document-key-3');
    expect(batchDocuments.delete.mock.calls[4][0]).toEqual({Key: 'document-key-3'});

    expect(issuedDocuments.put.mock.calls[5][0].Key).toEqual('document-key-4');
    expect(batchDocuments.delete.mock.calls[5][0]).toEqual({Key: 'document-key-4'});
  });
})
