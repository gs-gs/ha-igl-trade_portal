import _ from 'lodash';
import {
  getData,
  wrapDocument as wrapDocumentV2,
  __unsafe__use__it__at__your__own__risks__wrapDocument as wrapDocumentV3
} from '@govtechsg/open-attestation';
import { documentV2, documentV3 } from 'tests/data';
import { RetryableBucket } from 'tests/repos';
import * as ReposConfig from 'tests/config';


async function getBuckets(config: any){
  const bucket = {
    revoke: {
      invalid: new RetryableBucket({Bucket: config.REVOKE_INVALID_BUCKET}),
      revoked: new RetryableBucket({Bucket: config.REVOKED_BUCKET}),
      unprocessed: new RetryableBucket({Bucket: config.REVOKE_UNPROCESSED_BUCKET})
    },
    issue: {
      invalid: new RetryableBucket({Bucket: config.ISSUE_UNPROCESSED_BUCKET}),
      issued: new RetryableBucket({Bucket: config.ISSUED_BUCKET}),
      unprocessed: new RetryableBucket({Bucket: config.ISSUE_UNPROCESSED_BUCKET})
    }
  }

  await bucket.revoke.invalid.clear();
  await bucket.revoke.revoked.clear();
  await bucket.revoke.unprocessed.clear();

  await bucket.issue.invalid.clear();
  await bucket.issue.issued.clear();
  await bucket.issue.unprocessed.clear();

  return bucket;
}

