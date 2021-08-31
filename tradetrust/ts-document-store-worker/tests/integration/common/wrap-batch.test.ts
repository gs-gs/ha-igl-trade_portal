import _ from 'lodash';
import { getData, utils } from '@govtechsg/open-attestation';
import { OpenAttestationVersion as Version } from 'src/constants';
import { Batch } from 'src/tasks/common/data';
import { WrapBatch } from 'src/tasks/common/wrap-batch';
import {
    generateDocumentsMapV2,
    generateDocumentsMapV3
} from 'tests/utils';


describe('WrapBatch Task', ()=>{

  beforeEach(()=>{
    jest.setTimeout(1000 * 60);
  })

  const TEST_PARAMS = [
    {
      version: Version.V2,
      generateDocumentsMap: generateDocumentsMapV2,
      unwrap: (document: any)=>getData(document),
      isWrapped: (document: any)=>utils.isWrappedV2Document(document),
      getSignature: (document: any)=>document.signature.merkleRoot
    },
    {
      version: Version.V3,
      generateDocumentsMap: generateDocumentsMapV3,
      unwrap: (document: any)=>{
        document = _.cloneDeep(document);
        delete document.proof;
        return document;
      },
      isWrapped: (document:any)=>utils.isWrappedV3Document(document),
      getSignature: (document: any)=>document.proof.merkleRoot
    }
  ]

  describe.each(TEST_PARAMS)('Wrap', ({
    version,
    generateDocumentsMap,
    unwrap,
    isWrapped,
    getSignature
  })=>{
    test(version, async ()=>{
      const batch = new Batch();
      const documents = generateDocumentsMap(10);
      documents.forEach((v,k)=>batch.unwrappedDocuments.set(k, {size: 1, body: v}));
      const wrapBatch = new WrapBatch({
        version,
        batch
      });
      await wrapBatch.start();
      for(let [key, document] of documents){
        const wrappedDocumentEntry = batch.wrappedDocuments.get(key);
        const wrappedDocument = wrappedDocumentEntry?.body;
        // check that key exists
        expect(wrappedDocumentEntry).toBeTruthy();
        // check wrapped state usign typeguard
        expect(isWrapped(wrappedDocument)).toBeTruthy();
        // check data integrity
        expect(unwrap(wrappedDocument)).toEqual(document);
        expect(getSignature(wrappedDocument)).toEqual(batch.merkleRoot);
      }
    })
  })
});
