class CriticalError extends Error{}


class RetryError extends Error{
  public source: Error;
  constructor(source: Error){
    super('Retry error');
    this.source = source;
  }
}


export {
  CriticalError,
  RetryError
}
