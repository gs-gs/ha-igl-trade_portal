const _ = require('lodash');
const chai = require('chai');
const chaiHttp = require('chai-http');
const create = require('../src/app');
const documentV3 = require('./document-v3');
const documentV2 = require('./document-v2');

chai.use(chaiHttp);
chai.should();

const TEST_PARAMS = [
  {
    document: documentV3,
    title: 'default open-attestation document version(V3)'
  },
  {
    document: documentV2,
    title: 'open-attestation document version V2',
    params: {
      version: 'https://schema.openattestation.com/2.0/schema.json'
    }
  },
  {
    document: documentV3,
    title: 'open-attestation document version V3',
    params: {
      version: 'https://schema.openattestation.com/3.0/schema.json'
    }
  }
]


function run(){
  const app = create();
  for (const params of TEST_PARAMS){
    test(params, app);
  }
}

run();


function test(testParams, app){
  describe(testParams.title,  function(){
    const unwrappedDocument = testParams.document;
    const params = testParams.params;
    let wrappedDocument = null;
    let obfuscatedDocument = null;
    describe('/document/wrap',  function(){
      it('valid schema',  function(){
        chai.request(app).post('/document/wrap')
        .send({document:unwrappedDocument, params})
        .end(function(err, res){
          res.should.have.status(200, res.body);
          wrappedDocument = res.body;
        });
      });
      it('invalid schema',  function(){
        chai.request(app).post('/document/wrap')
        .send({document:{}, params})
        .end(function(err, res){
          res.should.have.status(400);
          res.body.should.have.nested.property('error');
        });
      });
      it('no document',  function(){
        chai.request(app).post('/document/wrap')
        .send({params})
        .end(function(err, res){
          res.should.have.status(400);
          res.body.should.deep.equal({error:"No \"document\" field in payload"})
        });
      });
    });

    describe('/document/unwrap',  function(){
      it('wrapped document',  function(){
        chai.request(app).post('/document/unwrap')
        .send({document:wrappedDocument})
        .end(function(err, res){
          res.should.have.status(200);
          res.body.should.deep.equal(unwrappedDocument);
        })
      });
      it('empty document',  function(){
        chai.request(app).post('/document/unwrap')
        .send({document:{}})
        .end(function(err, res){
          res.should.have.status(200);
          res.body.should.deep.equal({});
        })
      });
      it('no document',  function(){
        chai.request(app).post('/document/unwrap')
        .send({})
        .end(function(err, res){
          res.should.have.status(400);
          res.body.should.deep.equal({error: "No \"document\" field in payload"});
        })
      });
    });

    describe('/document/obfuscate',  function(){
      it('obfuscate',  function(){
        chai.request(app).post('/document/obfuscate')
        .send({keys: ['data.message.private'], document: wrappedDocument})
        .end(function(err, res){
          res.should.have.status(200);
          obfuscatedDocument = res.body;
        });
      });
      it('unwrap and compare',  function(){
        chai.request(app).post('/document/unwrap')
        .send({document: obfuscatedDocument})
        .end(function(err, res){
          res.should.have.status(200);
          const unwrappedDocumentCopy = _.cloneDeep(unwrappedDocument);
          delete unwrappedDocumentCopy.data.message.private;
          res.body.should.deep.equal(unwrappedDocumentCopy);
        });
      });
      it('empty document',  function(){
        chai.request(app).post('/document/obfuscate')
        .send({keys: ['data.message.private'], document: {}})
        .end(function(err, res){
          res.should.have.status(200);
        });
      });
      it('no document',  function(){
        chai.request(app).post('/document/obfuscate')
        .send({keys:[]})
        .end(function(err, res){
          res.should.have.status(400);
          res.body.should.deep.equal({error: "No \"document\" field in payload"});
        });
      });
      it('no keys',  function(){
        chai.request(app).post('/document/obfuscate')
        .send({document:{}})
        .end(function(err, res){
          res.should.have.status(400);
          res.body.should.deep.equal({error: "No \"keys\" field in payload"});
        });
      });
    });


    describe('/document/validate/schema',  function(){
      it('wrapped document',  function(){
        chai.request(app).post('/document/validate/schema')
        .send({document:wrappedDocument})
        .end(function(err, res){
          res.should.have.status(200);
          res.body.should.deep.equal({valid:true})
        });
      });
      it('obfuscated document',  function(){
        chai.request(app).post('/document/validate/schema')
        .send({document:obfuscatedDocument})
        .end(function(err, res){
          res.should.have.status(200);
          res.body.should.deep.equal({valid:true})
        });
      });
      it('unwrapped document',  function(){
        chai.request(app).post('/document/validate/schema')
        .send({document: unwrappedDocument})
        .end(function(err, res){
          res.should.have.status(200);
          res.body.should.deep.equal({valid:false})
        });
      });
      it('empty document',  function(){
        chai.request(app).post('/document/validate/schema')
        .send({document:{}})
        .end(function(err, res){
          res.should.have.status(200);
          res.body.should.deep.equal({valid:false})
        });
      });
      it('no document',  function(){
        chai.request(app).post('/document/validate/schema')
        .end(function(err, res){
          res.should.have.status(400);
          res.body.should.deep.equal({error: "No \"document\" field in payload"});
        });
      });
    });


    describe('/document/verify/signature',  function(){
      it('wrapped document',  function(){
        chai.request(app).post('/document/verify/signature')
        .send({document:wrappedDocument})
        .end(function(err, res){
          res.should.have.status(200);
          res.body.should.deep.equal({valid:true})
        });
      });
      it('obfuscated document',  function(){
        chai.request(app).post('/document/verify/signature')
        .send({document:obfuscatedDocument})
        .end(function(err, res){
          res.should.have.status(200);
          res.body.should.deep.equal({valid:true})
        });
      });
      it('unwrapped document',  function(){
        chai.request(app).post('/document/verify/signature')
        .send({document:unwrappedDocument})
        .end(function(err, res){
          res.should.have.status(200);
          res.body.should.deep.equal({valid:false})
        });
      });
      it('empty document',  function(){
        chai.request(app).post('/document/verify/signature')
        .send({document:{}})
        .end(function(err, res){
          res.should.have.status(200, res.body);
          res.body.should.deep.equal({valid:false})
        });
      });
      it('no document',  function(){
        chai.request(app).post('/document/verify/signature')
        .end(function(err, res){
          res.should.have.status(400);
          res.body.should.deep.equal({error: "No \"document\" field in payload"})
        });
      });
    });
  });
}
