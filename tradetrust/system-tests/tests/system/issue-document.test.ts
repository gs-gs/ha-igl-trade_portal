import _ from 'lodash';
import {
  getData,
  wrapDocument as wrapDocumentV2,
  __unsafe__use__it__at__your__own__risks__wrapDocument as wrapDocumentV3
} from '@govtechsg/open-attestation';
import * as ReposConfig from 'tests/config';
import { RetryableBucket } from 'tests/repos';
import { documentV2, documentV3 } from 'tests/data';

const TEST_PARAMS = [
  {
    version: '2.0',
    document: documentV2,
    setDocumentStoreAddress: (document:any, address: string)=>document.issuers[0].documentStore = address,
    Config: ReposConfig.V2_CONFIG,
    unwrap: getData,
    wrap: async (document: any)=>wrapDocumentV2(document)
  },
  {
    version: '3.0',
    document: documentV3,
    setDocumentStoreAddress: (document:any, address: string)=>document.openAttestationMetadata.proof.value = address,
    Config: ReposConfig.V3_CONFIG,
    unwrap: (document: any)=>{
      const copy = _.cloneDeep(document);
      delete copy.proof;
      return copy;
    },
    wrap: async (document:any)=>await wrapDocumentV3(document)
  }
]

describe.each(TEST_PARAMS)('Issue Document', ({
  version,
  document,
  setDocumentStoreAddress,
  Config,
  unwrap,
  wrap
})=>{
  describe(version, ()=>{
    test('Valid document', async ()=>{
      jest.setTimeout(300 * 1000);
      const unwrappedDocument = document();

      const unprocessed = new RetryableBucket({Bucket: Config.ISSUE_UNPROCESSED_BUCKET});
      const issued = new RetryableBucket({Bucket: Config.ISSUED_BUCKET});
      await unprocessed.clear();
      await issued.clear();

      const Body = JSON.stringify(unwrappedDocument);
      const Key = 'valid-document.json';

      await unprocessed.put({Body, Key});
      const wrappedDocumentObject = await issued.get({Attempts: 10, AttemptsInterval: 10, Key})
      expect(wrappedDocumentObject).toBeTruthy();
      const wrappedDocument = JSON.parse(wrappedDocumentObject!.Body!.toString());
      expect(unwrap(wrappedDocument)).toEqual(unwrappedDocument);
    });

    test('Invalid document', async ()=>{
      jest.setTimeout(300 * 1000);
      const unprocessed = new RetryableBucket({Bucket: Config.ISSUE_UNPROCESSED_BUCKET});
      const issued = new RetryableBucket({Bucket: Config.ISSUED_BUCKET});
      const invalid = new RetryableBucket({Bucket: Config.ISSUE_INVALID_BUCKET});
      await unprocessed.clear();
      await issued.clear();
      await invalid.clear();

      const documents = new Map<string, {Body: string, Reason: string}>();

      async function put(Key: string, Body: string, Reason: string){
        documents.set(Key, {Body, Reason});
        await unprocessed.put({Key, Body});
      }

      let Body, Key, Reason;

      Body = 'non json document';
      Key = 'non-json-document.json';
      Reason = 'Document body is not a valid JSON';

      await put(Key, Body, Reason);

      Body = JSON.stringify(await wrap(document() as any));
      Key = 'wrapped-document.json';
      Reason = 'Document is wrapped';

      await put(Key, Body, Reason);

      Body = document();
      setDocumentStoreAddress(Body, '0x0000000000000000000000000000000000000000');
      Body = JSON.stringify(Body);
      Key = 'invalid-document-store.json';
      Reason = 'Invalid document store address';

      await put(Key, Body, Reason);

      for([Key, {Body, Reason}] of documents.entries()){
        let object;

        object = await invalid.get({Attempts: 10, AttemptsInterval: 10, Key});
        expect(object).toBeTruthy();
        expect(object!.Body!.toString()).toEqual(Body);

        Key = Key.split('.')[0] + '.reason.json';
        object = await invalid.get({Attempts: 10, AttemptsInterval: 10, Key});
        expect(object).toBeTruthy();
        expect(JSON.parse(object!.Body!.toString()).reason).toMatch(Reason);
      }

    });

    test('Mix: valid & invalid documents', async ()=>{
      jest.setTimeout(300 * 1000);
      const unprocessed = new RetryableBucket({Bucket: Config.ISSUE_UNPROCESSED_BUCKET});
      const issued = new RetryableBucket({Bucket: Config.ISSUED_BUCKET});
      const invalid = new RetryableBucket({Bucket: Config.ISSUE_INVALID_BUCKET});
      await unprocessed.clear();
      await issued.clear();
      await invalid.clear();

      const documents = {
        valid: new Map<string, string>(),
        invalid: new Map<string, { Body: string, Reason: string}>()
      }

      const put = {
        async valid(Key: string, Body: string){
          await unprocessed.put({Key, Body});
          documents.valid.set(Key, Body);
        },
        async invalid(Key: string, Body: string, Reason: string){
          await unprocessed.put({Key, Body});
          documents.invalid.set(Key, {Body, Reason});
        }
      }

      let Body, Key, Reason;

      Body = 'non json document';
      Key = 'non-json-document.json';
      Reason = 'Document body is not a valid JSON';

      await put.invalid(Key, Body, Reason);

      Body = JSON.stringify(await wrap(document() as any));
      Key = 'wrapped-document.json';
      Reason = 'Document is wrapped';

      await put.invalid(Key, Body, Reason);

      Body = document() as any;
      Body = JSON.stringify(Body);
      Key = 'valid-document-0.json';

      await put.valid(Key, Body);

      Body = document();
      setDocumentStoreAddress(Body, '0x0000000000000000000000000000000000000000');
      Body = JSON.stringify(Body);
      Key = 'invalid-document-store.json';
      Reason = 'Invalid document store address';

      await put.invalid(Key, Body, Reason);

      Body = document() as any;
      Body = JSON.stringify(Body);
      Key = 'valid-document-1.json';

      await put.valid(Key, Body);


      for(let [Key, Body] of documents.valid.entries()){
        const object = await issued.get({Attempts: 10, AttemptsInterval: 10, Key})
        expect(object).toBeTruthy();
        const wrappedDocument = JSON.parse(object!.Body!.toString());
        expect(unwrap(wrappedDocument)).toEqual(JSON.parse(Body));
      }

      for([Key, {Body, Reason}] of documents.invalid.entries()){
        let object;

        object = await invalid.get({Attempts: 10, AttemptsInterval: 10, Key});
        expect(object).toBeTruthy();
        expect(object!.Body!.toString()).toEqual(Body);

        Key = Key.split('.')[0] + '.reason.json';
        object = await invalid.get({Attempts: 10, AttemptsInterval: 10, Key});
        expect(object).toBeTruthy();
        expect(JSON.parse(object!.Body!.toString()).reason).toMatch(Reason);
      }

    });
  });

})
