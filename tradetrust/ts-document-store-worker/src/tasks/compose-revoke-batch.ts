import { verifySignature, validateSchema, getData } from '@govtechsg/open-attestation';
import { logger } from '../logger';
import {
  ComposeBatch,
  Document,
  InvalidDocumentError
} from './compose-batch';


class ComposeRevokeBatch extends ComposeBatch{

  async verifyDocument(document: Document){
    if(!validateSchema(document.body.json)){
      throw new InvalidDocumentError('Invalid document schema');
    }
    if(!verifySignature(document.body.json)){
      throw new InvalidDocumentError('Invalid document signature');
    }
    const unwrappedDocumentData = getData(document.body.json);
    const version = this.getDocumentVersion(unwrappedDocumentData);
    const documentStoreAddress = this.getDocumentStoreAddress(unwrappedDocumentData, version);
    if(documentStoreAddress != this.props.documentStore.address){
      throw new InvalidDocumentError(
        `Expected document store address to be "${this.props.documentStore.address}", got "${documentStoreAddress}"`
      )
    }
    // A document must not be revoked previosly, attempts to revoke revoked documents cause an error
    const targetHash = `0x${document.body.json.signature.targetHash}`;
    if(await this.props.documentStore.isRevoked(targetHash)){
      throw new InvalidDocumentError(`Document ${targetHash} already revoked`);
    }
  }

  async addDocumentToBatch(document: Document){
    await this.putDocumentToBatchBackup(document);
    await this.removeDocumentFromUnprocessed(document);
    this.props.batch.wrappedDocuments.set(document.key, {body: document.body.json, size: document.size});
  }

  async start(){
    logger.info('ComposeRevokeBatch task started');
    return super.start();
  }
}

export default ComposeRevokeBatch;
