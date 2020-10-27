const _ = require('lodash');
const express = require('express');
const bodyParser = require('body-parser');
const expressPino = require('express-pino-logger');
const pino = require('pino');
const multer = require('multer');
const { verify, isValid } = require('@govtechsg/oa-verify');

function create(){

  const logger = pino({level: process.env.LOG_LEVEL || 'info', enabled: process.env.NOLOG === undefined});

  class UserFriendlyError extends Error{}

  function errorHandler(err, req, res, next){
    if(err instanceof UserFriendlyError){
      res.status(400).send({error: err.message});
    }else if (err.status == 400) {
      res.status(400).send({error: err.message});
    }else{
      res.status(500).send({error: 'Internal server error'});
    }
    logger.error(err);
  }

  const upload = multer({storage: multer.memoryStorage(), fileSize: 1024 * 1024 * 50});
  const app = express();

  const VERIFY_OPTIONS = {
    network: (process.env.ETHEREUM_NETWORK || 'ropsten').toLowerCase()
  };

  app.use(bodyParser.json({'limit': '50mb', 'strict': true}));
  app.use(expressPino({logger}));

  function getDocumentJSON(req){
    const {body, file} = req;
    let document = null;
    if(file !== undefined){
      try {
        document = JSON.parse(file.buffer.toString('utf8'));
      } catch(e){
        throw new UserFriendlyError(`File is not valid JSON document. ${e}`);
      }
    } else if (body !== undefined) {
      document = body;
    }else{
      throw new UserFriendlyError("Can't find document data in the request.");
    }
    return document;
  }

  app.post('/verify', upload.single('file'), async function (req, res, next){
    async function handler(){
      const document = getDocumentJSON(req);
      const fragments = await verify(document, VERIFY_OPTIONS);
      const valid = isValid(fragments);
      res.status(200).send({valid});
    }
    handler().catch(next);
  });


  app.post('/verify/fragments', upload.single('file'), async function(req, res, next){
    async function handler(){
      const document = getDocumentJSON(req);
      const fragments = await verify(document, VERIFY_OPTIONS);
      res.status(200).send(fragments);
    }
    handler().catch(next);
  });


  app.use(errorHandler);

  return app
}

module.exports = create
