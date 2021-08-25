import { getData } from '@govtechsg/open-attestation';
import { Batch } from 'src/tasks/common/data';
import WrapBatch from 'src/tasks/v2/wrap-batch';
import { documentV2 } from 'tests/utils';


describe('WrapBatch Task', ()=>{

  jest.setTimeout(1000 * 100);

  test('wrap batch', ()=>{
    const batch = new Batch();
    for(let documentIndex = 0; documentIndex < 10; documentIndex++){
      const key = `document-${documentIndex}`
      const body = `document-body-${documentIndex}`;
      const entry = {
        size: 512,
        body: documentV2({body})
      }
      batch.unwrappedDocuments.set(key, entry);
    }
    const wrapBatch = new WrapBatch({batch});
    wrapBatch.start();
    expect(Array.from<string>(batch.wrappedDocuments.keys())).toEqual(Array.from<string>(batch.unwrappedDocuments.keys()))
    for(let [key, wrappedDocument] of batch.wrappedDocuments){
      expect(getData(wrappedDocument.body)).toEqual(batch.unwrappedDocuments.get(key)?.body);
      expect(wrappedDocument.body.signature.merkleRoot).toEqual(batch.merkleRoot);
    }
  })
});
