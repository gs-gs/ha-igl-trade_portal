const _ = require('lodash');
const express = require('express');
const bodyParser = require('body-parser');
const expressPino = require('express-pino-logger');
const pino = require('pino');

const {
  wrapDocument,
  verifySignature,
  validateSchema,
  getData,
  obfuscateDocument
} = require('@govtechsg/open-attestation');


const DEFAULT_WRAP_PARAMS = {
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

  app.post('/document/wrap', function (req, res){
    if (req.body.document === undefined){throw new UserFriendlyError('No "document" field in payload');}
    const document = req.body.document;
    const params = {...DEFAULT_WRAP_PARAMS, ...(req.body.params || {})};
    try{
      const wrappedDocument = wrapDocument(document, params);
      res.status(200).send(wrappedDocument);
    }catch(e){
      let error = e.message;
      if (e.validationErrors) {
        error = JSON.stringify(e.validationErrors)
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
