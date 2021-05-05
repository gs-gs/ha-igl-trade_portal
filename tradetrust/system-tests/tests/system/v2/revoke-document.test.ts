import { getData, wrapDocument } from '@govtechsg/open-attestation';
import { documentV2 } from 'tests/data';
import { RetryableBucket } from 'tests/repos';
import * as Config from 'tests/config';


async function getBuckets(){
  const bucket = {
    revoke: {
      invalid: new RetryableBucket({Bucket: Config.REVOKE_INVALID_BUCKET}),
      revoked: new RetryableBucket({Bucket: Config.REVOKED_BUCKET}),
      unprocessed: new RetryableBucket({Bucket: Config.REVOKE_UNPROCESSED_BUCKET})
    },
    issue: {
      invalid: new RetryableBucket({Bucket: Config.ISSUE_UNPROCESSED_BUCKET}),
      issued: new RetryableBucket({Bucket: Config.ISSUED_BUCKET}),
      unprocessed: new RetryableBucket({Bucket: Config.ISSUE_UNPROCESSED_BUCKET})
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

describe('Revoke Document V2', ()=>{
  test('Valid document', async ()=>{
    jest.setTimeout(300 * 1000);
    const bucket = await getBuckets();
    // STEP 1. Issue document
    const document:any = {
      unwrapped: undefined,
      wrapped: undefined,
      revoked: undefined
    };

    document.unwrapped = documentV2();

    let Key, Body;
    Key = 'valid-document.json';
    Body = JSON.stringify(document.unwrapped);
    await bucket.issue.unprocessed.put({Key, Body});

    // STEP 2. Getting issued document,  checking data correctness.
    document.wrapped = await bucket.issue.issued.get({Attempts: 10, AttemptsInterval: 10, Key});
    expect(document.wrapped).toBeTruthy();
    document.wrapped = JSON.parse(document.wrapped.Body.toString());
    expect(document.unwrapped).toEqual(getData(document.wrapped));

    // STEP 3. Revoking document
    Key = 'valid-document.json'
    Body = JSON.stringify(document.wrapped);
    await bucket.revoke.unprocessed.put({Key, Body});

    // STEP 4. Getting revoked document, checking data correctness.
    document.revoked = await bucket.revoke.revoked.get({Attempts: 10, AttemptsInterval: 10, Key});
    expect(document.revoked).toBeTruthy();
    document.revoked = JSON.parse(document.revoked.Body.toString());
    expect(document.unwrapped).toEqual(getData(document.revoked));
    expect(document.wrapped).toEqual(document.revoked);

  });

  test('Invalid document', async ()=>{
    jest.setTimeout(300 * 1000);
    const bucket = await getBuckets();

    const documents = new Map<string, {Body: string, Reason: string}>();
    const document:any = {
      unwrapped: documentV2(),
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
    Reason = 'Invalid document schema';
    await put.revoke.invalid(Key, Body, Reason);

    // STEP 8. Trying to revoke document with an invalid document store address
    Body = documentV2();
    Body.issuers[0].documentStore = '0x0000000000000000000000000000000000000000';
    Body = JSON.stringify(wrapDocument(Body as any));
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

  test.only('Mix: valid & invalid documents', async ()=>{
    jest.setTimeout(300 * 1000);
    const bucket = await getBuckets();
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
    Body = documentV2() as any;
    Body.data = 'issued-document-data-1';
    Body = JSON.stringify(Body);
    await put.issue.valid(Key, Body);
    Confirmation = await bucket.issue.issued.get({Attempts:10, AttemptsInterval: 10, Key});
    expect(Confirmation).toBeTruthy();
    documents.issued.issued.set(Key, Confirmation!.Body!.toString());


    Key = 'issued-document-2.json';
    Body = documentV2() as any;
    Body.data = 'issued-document-data-2';
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
