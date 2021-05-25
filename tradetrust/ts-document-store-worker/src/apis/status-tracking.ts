import express, { Request, Response } from 'express';
import { getStatusTrackingAPIConfig } from 'src/config';
import { Bucket } from 'src/repos';
import { logger } from 'src/logger';
import { handler } from 'src/apis/utils/exceptions';


export const STATUS_PENDING = 'pending';
export const STATUS_PROCESSING = 'processing';
export const STATUS_INVALID = 'invalid';
export const STATUS_PROCESSED = 'processed';


export const api = ()=>{
  const config = getStatusTrackingAPIConfig();

  const repos = {
    issue: {
      unprocessed: new Bucket(config.ISSUE_UNPROCESSED_BUCKET_NAME),
      batch: new Bucket(config.ISSUE_BATCH_BUCKET_NAME),
      invalid: new Bucket(config.ISSUE_INVALID_BUCKET_NAME),
      processed: new Bucket(config.ISSUED_BUCKET_NAME)
    },
    revoke: {
      unprocessed: new Bucket(config.REVOKE_UNPROCESSED_BUCKET_NAME),
      batch: new Bucket(config.REVOKE_BATCH_BUCKET_NAME),
      invalid: new Bucket(config.REVOKE_INVALID_BUCKET_NAME),
      processed: new Bucket(config.REVOKED_BUCKET_NAME)
    }
  }

  interface IRepos{
    unprocessed: Bucket,
    batch: Bucket,
    invalid: Bucket,
    processed: Bucket
  }


  const app = express();
  app.use(handler);

  async function getDocument(repo: Bucket, key: string){
    try{
      return await repo.get({Key: key})
    }catch(e){
      if(e.code == 'NoSuchKey'){
        return null;
      }
      throw e;
    }
  }

  async function getStatus(
    key: string,
    repos: IRepos
  ): Promise<string | null> {
    if(await getDocument(repos.unprocessed, key)){
      return STATUS_PENDING;
    }else if(await getDocument(repos.batch, key)){
      return STATUS_PROCESSING;
    }else if(await getDocument(repos.processed, key)){
      return STATUS_PROCESSED;
    }else if(await getDocument(repos.invalid, key)){
      return STATUS_INVALID;
    }else{
      return null;
    }
  }

  async function getStatusRequest(Key: string, Repos: IRepos, res: Response){
    const status: string|null = await getStatus(Key, Repos);
    if(status){
      res.send({status});
    }else{
      res.sendStatus(404);
    }
  }


  app.get('/status/issue/:document', async (req: Request, res: Response, next: CallableFunction)=>{
    logger.info('Getting issue document status. Key: "%s"', req.params.document);
    try{
      await getStatusRequest(req.params.document, repos.issue, res);
    }catch(e){
      next(e);
    }
  });
  app.get('/status/revoke/:document', async (req: Request, res: Response, next: CallableFunction)=>{
    logger.info('Getting revoke document status. Key: "%s"', req.params.Key);
    try{
      await getStatusRequest(req.params.document, repos.revoke, res);
    }catch(e){
      next(e);
    }
  });


  return app;
}
