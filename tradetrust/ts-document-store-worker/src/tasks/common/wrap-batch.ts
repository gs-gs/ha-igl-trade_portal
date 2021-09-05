import {
  wrapDocuments as wrapDocumentsV2,
  __unsafe__use__it__at__your__own__risks__wrapDocuments as wrapDocumentsV3
} from '@govtechsg/open-attestation';
import { logger } from 'src/logger';
import { OpenAttestationVersion as Version } from 'src/constants';
import { Batch } from 'src/tasks/common/data';
import { Task } from 'src/tasks/common/interfaces';

export interface IWrapBatchProps{
  batch: Batch,
  version?: Version
}


export class WrapBatch implements Task<Promise<void>>{
  private props: IWrapBatchProps;
  private wrapDocuments: Function;
  private getMerkleRoot: Function;
  constructor(props: IWrapBatchProps){
    this.props = Object.assign({version: Version.V2}, props);
    if(this.props.version == Version.V2){
      this.wrapDocuments = async (documents: Array<any>)=>wrapDocumentsV2(documents);
      this.getMerkleRoot = (document: any)=>document.signature.merkleRoot
    }else if(this.props.version == Version.V3){
      this.wrapDocuments = async (documents: Array<any>)=>await wrapDocumentsV3(documents);
      this.getMerkleRoot = (document: any)=>document.proof.merkleRoot
    }else{
      throw new Error(`Unknown version "${this.props.version}"`);
    }
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

  async start(){
    logger.info('WrapBatch[%s] task started', this.props.version);
    let {keys, bodies} = this.prepareBatchUnwrappedDocumentsData();
    bodies = await this.wrapDocuments(bodies);
    this.props.batch.wrappedDocuments.clear();
    // size here is irrelevant therefore we're not computing it
    keys.forEach((key, index)=>{this.props.batch.wrappedDocuments.set(key, {body: bodies[index], size: 0})});
    this.props.batch.merkleRoot = this.getMerkleRoot(bodies[0]);
    logger.info(
      'Completed documents wrapping. Documents count = %s, merkleRoot = %s',
      this.props.batch.wrappedDocuments.size,
      this.props.batch.merkleRoot
    );
  }
}
