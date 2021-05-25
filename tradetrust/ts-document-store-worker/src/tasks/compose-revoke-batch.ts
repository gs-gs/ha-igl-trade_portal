import { VerifyDocumentRevocation, VerificationError } from 'src/tasks/utils/verify-document';
import { logger } from 'src/logger';
import {
  ComposeBatch,
  Document,
  InvalidDocumentError,
  IComposeBatchProps
} from 'src/tasks/compose-batch';


class ComposeRevokeBatch extends ComposeBatch{
  private verificator: VerifyDocumentRevocation;

  constructor(props: IComposeBatchProps){
    super(props);
    this.verificator = new VerifyDocumentRevocation({documentStore: props.documentStore});
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
    this.props.batch.wrappedDocuments.set(document.key, {body: document.body.json, size: document.size});
  }

  async start(){
    logger.info('ComposeRevokeBatch task started');
    return super.start();
  }
}

export default ComposeRevokeBatch;
