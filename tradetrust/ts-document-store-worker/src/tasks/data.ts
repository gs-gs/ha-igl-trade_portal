import { UnwrappedDocument } from './interfaces';

class Batch{

  public unwrappedDocuments: Map<string, UnwrappedDocument>;
  public wrappedDocuments: Map<string, any>;
  public merkleRoot: string = '';
  public composed: boolean = false;
  public wrapped: boolean = false;
  public issued: boolean = false;
  public saved: boolean = false;

  constructor(){
    this.unwrappedDocuments = new Map<string, UnwrappedDocument>();
    this.wrappedDocuments = new Map<string, any>();
  }
  // size must be computed dynamically in case one of the documents gets replaced during batch composition
  size(): number{
    let size = 0;
    this.unwrappedDocuments.forEach(document=>{size += document.size});
    return size;
  }

  isEmpty(){
    return this.unwrappedDocuments.size == 0;
  }
}


export {
  Batch
}
