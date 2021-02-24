import { logger } from '../logger';
import {
  SendDocumentStoreTransaction,
  ISendDocumentStoreTransactionProps
} from './send-document-store-transaction';
import { Batch } from './data';


interface IRevokeDocumentProps extends ISendDocumentStoreTransactionProps{
  batch: Batch
}

class RevokeBatch extends SendDocumentStoreTransaction{

  protected props!: IRevokeDocumentProps;

  constructor(props: IRevokeDocumentProps){
    super(props);
  }

  async populateTransaction(){
    const targetHashes = new Array<string>(this.props.batch.wrappedDocuments.size);
    for(let document of this.props.batch.wrappedDocuments.values()){
      targetHashes.push(`0x${document.body.signature.targetHash}`);
    }
    logger.info('Revoking documents batch');
    logger.info(targetHashes);
    return await this.props.documentStore.populateTransaction.bulkRevoke(targetHashes);
  }
  async onComplete(){
    logger.info('Documents batch revoked');
  }
  async onRanOutOfAttemps(){
    logger.error('Documents batch revocation failed');
  }

  async start(){
    logger.info('RevokeBatch task started');
    return super.start();
  }
}


export default RevokeBatch;
