import { UnwrappedDocument } from './interfaces';

class Batch{

  public creationTimestampMs: number = 0
  public unwrappedDocuments: Map<string, UnwrappedDocument>;
  public wrappedDocuments: Map<string, any>;
  public merkleRoot: string = '';

  constructor(){
    this.creationTimestampMs = Date.now();
    this.unwrappedDocuments = new Map<string, UnwrappedDocument>();
    this.wrappedDocuments = new Map<string, any>();
  }
  // size must be computed dynamically in case one of the documents gets replaced during batch composition
  size(): number{
    let size = 0;
    this.unwrappedDocuments.forEach(document=>{size += document.size});
    return size;
  }
}


export {
  Batch
}
