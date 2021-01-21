import { DocumentStore } from "@govtechsg/document-store/src/contracts/DocumentStore";
import { Wallet } from "ethers";
import {
  BatchDocuments,
  IssuedDocuments,
  UnprocessedDocuments,
  UnprocessedDocumentsQueue
} from "src/repos";
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
    private maxBatchTimeSeconds: number
  ){}

  async start(){
    while(true){
      await this.next();
    }
  }

  async next(){
    const batch = await new ComposeBatch(
      this.unprocessedDocuments,
      this.batchDocuments,
      this.unprocessedDocumentsQueue,
      this.maxBatchSizeBytes,
      this.maxBatchTimeSeconds,
      this.messageWaitTime,
      this.documentStore.address
    ).start()
    new WrapBatch(batch).start()
    await new IssueBatch(
      this.wallet,
      this.documentStore,
      batch
    ).start()
    await new SaveIssuedBatch(
      this.issuedDocuments,
      this.batchDocuments,
      batch
    ).start()
  }
}

export default ProcessDocuments;
