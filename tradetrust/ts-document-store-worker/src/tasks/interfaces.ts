interface UnwrappedDocument{
  size: number,
  body: any
}


interface Task<T>{
  start(): T;
  next(): void
}


export {
  Task,
  UnwrappedDocument
}
