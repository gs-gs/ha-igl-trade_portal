const _ = require('lodash');
const express = require('express');
const bodyParser = require('body-parser');
const expressPino = require('express-pino-logger');
const pino = require('pino');
const AWS = require('aws-sdk');

const {
  wrapDocument,
  verifySignature,
  validateSchema,
  getData,
  obfuscateDocument,
  signDocument,
  SUPPORTED_SIGNING_ALGORITHM
} = require('@govtechsg/open-attestation');

const KMS = new AWS.KMS();

const DEFAULT_WRAP_PARAMS = { //Morgan: This currently does nothing in OA, despite what docs say!
  version: 'https://schema.openattestation.com/3.0/schema.json'  
};



function create(){
  const logger = pino({level: process.env.LOG_LEVEL || 'info', enabled: process.env.NOLOG === undefined});
  const app = express();

  app.use(bodyParser.json({"limit": "50mb", "strict": true}));
  app.use(expressPino({logger}));

  class UserFriendlyError extends Error{}

  function errorHandler(err, req, res, next){
    if(err instanceof UserFriendlyError){
      res.status(400).send({error: err.message});
    }else if (err.status == 400) {
      res.status(400).send({error: err.type});
    }else{
      res.status(500).send({error: 'Internal server error'});
    }
    logger.error(err);
  }

  
  app.post("/document/sign", async function(req,res){
    console.log('/document/sign')
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    const document = req.body.document; 


    const pkEnv = process.env.DOCUMENT_STORE_OWNER_PRIVATE_KEY||'';
    if(pkEnv.startsWith('kms+base64:')){// Then it needs decrypting.
      const b64String = pkEnv.slice("kms+base64:".length)
      console.log(b64String);
    
      const data = Buffer.from(b64String, 'base64');
      console.log("attempting to decrypt private key")
      try{
        const decrypted = await KMS.decrypt({CiphertextBlob: data}).promise();
        const privateKey = decrypted.Plaintext?.toString('utf-8')??'';
        console.log("private key decrypted")

        console.log(privateKey.slice(0, 10))
      }
      catch(e){
        console.log("failed to decrypt key")
      }
    } 
    else{ // Probably running locally in this case.
      privateKey = pkEnv;
    }
    const publicKey = process.env.DOCUMENT_STORE_OWNER_PUBLIC_KEY;
    try{// Do the actual signing
      const signedDocument = await signDocument(document, 
          SUPPORTED_SIGNING_ALGORITHM.Secp256k1VerificationKey2018, {
        public: `did:ethr:${publicKey}#controller`, // this will become the verificationMethod in the singed document
        private: privateKey,
      });
      console.log("document signed")
      console.log(JSON.stringify(signedDocument, null, 2));
      if (!verifySignature(signedDocument)){
        console.log("Signing not validated immediately after signing.");
      }
          
      res.status(200).send(signedDocument);
    } 
    catch(e){
        console.log(e)
    }
  });

  app.post("/document/wrap", async function (req, res){
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    const document = req.body.document;
    const params = {...DEFAULT_WRAP_PARAMS, ...(req.body.params || {})};
    try{
      const wrappedDocument = wrapDocument(document, params);
      res.status(200).send(wrappedDocument);
      /*
      console.log("document wrapped")
      console.log(wrappedDocument)
      // Previously  finished here: res.status(200).send(wrappedDocument);
      // get sigining key
      const pkEnv = process.env.DOCUMENT_STORE_OWNER_PRIVATE_KEY||'';
      const b64String = pkEnv.slice("kms+base64:".length)
      console.log(b64String);
      const data = Buffer.from(b64String, 'base64');


      console.log("attempting to decrypt private key")
      try{
        const decrypted = await KMS.decrypt({CiphertextBlob: data}).promise();
        const privateKey = decrypted.Plaintext?.toString('utf-8')??'';
        console.log("private key decrypted")

        console.log(privateKey.slice(0, 10))
        const publicKey = process.env.DOCUMENT_STORE_OWNER_PUBLIC_KEY;

        const signedDocument = await signDocument(wrappedDocument, SUPPORTED_SIGNING_ALGORITHM.Secp256k1VerificationKey2018, {
          public: `did:ethr:${publicKey}#controller`,
          private: privateKey,
        });
        console.log("document signed")
        console.log(JSON.stringify(signedDocument, null, 2));
        
        res.status(200).send(signedDocument);
      } 
      catch(e){
        console.log("failed to either decrypt key or sign document")
        console.log(e)
      }
      */
      
    }catch(e){
      let error = e.message;
      if (e.validationErrors) {
         error = JSON.stringify(e.validationErrors) //Morgan: I suspect this is vestigial?
      }
      throw new UserFriendlyError(error);
    }
  });

  app.post('/document/unwrap', function (req, res){
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    const unwrappedDocument = getData(req.body.document);
    res.status(200).send(unwrappedDocument);
  });

  app.post('/document/obfuscate', (req, res)=>{
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    if (req.body.keys === undefined){throw new UserFriendlyError('No "keys" field in payload');}
    const obfuscatedDocument = obfuscateDocument(req.body.document, req.body.keys);
    res.status(200).send(obfuscatedDocument);
  });

  app.post('/document/validate/schema', function (req, res){
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    const valid = validateSchema(req.body.document)
    const verification = {valid};
    res.send(verification);
  });

  app.post('/document/verify/signature', function (req, res){
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    const valid = verifySignature(req.body.document);
    const verification = {valid};
    res.send(verification);
  });

  app.get("/healthcheck", function (req, res){
    if (req.query.exception) {
      // for Sentry tests
      throw "healthcheck test exception";
    }
    res.json({
      "product": "oa-api",
      "version": "20200327"
    });
  });

  app.use(errorHandler);

  return app
}

module.exports = create
