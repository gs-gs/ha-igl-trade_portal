import _ from 'lodash';
import request from 'supertest';
import path from 'path';
import { isValid } from '@govtechsg/oa-verify';
import createApp from 'src/app';
import V2_VALID from './data/v2/valid.json';
import V2_INVALID from './data/v2/invalid.json';
import V3_VALID from './data/v3/valid.json';
import V3_INVALID from './data/v3/invalid.json';


const DATA_DIR = '/open-attestation-verify-api/tests/data/';
const V2_VALID_PATH = path.join(DATA_DIR, 'v2/valid.json');
const V2_INVALID_PATH = path.join(DATA_DIR, 'v2/invalid.json');
const V3_VALID_PATH = path.join(DATA_DIR, 'v3/valid.json');
const V3_INVALID_PATH = path.join(DATA_DIR, 'v3/invalid.json');


const TEST_PARAMS = [
  {
    title: 'V2',
    documents: {
      valid: {
        json: V2_VALID,
        path: V2_VALID_PATH
      },
      invalid: {
        json: V2_INVALID,
        path: V2_INVALID_PATH
      }
    },
    provider: {
      PROVIDER_ENDPOINT_URL: 'https://ropsten.infura.io/v3/bb46da3f80e040e8ab73c0a9ff365d18',
      PROVIDER_NETWORK: 'ropsten',
      PROVIDER_CHAIN_ID: '3'
    }
  },
  {
    title: 'V3',
    documents:{
      valid: {
        json: V3_VALID,
        path: V3_VALID_PATH
      },
      invalid: {
        json: V3_INVALID,
        path: V3_INVALID_PATH
      }
    },
    provider: {
      PROVIDER_ENDPOINT_URL: 'https://mainnet.infura.io/v3/bb46da3f80e040e8ab73c0a9ff365d18',
      PROVIDER_NETWORK: 'mainnet',
      PROVIDER_CHAIN_ID: '1'
    }
  }
]

describe.each(TEST_PARAMS)('API $title', ({documents, provider})=>{
  process.env.PROVIDER_ENDPOINT_URL = provider.PROVIDER_ENDPOINT_URL;
  process.env.PROVIDER_NETWORK = provider.PROVIDER_NETWORK;
  process.env.PROVIDER_CHAIN_ID = provider.PROVIDER_CHAIN_ID;
  const app = createApp();
  beforeEach(()=>{
    jest.setTimeout(60 * 1000);
  })
  describe('POST /verify', ()=>{
    describe('json', ()=>{
      test('valid', async ()=>{
        const res = await request(app).post('/verify').send(documents.valid.json);
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:true});
      })
      test('invalid', async ()=>{
        const res = await request(app).post('/verify').send(documents.invalid.json);
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:false});
      });
    });
    describe('file', ()=>{
      test('valid', async ()=>{
        const res = await request(app).post('/verify').attach('file', documents.valid.path);
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:true});
      })
      test('invalid', async ()=>{
        const res = await request(app).post('/verify').attach('file', documents.invalid.path);
        expect(res.statusCode).toBe(200);
        expect(res.body).toEqual({valid:false});
      });
    });
    test('no payload', async ()=>{
      const res = await request(app).post('/verify');
      expect(res.statusCode).toBe(400);
      expect(res.body).toEqual({error: "Can't find document data in the request."})
    });
  });

  describe('POST /verify/fragments', ()=>{
    const fragments: any = {
      file: {},
      json: {}
    }
    describe('json', ()=>{
      test('valid', async ()=>{
        const res = await request(app).post('/verify/fragments').send(documents.valid.json);
        expect(res.statusCode).toBe(200);
        expect(isValid(res.body)).toBe(true);
        fragments.json.valid = res.body;
      });
      test('invalid', async ()=>{
        const res = await request(app).post('/verify/fragments').send(documents.invalid.json);
        expect(res.statusCode).toBe(200);
        expect(isValid(res.body)).toBe(false);
        fragments.json.invalid = res.body;
      });
    });
    describe('file', ()=>{
      test('valid', async ()=>{
        const res = await request(app).post('/verify/fragments').attach('file', documents.valid.path);
        expect(res.statusCode).toBe(200);
        expect(isValid(res.body)).toBe(true);
        fragments.file.valid = res.body;
      });
      test('invalid', async ()=>{
        const res = await request(app).post('/verify/fragments').attach('file', documents.invalid.path);
        expect(res.statusCode).toBe(200);
        expect(isValid(res.body)).toBe(false);
        fragments.file.invalid = res.body;
      });
    });
    describe('fragments equality', ()=>{
      test('valid', ()=>{
        expect(fragments.json.valid).toEqual(fragments.file.valid);
      });
      test('invalid', ()=>{
        expect(fragments.json.invalid).toEqual(fragments.file.invalid);
      })
    });
    test('no payload', async ()=>{
      const res = await request(app).post('/verify/fragments');
      expect(res.statusCode).toBe(400);
      expect(res.body).toEqual({error: "Can't find document data in the request."})
    });
  });
});
