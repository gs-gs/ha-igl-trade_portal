import { logger }  from 'src/logger';
import {
  Batch
} from './data';
import {
  ISendDocumentStoreTransactionProps,
  SendDocumentStoreTransaction
} from 'src/tasks/send-document-store-transaction';

interface IIssueBatchProps extends ISendDocumentStoreTransactionProps{
  batch: Batch;
}

class IssueBatch extends SendDocumentStoreTransaction{

  protected props!: IIssueBatchProps;

  constructor(props: IIssueBatchProps){
    super(props);
  }

  async populateTransaction(){
    const merkleRoot = '0x'+this.props.batch.merkleRoot;
    const transaction = await this.props.documentStore.populateTransaction.issue(merkleRoot);
    return transaction;
  }
  async onComplete() {
    logger.info('Documents batch "%s" issued', this.props.batch.merkleRoot);
  }
  async onRanOutOfAttemps(){
    logger.warn('Documents batch "%s" issuing failed', this.props.batch.merkleRoot);
  }
  async start(){
    logger.info('IssueBatch task started');
    return super.start();
  }
}

export default IssueBatch;
