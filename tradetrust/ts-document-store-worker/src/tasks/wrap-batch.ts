import { wrapDocuments } from '@govtechsg/open-attestation';
import { logger } from 'src/logger';
import { Batch } from 'src/tasks/data';
import { Task } from 'src/tasks/interfaces';

interface IWrapBatchProps{
  batch: Batch
}



class WrapBatch implements Task<void>{
  private props: IWrapBatchProps;
  constructor(props: IWrapBatchProps){
    this.props = Object.assign({}, props);
  }

  prepareBatchUnwrappedDocumentsData(){
    const keys:Array<string> = new Array<string>(this.props.batch.unwrappedDocuments.size);
    const bodies: Array<any> = new Array<any>(this.props.batch.unwrappedDocuments.size);
    let documentIndex = 0;
    for(let [key, entry] of this.props.batch.unwrappedDocuments){
      keys[documentIndex] = key;
      bodies[documentIndex] = entry.body;
      documentIndex++;
    }
    return {keys, bodies};
  }

  start(){
    logger.info('WrapBatch task started');
    let {keys, bodies} = this.prepareBatchUnwrappedDocumentsData();
    bodies = wrapDocuments(bodies);
    this.props.batch.wrappedDocuments.clear();
    // size here is irrelevant therefore we're not computing it
    keys.forEach((key, index)=>{this.props.batch.wrappedDocuments.set(key, {body: bodies[index], size: 0})});
    this.props.batch.merkleRoot = bodies[0].signature.merkleRoot;
    logger.info(
      'Completed documents wrapping. Documents count = %s, merkleRoot = %s',
      this.props.batch.wrappedDocuments.size,
      this.props.batch.merkleRoot
    );
  }
}

export default WrapBatch;
