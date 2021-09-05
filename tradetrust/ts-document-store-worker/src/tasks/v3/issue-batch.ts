import { signDocument, SUPPORTED_SIGNING_ALGORITHM } from "@govtechsg/open-attestation";
import { OpenAttestationVersion as Version } from 'src/constants';
import { Wallet } from 'ethers';
import { logger }  from 'src/logger';
import { Batch } from 'src/tasks/common/data';
import { Task } from 'src/tasks/common/interfaces';


interface IIssueBatchProps {
  batch: Batch;
  signer: Wallet
}


export class IssueBatch implements Task<Promise<void>>{
  private props: IIssueBatchProps;

  constructor(props: IIssueBatchProps){
    this.props = props;
  }

  async start() {
    logger.info(`IssueBatch[${Version.V3}] task started`)
    logger.info('Signing documents...');
    const { batch, signer } = this.props;
    for(let [key, document] of batch.wrappedDocuments.entries()){
      // updating wrapped documents bodies, because SaveBatch task uses wrapped documents as its data source
      document.body = await signDocument(
        document.body,
        SUPPORTED_SIGNING_ALGORITHM.Secp256k1VerificationKey2018,
        signer
      )
      logger.info('Document "%s" signed', key);
    }
    const document = batch.wrappedDocuments.values().next().value;
    logger.info('Documents batch signing completed. Batch signature %s', document?.body?.proof.signature);
  }
}
