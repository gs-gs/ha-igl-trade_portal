import { logger } from 'src/logger';
import {
  SendDocumentStoreTransaction,
  ISendDocumentStoreTransactionProps
} from 'src/tasks/common/send-document-store-transaction';
import { Batch } from 'src/tasks/common/data';


interface IRevokeDocumentProps extends ISendDocumentStoreTransactionProps{
  batch: Batch
}

class RevokeBatch extends SendDocumentStoreTransaction{

  protected props!: IRevokeDocumentProps;

  constructor(props: IRevokeDocumentProps){
    super(props);
  }

  async populateTransaction(){
    const targetHashes = new Array<string>();
    logger.info('Revoking documents batch');
    for(let document of this.props.batch.wrappedDocuments.values()){
      logger.info('Target hash %s', `0x${document.body.signature.targetHash}`);
      targetHashes.push(`0x${document.body.signature.targetHash}`);
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
    logger.info('RevokeBatch task started');
    return super.start();
  }
}


export default RevokeBatch;
