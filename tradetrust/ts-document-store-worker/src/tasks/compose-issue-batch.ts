import { logger } from '../logger';
import { VerifyDocumentIssuance, VerificationError } from './utils/verify-document';
import {
  ComposeBatch,
  Document,
  InvalidDocumentError,
  IComposeBatchProps
} from './compose-batch';


class ComposeIssueBatch extends ComposeBatch{
  private verificator: VerifyDocumentIssuance;

  constructor(props: IComposeBatchProps){
    super(props);
    this.verificator = new VerifyDocumentIssuance({documentStore:props.documentStore});
  }

  async verifyDocument(document: Document){
    try{
      await this.verificator.verify(document.body.json);
    }catch(e){
      if(e instanceof VerificationError){
        throw new InvalidDocumentError(e.message, document);
      }else{
        throw e;
      }
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
