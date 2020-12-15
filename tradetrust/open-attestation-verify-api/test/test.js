const _ = require('lodash');
const {promises:fs} = require('fs');
const path = require('path');
const chai = require('chai');
const chaiHttp = require('chai-http');
const { isValid } = require('@govtechsg/oa-verify');

chai.use(chaiHttp);
chai.should();


const TEST_DATA_DIR = '/open-attestation-verify-api/test/data'
const ROPSTEN_DOCUMENT_VALID_PATH = path.join(TEST_DATA_DIR, 'ropsten-certificate-valid.json');
const ROPSTEN_DOCUMENT_INVALID_PATH = path.join(TEST_DATA_DIR, 'ropsten-certificate-invalid.json');
const EMPTY_JSON_PATH = path.join(TEST_DATA_DIR, 'empty.json');


describe('API test', function(){
  const props = {
    fragments:{
      file:{},
      json:{}
    }
  };
  before(async function(){
    // this is OA developers default infura api key, we probably need to use our own
    process.env.BLOCKCHAIN_ENDPOINT = "https://ropsten.infura.io/v3/bb46da3f80e040e8ab73c0a9ff365d18"
    const create = require('../src/app');
    props.app = create();
    props.ropstenDocumentValid = JSON.parse(await fs.readFile(ROPSTEN_DOCUMENT_VALID_PATH));
    props.ropstenDocumentInvalid = JSON.parse(await fs.readFile(ROPSTEN_DOCUMENT_INVALID_PATH));
  });
  describe('POST /verify', function(){
    describe('json', function(){
      it('valid', async function(){
        const res = await chai.request(props.app).post('/verify').send(props.ropstenDocumentValid);
        res.should.have.status(200);
        res.body.should.deep.equal({valid:true});
      });
      it('invalid', async function(){
        const res = await chai.request(props.app).post('/verify').send(props.ropstenDocumentInvalid);
        res.should.have.status(200);
        res.body.should.deep.equal({valid:false});
      });
      it('empty', async function(){
        const res = await chai.request(props.app).post('/verify').send({});
        res.should.have.status(200);
        res.body.should.deep.equal({valid:false});
      });
    });
    describe('file', function(){
      it('valid', async function(){
        const res = await chai.request(props.app)
        .post('/verify')
        .attach('file', ROPSTEN_DOCUMENT_VALID_PATH, 'document.json')
        res.should.have.status(200);
        res.body.should.deep.equal({valid:true});
      });
      it('invalid', async function(){
        const res = await chai.request(props.app)
        .post('/verify')
        .attach('file', ROPSTEN_DOCUMENT_INVALID_PATH, 'document.json')
        res.should.have.status(200);
        res.body.should.deep.equal({valid:false});
      });
      it('empty', async function(){
        const res = await chai.request(props.app)
        .post('/verify')
        .attach('file', EMPTY_JSON_PATH, 'document.json')
        res.should.have.status(200);
        res.body.should.deep.equal({valid:false});
      });
    });
  });
  describe('POST /verify/fragments', function(){
    describe('json', function(){
      it('valid', async function(){
        const res = await chai.request(props.app).post('/verify/fragments').send(props.ropstenDocumentValid);
        res.should.have.status(200);
        chai.assert(isValid(res.body));
        props.fragments.json.valid = res.body;
      });
      it('invalid', async function(){
        const res = await chai.request(props.app).post('/verify/fragments').send(props.ropstenDocumentInvalid);
        res.should.have.status(200);
        chai.assert(!isValid(res.body));
        props.fragments.json.invalid = res.body;
      });
      it('empty', async function(){
        const res = await chai.request(props.app).post('/verify/fragments').send({});
        res.should.have.status(200);
        chai.assert(!isValid(res.body));
        props.fragments.json.empty = res.body;
      });
    });
    describe('file', function(){
      it('valid', async function(){
        const res = await chai.request(props.app)
        .post('/verify/fragments')
        .attach('file', ROPSTEN_DOCUMENT_VALID_PATH, 'document.json')
        res.should.have.status(200);
        chai.assert(isValid(res.body));
        props.fragments.file.valid = res.body;
      });
      it('invalid', async function(){
        const res = await chai.request(props.app)
        .post('/verify/fragments')
        .attach('file', ROPSTEN_DOCUMENT_INVALID_PATH, 'document.json')
        res.should.have.status(200);
        chai.assert(!isValid(res.body));
        props.fragments.file.invalid = res.body;
      });
      it('empty', async function(){
        const res = await chai.request(props.app)
        .post('/verify/fragments')
        .attach('file', EMPTY_JSON_PATH, 'document.json')
        res.should.have.status(200);
        chai.assert(!isValid(res.body));
        props.fragments.file.empty = res.body;
      });
    });
    describe('fragments equality', function(){
      it('valid', function(){
        chai.assert.deepEqual(props.fragments.json.valid, props.fragments.file.valid);
      });
      it('invalid', function(){
        chai.assert.deepEqual(props.fragments.json.invalid, props.fragments.file.invalid);
      });
      it('empty', function(){
        chai.assert.deepEqual(props.fragments.json.empty, props.fragments.file.empty);
      });
    });
  });
});
