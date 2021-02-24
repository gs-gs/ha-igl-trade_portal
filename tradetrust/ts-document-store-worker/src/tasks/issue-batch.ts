import {
  SendDocumentStoreBatchTransaction
} from './send-document-store-batch-transaction';

class IssueBatch extends SendDocumentStoreBatchTransaction{
  async populateTransaction(){
    const merkleRoot = '0x'+this.props.batch.merkleRoot;
    const transaction = await this.props.documentStore.populateTransaction.issue(merkleRoot);
    return transaction;
  }
}

export default IssueBatch;
