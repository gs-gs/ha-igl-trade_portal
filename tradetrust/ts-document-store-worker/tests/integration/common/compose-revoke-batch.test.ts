import {
  wrapDocument as wrapDocumentV2,
  __unsafe__use__it__at__your__own__risks__wrapDocument as wrapDocumentV3
} from '@govtechsg/open-attestation';
import _ from 'lodash';
import { OpenAttestationVersion as Version } from 'src/constants';
import { getBatchedRevokeEnvConfig } from 'src/config';
import { connectWallet, connectDocumentStore } from 'src/document-store';
import { Batch } from 'src/tasks/common/data';
import { ComposeRevokeBatch } from 'src/tasks/common/compose-revoke-batch';
import {
  InvalidDocuments,
  UnprocessedDocuments,
  BatchDocuments,
  UnprocessedDocumentsQueue
} from 'src/repos';
import {
  clearQueue,
  clearBucket,
  documentV2,
  documentV3,
  generateDocumentsMapV2,
  generateDocumentsMapV3,
  createInvalidDocumentReasonAssert
} from 'tests/utils';


describe('ComposeRevokeBatch Task', ()=>{

  const config = getBatchedRevokeEnvConfig();
  const unprocessedDocuments = new UnprocessedDocuments(config);
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue(config);
  const batchDocuments = new BatchDocuments(config);
  const invalidDocuments = new InvalidDocuments(config);

  beforeEach(async ()=>{
    await clearQueue(config.UNPROCESSED_QUEUE_URL);
    await clearBucket(config.UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.BATCH_BUCKET_NAME);
    jest.setTimeout(60 * 1000);
  }, 1000 * 60);

  const SINGLE_DOCUMENT_BATCH_TEST_PARAMS = [
    {
      version: Version.V2,
      generateDocumentsMap: generateDocumentsMapV2,
      wrapDocument: async (document:any)=>wrapDocumentV2(document)
    },
    {
      version: Version.V3,
      generateDocumentsMap: generateDocumentsMapV3,
      wrapDocument: async (document:any)=>{return await wrapDocumentV3(document)}
    }
  ];

  describe.each(SINGLE_DOCUMENT_BATCH_TEST_PARAMS)('Single document batch', ({
    version,
    generateDocumentsMap,
    wrapDocument
  })=>{
    test(version, async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);
      const unwrappedDocumentsMap = generateDocumentsMap(5);
      const wrappedDocumentsMap = new Map<string, any>();
      for(let [key, body] of unwrappedDocumentsMap){
        body = await wrapDocument(body);
        wrappedDocumentsMap.set(key, body);
        await unprocessedDocuments.put({Key: key, Body: JSON.stringify(body)});
      }
      const batch = new Batch();
      const composeRevokeBatch = new ComposeRevokeBatch({
        version,
        wallet,
        documentStore,
        batchDocuments,
        unprocessedDocuments,
        unprocessedDocumentsQueue,
        invalidDocuments,
        messageWaitTime: 10,
        messageVisibilityTimeout: 10,
        batchSizeBytes: 1,
        batchTimeSeconds: 10,
        attempts: 1,
        attemptsIntervalSeconds: 60,
        batch
      });
      await composeRevokeBatch.start();
    });
  });


  const INVALID_DOCUMENTS_HANDLING_TEST_PARAMS = [
    {
      version: Version.V2,
      document: documentV2,
      getDocumentSignature: (document:any)=>document.signature.targetHash,
      wrapDocument: async (document:any)=>wrapDocumentV2(document),
      invalidDocumentStoreAddress: '0x0000000000000000000000000000000000000000',
      invalidDocumentStoreAddressOverride: {
        issuers:[
          {
            name: 'DEMO STORE',
            documentStore: '0x0000000000000000000000000000000000000000',
            identityProof: {
              type: 'DNS-TXT',
              location: 'tradetrust.io'
            }
          }
        ]
      },
      invalidDocumentSignatureOverride: {
        signature:{
          targetHash: '0x0000000000000000000000000000000000000000'
        }
      }
    },
    {
      version: Version.V3,
      document: documentV3,
      getDocumentSignature: (document:any)=>document.proof.targetHash,
      wrapDocument: async (document:any)=>{return await wrapDocumentV3(document)},
      invalidDocumentStoreAddress: '0x0000000000000000000000000000000000000000',
      invalidDocumentStoreAddressOverride: {
        openAttestationMetadata:{
          proof:{
            value: 'did:ethr:0x0000000000000000000000000000000000000000'
          }
        }
      },
      invalidDocumentSignatureOverride: {
        proof:{
          targetHash: '0x0000000000000000000000000000000000000000'
        }
      }
    }
  ];

  describe.each(INVALID_DOCUMENTS_HANDLING_TEST_PARAMS)('Invalid documents handling', ({
    version,
    document,
    invalidDocumentStoreAddress,
    invalidDocumentSignatureOverride,
    invalidDocumentStoreAddressOverride,
    getDocumentSignature,
    wrapDocument
  })=>{
    test(version, async ()=>{
      const wallet = await connectWallet(config);
      const documentStore = await connectDocumentStore(config, wallet);

      const documents = new Map<string, any>();

      const invalidSignatureDocument = await wrapDocument(document());
      _.merge(invalidSignatureDocument, invalidDocumentSignatureOverride);

      const revokedDocument = await wrapDocument(document());
      await documentStore.revoke(`0x${getDocumentSignature(revokedDocument)}`);

      documents.set('invalid-signature-document', invalidSignatureDocument);
      documents.set('revoked-document', revokedDocument);
      documents.set('non-json-document', 'non-json-document-body');
      documents.set('deleted-document', document());
      documents.set('unwrapped-document', document());
      documents.set('invalid-document', {body: 'invalid-document-body'});
      documents.set('invalid-document-store-document', await wrapDocument(document(invalidDocumentStoreAddressOverride)));
      documents.set('wrapped-document', await wrapDocument(document()));

      for(let [key, document] of documents){
        if(typeof document !== 'string'){
          document = JSON.stringify(document);
        }
        await unprocessedDocuments.put({Key: key, Body: document});
      }
      await unprocessedDocuments.delete({Key: 'deleted-document'});

      const batch = new Batch();
      const composeRevokeBatch = new ComposeRevokeBatch({
        version,
        wallet,
        documentStore,
        batchDocuments,
        unprocessedDocuments,
        unprocessedDocumentsQueue,
        invalidDocuments,
        messageWaitTime: 10,
        messageVisibilityTimeout: 10,
        batchSizeBytes: 1,
        batchTimeSeconds: 10,
        attempts: 1,
        attemptsIntervalSeconds: 60,
        batch
      });
      await composeRevokeBatch.start();

      const invalidDocumentReasonAssert = createInvalidDocumentReasonAssert(batch, documents, invalidDocuments);
      expect(batch.unwrappedDocuments.size).toBe(0);
      expect(batch.wrappedDocuments.size).toBe(1);
      await invalidDocumentReasonAssert(
        'invalid-document-store-document',
        `Invalid document store address. Expected: ${documentStore.address}. Got: ${invalidDocumentStoreAddress}`
      )
      await invalidDocumentReasonAssert(
        'non-json-document',
        'Document body is not a valid JSON'
      )
      await invalidDocumentReasonAssert(
        'unwrapped-document',
        'Document not wrapped'
      )
      await invalidDocumentReasonAssert(
        'invalid-document',
        'Document not wrapped'
      )
      await invalidDocumentReasonAssert(
        'invalid-signature-document',
        'Invalid document signature'
      )
      await invalidDocumentReasonAssert(
        'revoked-document',
        `Document 0x${getDocumentSignature(revokedDocument)} already revoked`
      )
      expect(batch.wrappedDocuments.get('deleted-document')).toBeFalsy();
      expect(batch.wrappedDocuments.get('wrapped-document')).toBeTruthy();
    });
  });
});;
