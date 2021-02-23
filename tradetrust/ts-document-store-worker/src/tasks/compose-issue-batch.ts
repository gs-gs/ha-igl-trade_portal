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
        throw new InvalidDocumentError(`Invalid document schema: ${JSON.stringify(e.validationErrors, null, 4)}`);
      }else{
        throw e;
      }
    }
    const version = this.getDocumentVersion(document);
    const documentStoreAddress = this.getDocumentStoreAddress(document, version);
    if(documentStoreAddress != this.props.documentStoreAddress){
      throw new InvalidDocumentError(
        `Expected document store address to be "${this.props.documentStoreAddress}", got "${documentStoreAddress}"`
      )
    }
  }
  async addDocumentToBatch(document: Document){
    await this.putDocumentToBatchBackup(document);
    await this.removeDocumentFromUnprocessed(document);
    this.props.batch.unwrappedDocuments.set(document.key, {body: document.body.json, size: document.size});
  }
}

export default ComposeIssueBatch;
