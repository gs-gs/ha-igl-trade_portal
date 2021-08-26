import { logger } from 'src/logger';
import { VerifyDocumentIssuanceV2, VerificationError } from 'src/tasks/utils/verify-document';
import {
  ComposeBatch,
  Document,
  InvalidDocumentError,
  IComposeBatchProps
} from 'src/tasks/common/compose-batch';


class V2ComposeIssueBatch extends ComposeBatch{
  private verificator: VerifyDocumentIssuanceV2;

  constructor(props: IComposeBatchProps){
    super(props);
    this.verificator = new VerifyDocumentIssuanceV2({documentStore:props.documentStore});
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

export default V2ComposeIssueBatch;
