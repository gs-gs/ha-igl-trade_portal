import { getData, wrapDocument } from '@govtechsg/open-attestation';
import * as Config from 'tests/config';
import { RetryableBucket } from 'tests/repos';
import { documentV2 } from 'tests/data';

describe('Issue Document V2', ()=>{
  test('Valid document', async ()=>{
    jest.setTimeout(300 * 1000);
    const unwrappedDocument = documentV2();

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
    expect(getData(wrappedDocument)).toEqual(unwrappedDocument);
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

    Body = JSON.stringify(wrapDocument(documentV2() as any));
    Key = 'wrapped-document.json';
    Reason = 'Invalid document schema';

    await put(Key, Body, Reason);

    Body = documentV2();
    Body.issuers[0].documentStore = '0x0000000000000000000000000000000000000000';
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

    Body = JSON.stringify(wrapDocument(documentV2() as any));
    Key = 'wrapped-document.json';
    Reason = 'Invalid document schema';

    await put.invalid(Key, Body, Reason);

    Body = documentV2() as any;
    Body.DocumentData = 'document-data-0';
    Body = JSON.stringify(Body);
    Key = 'valid-document-0.json';

    await put.valid(Key, Body);

    Body = documentV2();
    Body.issuers[0].documentStore = '0x0000000000000000000000000000000000000000';
    Body = JSON.stringify(Body);
    Key = 'invalid-document-store.json';
    Reason = 'Invalid document store address';

    await put.invalid(Key, Body, Reason);

    Body = documentV2() as any;
    Body.DocumentData = 'document-data-1';
    Body = JSON.stringify(Body);
    Key = 'valid-document-1.json';

    await put.valid(Key, Body);


    for(let [Key, Body] of documents.valid.entries()){
      const object = await issued.get({Attempts: 10, AttemptsInterval: 10, Key})
      expect(object).toBeTruthy();
      const wrappedDocument = JSON.parse(object!.Body!.toString());
      expect(getData(wrappedDocument)).toEqual(JSON.parse(Body));
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
