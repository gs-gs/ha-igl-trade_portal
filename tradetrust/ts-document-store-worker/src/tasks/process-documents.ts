import { DocumentStore } from "@govtechsg/document-store/src/contracts/DocumentStore";
import { Wallet } from "ethers";
import {
  Keys,
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocuments,
  UnprocessedDocumentsQueue
} from "src/repos";
import { logger } from 'src/logger';
import ComposeBatch from "./compose-batch";
import { Task } from "./interfaces";
import IssueBatch from "./issue-batch";
import SaveIssuedBatch from "./save-issued-batch";
import WrapBatch from "./wrap-batch";


class ProcessDocuments implements Task<void>{
  constructor(
    private unprocessedDocuments: UnprocessedDocuments,
    private batchDocuments: BatchDocuments,
    private issuedDocuments: IssuedDocuments,
    private unprocessedDocumentsQueue: UnprocessedDocumentsQueue,
    private wallet: Wallet,
    private documentStore: DocumentStore,
    private messageWaitTime: number,
    private maxBatchSizeBytes: number,
    private maxBatchTimeSeconds: number,
    private transactionTimeoutSeconds: number,
    private transactionConfirmationThreshold: number,
    private gasPriceMultiplier: number
  ){}

  async start(){
    while(true){
      await this.next();
    }
  }

  async next(){
    logger.debug('next');
    logger.debug('ComposeBatch');
    const batch = await new ComposeBatch(
      this.unprocessedDocuments,
      this.batchDocuments,
      this.unprocessedDocumentsQueue,
      this.maxBatchTimeSeconds,
      this.maxBatchSizeBytes,
      this.messageWaitTime,
      this.documentStore.address
    ).start()
    logger.debug('batch.isEmpty')
    if(batch.isEmpty()){
      return;
    }
    logger.debug('WrapBatch');
    new WrapBatch(batch).start()
    logger.debug('IssueBatch');
    await new IssueBatch(
      this.wallet,
      this.documentStore,
      batch,
      this.gasPriceMultiplier,
      this.transactionConfirmationThreshold,
      this.transactionTimeoutSeconds
    ).start()
    logger.debug('SaveIssuedBatch');
    await new SaveIssuedBatch(
      this.issuedDocuments,
      this.batchDocuments,
      batch
    ).start()
  }
}

export default ProcessDocuments;
