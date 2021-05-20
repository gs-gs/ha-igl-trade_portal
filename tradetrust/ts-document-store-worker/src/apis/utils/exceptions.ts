import { Request, Response } from "express";
import { logger } from 'src/logger';

export class UserFriendlyError extends Error{}

export function handler(err: any, req: Request, res:Response, next: CallableFunction){
  if(err instanceof UserFriendlyError){
    res.status(400).send({error: err.message});
  }else if (err.status == 400) {
    res.status(400).send({error: err.type});
  }else{
    res.status(500).send({error: 'Internal server error'});
    logger.error('Error:', err);
  }
}
