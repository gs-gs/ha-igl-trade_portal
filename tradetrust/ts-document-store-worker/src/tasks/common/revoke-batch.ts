import { logger } from 'src/logger';
import { OpenAttestationVersion as Version } from 'src/constants';
import {
  SendDocumentStoreTransaction,
  ISendDocumentStoreTransactionProps
} from 'src/tasks/common/send-document-store-transaction';
import { Batch } from 'src/tasks/common/data';


export interface IRevokeDocumentProps extends ISendDocumentStoreTransactionProps{
  batch: Batch,
  version?: Version
}

export class RevokeBatch extends SendDocumentStoreTransaction{

  protected props!: IRevokeDocumentProps;
  private getDocumentTargetHash: Function;

  constructor(props: IRevokeDocumentProps){
    super(Object.assign({version: Version.V2}, props));
    if (this.props.version == Version.V2){
      this.getDocumentTargetHash = (document:any)=> document.signature.targetHash;
    }else if(this.props.version == Version.V3){
      this.getDocumentTargetHash = (document:any)=> document.proof.targetHash;
    }else{
      throw new Error(`Unknown version "${this.props.version}"`)
    }
  }

  async populateTransaction(){
    const targetHashes = new Array<string>();
    logger.info('Revoking documents batch');
    for(let document of this.props.batch.wrappedDocuments.values()){
      const targetHash = this.getDocumentTargetHash(document.body);
      logger.info('Target hash %s', `0x${targetHash}`);
      targetHashes.push(`0x${targetHash}`);
    }
    return await this.props.documentStore.populateTransaction.bulkRevoke(targetHashes);
  }
  async onComplete(){
    logger.info('Documents batch revoked');
  }
  async onRanOutOfAttemps(){
    logger.warn('Documents batch revocation failed');
  }

  async start(){
    logger.info('RevokeBatch[%s] task started', this.props.version);
    return super.start();
  }
}
