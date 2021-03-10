import { logger } from '../logger';
import { wrapDocument } from '@govtechsg/open-attestation';
import {
  ComposeBatch,
  Document,
  InvalidDocumentError
} from './compose-batch';


class ComposeIssueBatch extends ComposeBatch{
  async verifyDocument(document: Document){
    try{
      wrapDocument(document.body.json)
    }catch(e){
      if(!!e.validationErrors){
        throw new InvalidDocumentError('Invalid document schema', document);
      }else{
        throw e;
      }
    }
    const version = this.getDocumentVersion(document.body.json);
    const documentStoreAddress = this.getDocumentStoreAddress(document.body.json, version);
    if(documentStoreAddress != this.props.documentStore.address){
      throw new InvalidDocumentError(
        `Expected document store address to be "${this.props.documentStore.address}", got "${documentStoreAddress}"`,
        document
      )
    }
  }
  async addDocumentToBatch(document: Document){
    await this.putDocumentToBatchBackup(document);
    await this.removeDocumentFromUnprocessed(document);
    this.props.batch.unwrappedDocuments.set(document.key, {body: document.body.json, size: document.size});
  }

  async start(){
    logger.info('ComposeIssueBatch task started');
    return super.start();
  }
}

export default ComposeIssueBatch;
