import pino from 'pino';
import {S3, SQS} from './aws';


class Worker{

  logger: pino.Logger

  constructor(name: string){
    this.logger = pino({name, level: process.env.LOG_LEVEL || 'info', enabled: process.env.NOLOG === undefined});
  }

  async sleep(seconds: number){
    return new Promise(resolve=>setTimeout(resolve, seconds * 1000))
  }

  async next(){}
  async init(){}

  async start(){
    await this.init();
    while(true){
      await this.next();
      await this.sleep(1);
      this.logger.info('next');
    }
  }
}

class BatchComposer extends Worker{

}

class BatchWrapper extends Worker{

}

class BatchIssuer extends Worker{

}
