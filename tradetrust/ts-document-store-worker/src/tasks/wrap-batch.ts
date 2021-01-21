import { wrapDocuments } from '@govtechsg/open-attestation';
import { logger } from '../logger';
import { Batch } from './data';
import { Task } from './interfaces';


class WrapBatch implements Task<void>{
  constructor(private batch: Batch){}

  prepareBatchUnwrappedDocumentsData(){
    logger.debug('prepareBatchUnwrappedDocumentsData');
    const keys:Array<string> = new Array<string>(this.batch.unwrappedDocuments.size);
    const bodies: Array<any> = new Array<any>(this.batch.unwrappedDocuments.size);
    let documentIndex = 0;
    for(let [key, entry] of this.batch.unwrappedDocuments){
      keys[documentIndex] = key;
      bodies[documentIndex] = entry.body;
      documentIndex++;
    }
    return {keys, bodies};
  }

  next(){
    logger.debug('next');
    let {keys, bodies} = this.prepareBatchUnwrappedDocumentsData();
    logger.debug('wrapDocuments');
    bodies = wrapDocuments(bodies);
    logger.debug('batch.wrappedDocuments.set')
    keys.forEach((key, index)=>{this.batch.wrappedDocuments.set(key, bodies[index])});
    logger.debug('batch.merkleRoot = %s', bodies[0].signature.merkleRoot);
    this.batch.merkleRoot = bodies[0].signature.merkleRoot;
  }

  start(){
    logger.debug('start');
    this.next();
  }
}

export default WrapBatch;
