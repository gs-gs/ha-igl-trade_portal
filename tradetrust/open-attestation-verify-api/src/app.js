const _ = require('lodash');
const Web3 = require('web3');
const ethers = require('ethers');
const express = require('express');
const bodyParser = require('body-parser');
const expressPino = require('express-pino-logger');
const Sentry = require("@sentry/node");
const pino = require('pino');
const multer = require('multer');

const { verificationBuilder, isValid, openAttestationVerifiers } = require('@govtechsg/oa-verify');

function create(){

  const logger = pino({level: process.env.LOG_LEVEL || 'info', enabled: process.env.NOLOG === undefined});

  if (process.env.SENTRY_DSN) {
    Sentry.init({
      dsn: process.env.SENTRY_DSN,
    });
  }

  class UserFriendlyError extends Error{}

  function errorHandler(err, req, res, next){
    if (process.env.SENTRY_DSN) {
      Sentry.captureException(err);
      Sentry.flush(2000);
    };
    if(err instanceof UserFriendlyError){
      res.status(400).send({error: err.message});
    }else if (err.status == 400) {
      res.status(400).send({error: err.message});
    }else{
      res.status(500).send(
        {
          error: 'Internal server error',
          msg: err,
        }
      );
    }
    logger.error(err);
  }

  const upload = multer({storage: multer.memoryStorage(), fileSize: 1024 * 1024 * 50});
  const app = express();

  const VERIFY_OPTIONS = {
    provider:  new ethers.providers.Web3Provider(new Web3.providers.HttpProvider(process.env.BLOCKCHAIN_ENDPOINT))
  };

  logger.info('Connected to blockchain endpoint "%s"', process.env.BLOCKCHAIN_ENDPOINT);

  const verify = verificationBuilder(openAttestationVerifiers, VERIFY_OPTIONS);

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

  app.get("/healthcheck", function (req, res){
    if (req.query.exception) {
      // for Sentry tests
      throw "healthcheck test exception";
    }
    res.json({
      "version": "20200317"
    });
  });

  app.post('/verify', upload.single('file'), async function (req, res, next){
    async function handler(){
      // check that the node connection is active
      // it will throw an error if something went wrong while getting network details
      await VERIFY_OPTIONS.provider.getNetwork();
      const document = getDocumentJSON(req);
      const fragments = await verify(document);
      const valid = isValid(fragments);
      res.status(200).send({valid});
    }
    handler().catch(next);
  });


  app.post('/verify/fragments', upload.single('file'), async function(req, res, next){
    async function handler(){
      // check that the node connection is active
      // it will throw an error if something went wrong while getting network details
      await VERIFY_OPTIONS.provider.getNetwork();
      const document = getDocumentJSON(req);
      const fragments = await verify(document);
      res.status(200).send(fragments);
    }
    handler().catch(next);
  });

  app.use(errorHandler);

  return app
}

module.exports = create
