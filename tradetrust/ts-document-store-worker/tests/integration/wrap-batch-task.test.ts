import { getData } from '@govtechsg/open-attestation';
import { WrapBatch, Batch } from 'src/tasks';
import { documentV2 } from 'tests/utils';


describe('WrapBatch Task', ()=>{
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
    const wrapBatch = new WrapBatch(batch);
    wrapBatch.start();
    expect(Array.from<string>(batch.wrappedDocuments.keys())).toEqual(Array.from<string>(batch.unwrappedDocuments.keys()))
    for(let [key, wrappedDocument] of batch.wrappedDocuments){
      expect(getData(wrappedDocument)).toEqual(batch.unwrappedDocuments.get(key)?.body);
      expect(wrappedDocument.signature.merkleRoot).toEqual(batch.merkleRoot);
    }
  })
});
