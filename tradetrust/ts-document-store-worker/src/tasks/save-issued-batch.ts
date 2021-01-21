import { BatchDocuments, IssuedDocuments } from "src/repos";
import { Batch } from './data';
import { Task } from './interfaces';


class SaveIssuedBatch implements Task<void>{
  constructor(
    private issuedDocuments: IssuedDocuments,
    private batchDocuments: BatchDocuments,
    private batch: Batch
  ){}
  async next(){
    for(let [key, document] of this.batch.wrappedDocuments){
      const documentBodyString = JSON.stringify(document);
      await this.issuedDocuments.put({Key:key, Body: documentBodyString});
      await this.batchDocuments.delete({Key:key})
    }
  }

  async start(){
    await this.next();
  }

}

export default SaveIssuedBatch;
