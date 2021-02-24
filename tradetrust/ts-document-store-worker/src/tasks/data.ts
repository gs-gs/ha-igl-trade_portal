interface Document{
  size: number,
  body: any
}


class Batch{

  public compositionStartTimestamp:number = -1;

  public unwrappedDocuments: Map<string, Document>;
  public wrappedDocuments: Map<string, Document>;
  public merkleRoot: string = '';

  public restored: boolean = false;
  public composed: boolean = false;

  constructor(){
    this.unwrappedDocuments = new Map<string, Document>();
    this.wrappedDocuments = new Map<string, Document>();
  }
  // size must be computed dynamically in case one of the documents gets replaced during batch composition
  unwrappedDocumentsSize(){
    let size = 0;
    this.unwrappedDocuments.forEach(document=>{size += document.size});
    return size;
  }
  wrappedDocumentsSize(){
    let size = 0;
    this.wrappedDocuments.forEach(document=>{size += document.size});
    return size;
  }
  size(): number{
    return this.unwrappedDocumentsSize() + this.wrappedDocumentsSize();
  }

  isEmpty(){
    return this.unwrappedDocuments.size == 0;
  }

  isComposed(maxSizeBytes: number, maxTimeSeconds: number){
    const time = Date.now() - this.compositionStartTimestamp >= maxTimeSeconds * 1000;
    const size = this.size() >= maxSizeBytes;
    return time || size;
  }
}


export {
  Batch
}
