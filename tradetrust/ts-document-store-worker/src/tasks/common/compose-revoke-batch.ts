import { logger } from 'src/logger';
import { OpenAttestationVersion as Version } from 'src/constants';
import {
  VerifyDocumentRevocationV2,
  VerifyDocumentRevocationV3,
  VerificationError
} from 'src/tasks/utils/verify-document';
import {
  ComposeBatch,
  Document,
  InvalidDocumentError,
  IComposeBatchProps
} from 'src/tasks/common/compose-batch';

export interface IComposeRevokeBatchProps extends IComposeBatchProps{
  version?:Version
}

export class ComposeRevokeBatch extends ComposeBatch{
  private verificator: VerifyDocumentRevocationV2|VerifyDocumentRevocationV3;

  constructor(props: IComposeRevokeBatchProps){
    super(Object.assign({version: Version.V2}, props));
    if(this.props.version == Version.V2){
      this.verificator = new VerifyDocumentRevocationV2({documentStore: props.documentStore});
    }else if(this.props.version == Version.V3){
      this.verificator = new VerifyDocumentRevocationV3({documentStore: props.documentStore});
    }else{
      throw new Error(`Unknown version "${this.props.version}"`);
    }
  }

  async verifyDocument(document: Document){
    try{
      await this.verificator.verify(document.body.json);
    }catch(e){
      if(e instanceof VerificationError){
        if(e.details){
          logger.warn(e.details);
        }
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
    logger.info('ComposeRevokeBatch[%s] task started', this.props.version);
    return super.start();
  }
}
