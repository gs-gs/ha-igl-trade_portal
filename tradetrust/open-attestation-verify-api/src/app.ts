import _ from 'lodash';
import { providers } from 'ethers';
import express from 'express';
import bodyParser from 'body-parser';
import expressPino from 'express-pino-logger';
import Sentry from '@sentry/node';
import pino from 'pino';
import multer from 'multer';
import {
  verificationBuilder,
  isValid,
  openAttestationVerifiers,
  openAttestationDidIdentityProof,
  createResolver
} from '@govtechsg/oa-verify';

export default function app(){

  const logger = pino({level: process.env.LOG_LEVEL || 'info', enabled: process.env.NOLOG === undefined});

  if (process.env.SENTRY_DSN) {
    Sentry.init({
      dsn: process.env.SENTRY_DSN,
    });
  }

  class UserFriendlyError extends Error{}

  function errorHandler(err: any, _req: express.Request, res: express.Response, _next: CallableFunction){
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

  const upload = multer({storage: multer.memoryStorage(), limits: {fileSize: 1024 * 1024 * 50}});
  const app = express();

  const getVerifyOptions = ()=>{
    const rpcUrl: string = process.env.PROVIDER_ENDPOINT_URL?? '';
    const network: string = process.env.PROVIDER_NETWORK??'mainnet';
    const chainId: number = parseInt(process.env.PROVIDER_CHAIN_ID??"1");
    const provider = new providers.JsonRpcProvider(rpcUrl, {name: network, chainId});
    logger.info({
      PROVIDER_ENDPOINT_URL: rpcUrl,
      PROVIDER_NETWORK: network,
      PROVIDER_CHAIN_ID: chainId
    });
    const resolver = createResolver({
      ethrResolverConfig: {
        networks: [
          {
            name: network,
            rpcUrl
          }
        ]
      }
    })
    return {
      provider,
      resolver
    }
  }

  const VERIFY_OPTIONS = getVerifyOptions();
  const VERIFIERS = [...openAttestationVerifiers, openAttestationDidIdentityProof];

  logger.info('Connected to blockchain endpoint "%s"', process.env.PROVIDER_ENDPOINT_URL);

  const verify = verificationBuilder(VERIFIERS, VERIFY_OPTIONS);

  app.use(bodyParser.json({'limit': '50mb', 'strict': true}));
  app.use(expressPino({logger}));

  function getDocumentJSON(req: express.Request){
    const {body, file} = req;
    let document = null;
    if(file !== undefined){
      try {
        document = JSON.parse(file.buffer.toString('utf8'));
      } catch(e){
        throw new UserFriendlyError(`File is not valid JSON document. ${e}`);
      }
    } else if (body !== undefined && !_.isEmpty(body)) {
      document = body;
    }else{
      throw new UserFriendlyError("Can't find document data in the request.");
    }
    return document;
  }

  const postVerifyRequestHandler = async (req: express.Request, res: express.Response, next: any)=>{
    // check that the node connection is active
    // it will throw an error if something went wrong while getting network details
    await VERIFY_OPTIONS.provider.getNetwork();
    const document = getDocumentJSON(req);
    const fragments = await verify(document);
    const valid = isValid(fragments);
    res.status(200).send({valid});
  }

  const postVerifyFragmentsHandler = async (req: express.Request, res: express.Response, next: any)=>{
    // check that the node connection is active
    // it will throw an error if something went wrong while getting network details
    await VERIFY_OPTIONS.provider.getNetwork();
    const document = getDocumentJSON(req);
    const fragments = await verify(document);
    res.status(200).send(fragments);
  }

  const getHealthcheckRequestHandler = async (req: express.Request, res: express.Response, next: any)=>{
    if (req.query.exception) {
      // for Sentry tests
      throw "healthcheck test exception";
    }
    res.json({
      "version": "20200317"
    });
  }

  app.post('/verify', upload.single('file'), async function (req: express.Request, res: express.Response, next: any){
    postVerifyRequestHandler(req, res, next).catch(next);
  });

  app.post('/verify/fragments', upload.single('file'), async function(req: express.Request, res: express.Response, next: any){
    postVerifyFragmentsHandler(req, res, next).catch(next);
  });

  app.get("/healthcheck", function (req: express.Request, res: express.Response, next: any){
    getHealthcheckRequestHandler(req, res, next).catch(next)
  });

  app.use(errorHandler);

  return app
}