const TEST_PARAMS = [
  {
    version: '2.0',
    generateDocument: documentV2,
    setDocumentStoreAddress: (document:any, address: string)=>document.issuers[0].documentStore = address,
    Config: ReposConfig.V2_CONFIG,
    unwrap: getData,
    wrap: async (document: any)=>wrapDocumentV2(document)
  },
  {
    version: '3.0',
    generateDocument: documentV3,
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

describe.each(TEST_PARAMS)('Revoke Document', ({
  version,
  generateDocument,
  setDocumentStoreAddress,
  Config,
  unwrap,
  wrap
})=>{
  describe(version, ()=>{
    test('Valid document', async ()=>{
      jest.setTimeout(300 * 1000);
      const bucket = await getBuckets(Config);
      // STEP 1. Issue document
      const document:any = {
        unwrapped: undefined,
        wrapped: undefined,
        revoked: undefined
      };

      document.unwrapped = generateDocument();

      let Key, Body;
      Key = 'valid-document.json';
      Body = JSON.stringify(document.unwrapped);
      await bucket.issue.unprocessed.put({Key, Body});

      // STEP 2. Getting issued document,  checking data correctness.
      document.wrapped = await bucket.issue.issued.get({Attempts: 10, AttemptsInterval: 10, Key});
      expect(document.wrapped).toBeTruthy();
      document.wrapped = JSON.parse(document.wrapped.Body.toString());
      expect(document.unwrapped).toEqual(unwrap(document.wrapped));

      // STEP 3. Revoking document
      Key = 'valid-document.json'
      Body = JSON.stringify(document.wrapped);
      await bucket.revoke.unprocessed.put({Key, Body});

      // STEP 4. Getting revoked document, checking data correctness.
      document.revoked = await bucket.revoke.revoked.get({Attempts: 10, AttemptsInterval: 10, Key});
      expect(document.revoked).toBeTruthy();
      document.revoked = JSON.parse(document.revoked.Body.toString());
      expect(document.unwrapped).toEqual(unwrap(document.revoked));
      expect(document.wrapped).toEqual(document.revoked);

    });

    test('Invalid document', async ()=>{
      jest.setTimeout(300 * 1000);
      const bucket = await getBuckets(Config);

      const documents = new Map<string, {Body: string, Reason: string}>();
      const document:any = {
        unwrapped: generateDocument(),
        wrapped: undefined,
        revoked: undefined
      };

      const put = {
        revoke: {
          valid: async function (Key: string, Body: string){
            await bucket.revoke.unprocessed.put({Key, Body});
          },
          invalid: async function(Key: string, Body: string, Reason: string){
            await bucket.revoke.unprocessed.put({Key, Body});
            documents.set(Key, {Body, Reason});
          }
        }
      }
      // STEP 1. Issue document
      let Key, Body, Reason;
      Key = 'valid-document.json';
      Body = JSON.stringify(document.unwrapped);
      await bucket.issue.unprocessed.put({Key, Body});

      // STEP 2. Getting issued document
      document.wrapped = await bucket.issue.issued.get({Attempts: 10, AttemptsInterval: 10, Key});
      expect(document.wrapped).toBeTruthy();
      document.wrapped = JSON.parse(document.wrapped.Body.toString());

      // STEP 3. Revoking document
      Key = 'valid-document.json'
      Body = JSON.stringify(document.wrapped);
      await put.revoke.valid(Key, Body);

      // STEP 4. Getting revoked document
      document.revoked = await bucket.revoke.revoked.get({Attempts: 10, AttemptsInterval: 10, Key});
      expect(document.revoked).toBeTruthy();
      document.revoked = JSON.parse(document.revoked.Body.toString());

      // STEP 5. Trying to revoke the document again
      Key = 'revoked-document.json'
      Body = JSON.stringify(document.revoked);
      Reason = 'already revoked';
      await put.revoke.invalid(Key, Body, Reason);

      // STEP 6. Trying to revoke non json document
      Key = 'non-json-document'
      Body = 'non-json-document-body'
      Reason = 'Document body is not a valid JSON';
      await put.revoke.invalid(Key, Body, Reason);

      // STEP 7. Trying to revoke document with an invalid schema
      Key = 'unwrapped-document.json'
      Body = JSON.stringify(document.unwrapped);
      Reason = 'Document not wrapped';
      await put.revoke.invalid(Key, Body, Reason);

      // STEP 8. Trying to revoke document with an invalid document store address
      Body = generateDocument();
      setDocumentStoreAddress(Body, '0x0000000000000000000000000000000000000000');
      Body = JSON.stringify(await wrap(Body as any));
      Key = 'invalid-document-store.json';
      Reason = 'Invalid document store address';
      await put.revoke.invalid(Key, Body, Reason);

      for([Key, {Body, Reason}] of documents.entries()){
        let object;

        object = await bucket.revoke.invalid.get({Attempts: 10, AttemptsInterval: 10, Key});
        expect(object).toBeTruthy();
        expect(object!.Body!.toString()).toEqual(Body);

        Key = Key.split('.')[0] + '.reason.json';
        object = await bucket.revoke.invalid.get({Attempts: 10, AttemptsInterval: 10, Key});
        expect(object).toBeTruthy();
        expect(JSON.parse(object!.Body!.toString()).reason).toMatch(Reason);
      }
    });

    test('Mix: valid & invalid documents', async ()=>{
      jest.setTimeout(300 * 1000);
      const bucket = await getBuckets(Config);
      const documents = {
        issued: {
          valid: new Map<string, string>(),
          issued: new Map<string, string>(),
        },
        revoked: {
          valid: new Map<string, string>(),
          invalid: new Map<string, {Body: string, Reason: string}>()
        }
      };
      const put = {
        issue:{
          valid: async function(Key: string, Body:string){
            await bucket.issue.unprocessed.put({Key, Body});
            documents.issued.valid.set(Key, Body);
          }
        },
        revoke: {
          valid: async function (Key: string, Body: string){
            await bucket.revoke.unprocessed.put({Key, Body});
            documents.revoked.valid.set(Key, Body);
          },
          invalid: async function(Key: string, Body: string, Reason: string){
            await bucket.revoke.unprocessed.put({Key, Body});
            documents.revoked.invalid.set(Key, {Body, Reason});
          }
        }
      };

      let Key, Body, Reason, Confirmation;
      // STEP 1. Issuing documents
      Key = 'issued-document-1.json';
      Body = generateDocument() as any;
      Body = JSON.stringify(Body);
      await put.issue.valid(Key, Body);
      Confirmation = await bucket.issue.issued.get({Attempts:10, AttemptsInterval: 10, Key});
      expect(Confirmation).toBeTruthy();
      documents.issued.issued.set(Key, Confirmation!.Body!.toString());


      Key = 'issued-document-2.json';
      Body = generateDocument() as any;
      Body = JSON.stringify(Body);
      await put.issue.valid(Key, Body);
      Confirmation = await bucket.issue.issued.get({Attempts:10, AttemptsInterval: 10, Key});
      expect(Confirmation).toBeTruthy();
      documents.issued.issued.set(Key, Confirmation!.Body!.toString());

      // STEP 2. Revoking invalid document
      Key = 'non-json-document-1'
      Body = 'non-json-document-body'
      Reason = 'Document body is not a valid JSON';
      await put.revoke.invalid(Key, Body, Reason);

      // STEP 3. Revoking valid document
      Key = 'issued-document-1.json'
      Body = documents.issued.issued.get(Key);
      await put.revoke.valid(Key, Body!);
      Confirmation = await bucket.revoke.revoked.get({Attempts: 10, AttemptsInterval: 10, Key});
      expect(Confirmation).toBeTruthy();

      // STEP 4. Revoke invalid document
      Key = 'revoked-document-1.json'
      Reason = 'already revoked'
      await put.revoke.invalid(Key, Body!, Reason);

      // STEP 5. Revoke invalid document
      Key = 'non-json-document-2'
      Body = 'non-json-document-body'
      Reason = 'Document body is not a valid JSON';
      await put.revoke.invalid(Key, Body, Reason);

      // STEP 6. Revoke valid document
      Key = 'issued-document-2.json'
      Body = documents.issued.issued.get(Key);
      await put.revoke.valid(Key, Body!);
      Confirmation = await bucket.revoke.revoked.get({Attempts: 10, AttemptsInterval: 10, Key});
      expect(Confirmation).toBeTruthy();

      // STEP 7. Revoke invalid document
      Key = 'revoked-document-2.json'
      Reason = 'already revoked'
      await put.revoke.invalid(Key, Body!, Reason);

      for([Key, Body] of documents.revoked.valid.entries()){
        let object;

        object = await bucket.revoke.revoked.get({Attempts: 10, AttemptsInterval: 10, Key});
        expect(object).toBeTruthy();
        expect(object!.Body!.toString()).toEqual(Body);
      }


      for([Key, {Body, Reason}] of documents.revoked.invalid.entries()){
        let object;

        object = await bucket.revoke.invalid.get({Attempts: 10, AttemptsInterval: 10, Key});
        expect(object).toBeTruthy();
        expect(object!.Body!.toString()).toEqual(Body);

        Key = Key.split('.')[0] + '.reason.json';
        object = await bucket.revoke.invalid.get({Attempts: 10, AttemptsInterval: 10, Key});
        expect(object).toBeTruthy();
        expect(JSON.parse(object!.Body!.toString()).reason).toMatch(Reason);
      }
    })
  });
});
