import _ from 'lodash';
import request from 'supertest';
import create from '../src/app';
import documentV3 from './document-v3.json';
import documentV2 from './document-v2.json';

const TEST_PARAMS = [
  [
    'V2',
    {
      document: documentV2 as any,
      params: {
        version: 'https://schema.openattestation.com/2.0/schema.json'
      }
    }
  ],
  [
    'V3',
    {
      document: documentV3 as any,
      params: {
        version: 'https://schema.openattestation.com/3.0/schema.json'
      }
    }
  ]
]


describe('API', ()=>{
  const app = create();
  describe.each(TEST_PARAMS)('%s', (title: any, props: any)=>{
    let params = props.params;
    let unwrappedDocument: any = props.document;
    let wrappedDocument: any = null;
    let obfuscatedDocument: any = null;


    describe('/document/wrap', ()=>{
      test('valid', async ()=>{
        const res = await request(app).post('/document/wrap').send({document: unwrappedDocument, params})
        expect(res.statusCode).toBe(200);
        expect(res.body).toBeTruthy();
        wrappedDocument = res.body;
      }),
      test('invalid', async ()=>{
        const res = await request(app).post('/document/wrap').send({document:{}, params})
        expect(res.statusCode).toBe(400);
        expect(res.body).toHaveProperty('error')
      });
      test('no document',  async function(){
        const res = await request(app).post('/document/wrap').send({params});
        expect(res.statusCode).toBe(400);
        expect(res.body).toEqual({error:"No \"document\" field in payload"})
      });
    })


    if(title == 'V2'){
      // test uses wrappedDocument obtained from the previous test
      describe('/document/unwrap', ()=>{
        test('wrapped document', async ()=>{
          const res = await request(app).post('/document/unwrap')
          .send({document:wrappedDocument});
          expect(res.statusCode).toBe(200);
          expect(res.body).toEqual(unwrappedDocument);
        });
        test('empty document', async ()=>{
          const res = await request(app).post('/document/unwrap')
          .send({document:{}});
          expect(res.statusCode).toBe(200);
        });
        test('no document',  async ()=>{
          const res = await request(app).post('/document/unwrap')
          .send({});
          expect(res.statusCode).toBe(400);
          expect(res.body).toEqual({error: "No \"document\" field in payload"});
        });
      });
    }


    describe('/document/obfuscate', ()=>{
      test('obfuscate',  async ()=>{
        const res = await request(app).post('/document/obfuscate')
        .send({keys: ['credentialSubject.birthDate'], document: wrappedDocument});
        expect(res.statusCode).toBe(200);
        obfuscatedDocument = res.body;
      });
      if( title == 'V2'){
        test('unwrap and compare',  async ()=>{
          const res = await request(app).post('/document/unwrap')
          .send({document: obfuscatedDocument});
          expect(res.statusCode).toBe(200);
          const unwrappedDocumentCopy = _.cloneDeep(unwrappedDocument);
          delete unwrappedDocumentCopy.credentialSubject.birthDate;
          expect(res.body).toEqual(unwrappedDocumentCopy);
        });
      }else if(title == 'V3'){
        test('compare with unwrapped', async ()=>{
          const unwrappedDocumentCopy = _.cloneDeep(unwrappedDocument);
          delete unwrappedDocumentCopy.credentialSubject.birthDate;
          expect(obfuscatedDocument.credentialSubject).toEqual(unwrappedDocumentCopy.credentialSubject);
        });
      }
      test('empty document',  async ()=>{
        const res = await request(app).post('/document/obfuscate')
        .send({keys: ['credentialSubject.birthDate'], document: {}});
        expect(res.statusCode).toBe(200);
      });
      test('no document',  async ()=>{
        const res = await request(app).post('/document/obfuscate')
        .send({keys:[]});
        expect(res.statusCode).toBe(400);
        expect(res.body).toEqual({error: "No \"document\" field in payload"});
      });
      test('no keys',  async ()=>{
        const res = await request(app).post('/document/obfuscate')
        .send({document:{}});
        expect(res.statusCode).toBe(400);
        expect(res.body).toEqual({error: "No \"keys\" field in payload"});
      });
    });


    describe('/document/validate/schema',  ()=>{
      test('wrapped document',  async ()=>{
        const res = await request(app).post('/document/validate/schema')
        .send({document:wrappedDocument});
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:true});
      });
      test('obfuscated document',  async ()=>{
        const res = await request(app).post('/document/validate/schema')
        .send({document:obfuscatedDocument});
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:true});
      });
      test('unwrapped document',  async ()=>{
        const res = await request(app).post('/document/validate/schema')
        .send({document:unwrappedDocument});
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:false});
      });
      test('empty document',  async ()=>{
        const res = await request(app).post('/document/validate/schema')
        .send({document:{}});
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:false});
      });
      test('no document',  async ()=>{
        const res = await request(app).post('/document/validate/schema');
        expect(res.statusCode).toBe(400);
        expect(res.body).toEqual({error: "No \"document\" field in payload"});
      });
    });


    describe('/document/verify/signature',  ()=>{
      test('wrapped document',  async ()=>{
        const res = await request(app).post('/document/verify/signature')
        .send({document:wrappedDocument});
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:true})
      });
      test('obfuscated document',  async ()=>{
        const res = await request(app).post('/document/verify/signature')
        .send({document:obfuscatedDocument});
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:true})
      });
      test('unwrapped document',  async ()=>{
        const res = await request(app).post('/document/verify/signature')
        .send({document:unwrappedDocument});
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:false})
      });
      test('empty document',  async ()=>{
        const res = await request(app).post('/document/verify/signature')
        .send({document:{}});
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:false})
      });
      test('no document',  async ()=>{
        const res = await request(app).post('/document/verify/signature')
        expect(res.statusCode).toBe(400);
        expect(res.body).toEqual({error: "No \"document\" field in payload"})
      });
    });
  })
})
