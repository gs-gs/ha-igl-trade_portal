import _ from 'lodash';
import express from 'express';
import bodyParser from 'body-parser';
import expressPino from 'express-pino-logger';
import pino from 'pino';
import AWS from 'aws-sdk';

import {
  wrapDocument,
  verifySignature,
  validateSchema,
  getData,
  obfuscateDocument,
  signDocument,
  SUPPORTED_SIGNING_ALGORITHM,
  __unsafe__use__it__at__your__own__risks__wrapDocument
} from '@govtechsg/open-attestation';

const OA_V2_ID = 'https://schema.openattestation.com/2.0/schema.json';
const OA_V3_ID = 'https://schema.openattestation.com/3.0/schema.json';

const KMS = new AWS.KMS();

const DEFAULT_WRAP_PARAMS = {
  version: OA_V3_ID
};

export default function app(){
  const logger = pino({level: process.env.LOG_LEVEL || 'info', enabled: process.env.NOLOG === undefined});
  const app = express();

  app.use(bodyParser.json({"limit": "50mb", "strict": true}));
  // app.use(expressPino({logger}));

  class UserFriendlyError extends Error{}

  function errorHandler(err: any, req: express.Request, res: express.Response, next: CallableFunction){
    if(err instanceof UserFriendlyError){
      res.status(400).send({error: err.message});
    }else if (err.status == 400) {
      res.status(400).send({error: err.type});
    }else{
      res.status(500).send({error: 'Internal server error'});
    }
    logger.error(err);
    next()
  }

  const documentWrapRequestHandler = async (req: express.Request, res: express.Response, _next: any)=>{
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    

    // get sigining key
    const pkEnv = process.env.DOCUMENT_STORE_OWNER_PRIVATE_KEY||'';
    const b64String = pkEnv.slice("kms+base64:".length)
    const data = Buffer.from(b64String, 'base64').toString('utf-8');

    const decrypted = await KMS.decrypt({CiphertextBlob: data}).promise();
    const privateKey = decrypted.Plaintext?.toString('utf-8')??'';

    const publicKey = process.env.DOCUMENT_STORE_OWNER_PUBLIC_KEY;


    const document = req.body.document;
    const params = {...DEFAULT_WRAP_PARAMS, ...(req.body.params || {})};
    console.log(JSON.stringify(document, null, 2))
    console.log(JSON.stringify(params, null, 2))
    let wrappedDocument: object;
    try{
      if(params.version == OA_V3_ID){
        wrappedDocument = await __unsafe__use__it__at__your__own__risks__wrapDocument(document);
      }else if(params.version == OA_V2_ID){
        wrappedDocument = wrapDocument(document, params);
      }else{
        throw new UserFriendlyError('Unknown document version');
      }
      console.log(JSON.stringify(wrappedDocument, null, 2))
  
      const signedDocument = await signDocument(wrappedDocument, SUPPORTED_SIGNING_ALGORITHM.Secp256k1VerificationKey2018, {
        public: `did:ethr:${publicKey}#controller`,
        private: privateKey,
      });

      console.log(JSON.stringify(signedDocument, null, 2));

      res.status(200).send(signedDocument);
    }catch(e){
      let error = e.message;
      if (e.validationErrors) {
        error = JSON.stringify(e.validationErrors)
      }
      throw new UserFriendlyError(error);
    }
  }

  const documentUnwrapRequestHandler = async (req: express.Request, res: express.Response, _next: any)=>{
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    const unwrappedDocument = getData(req.body.document);
    res.status(200).send(unwrappedDocument);
  }

  const documentObfuscateRequestHandler = async (req: express.Request, res: express.Response, _next: any)=>{
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    if (req.body.keys === undefined){throw new UserFriendlyError('No "keys" field in payload');}
    const obfuscatedDocument = obfuscateDocument(req.body.document, req.body.keys);
    res.status(200).send(obfuscatedDocument);
  }

  const documentValidateSchemaRequestHandler = async(req: express.Request, res: express.Response, _next: any)=>{
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    const valid = validateSchema(req.body.document)
    const verification = {valid};
    res.send(verification);
  }

  const documentVerifySignatureRequestHandler = async(req: express.Request, res: express.Response, _next: any)=>{
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    const valid = verifySignature(req.body.document);
    const verification = {valid};
    res.send(verification);
  }

  const healthcheckRequestHandler = async(req: express.Request, res: express.Response, _next: any)=>{
    if (req.query.exception) {
      // for Sentry tests
      throw "healthcheck test exception";
    }
    res.json({
      "product": "oa-api",
      "version": "20200327"
    });
  }

  app.post('/document/wrap', async function (req: express.Request, res: express.Response, next: any){
    documentWrapRequestHandler(req, res, next).catch(next);
  });

  app.post('/document/unwrap', function (req: express.Request, res: express.Response, next: any){
    documentUnwrapRequestHandler(req, res, next).catch(next);
  });

  app.post('/document/obfuscate', (req: express.Request, res: express.Response, next: any)=>{
    documentObfuscateRequestHandler(req, res, next).catch(next);
  });

  app.post('/document/validate/schema', function (req: express.Request, res: express.Response, next: any){
    documentValidateSchemaRequestHandler(req, res, next).catch(next);
  });

  app.post('/document/verify/signature', function (req: express.Request, res: express.Response, next: any){
    documentVerifySignatureRequestHandler(req, res, next).catch(next);
  });

  app.get("/healthcheck", function (req: express.Request, res: express.Response, next: any){
    healthcheckRequestHandler(req, res, next).catch(next);
  });

  app.use(errorHandler);

  return app
}
