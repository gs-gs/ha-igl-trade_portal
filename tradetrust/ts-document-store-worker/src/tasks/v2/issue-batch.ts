import { logger }  from 'src/logger';
import { OpenAttestationVersion as Version } from 'src/constants';
import {
  Batch
} from 'src/tasks/common/data';
import {
  ISendDocumentStoreTransactionProps,
  SendDocumentStoreTransaction
} from 'src/tasks/common/send-document-store-transaction';

export interface IIssueBatchProps extends ISendDocumentStoreTransactionProps{
  batch: Batch;
}

export class IssueBatch extends SendDocumentStoreTransaction{

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
    logger.info(`IssueBatch[${Version.V2}] task started`);
    return super.start();
  }
}
