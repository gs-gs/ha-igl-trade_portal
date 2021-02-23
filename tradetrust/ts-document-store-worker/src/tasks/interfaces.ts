interface Task<T>{
  start(): T;
  next(): void
}


export {
  Task
}
