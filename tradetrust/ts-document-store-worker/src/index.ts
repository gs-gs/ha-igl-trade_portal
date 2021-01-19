import pino from 'pino';
import {ComposeBatch} from './tasks';
import {UnprocessedDocumentsQueue, UnprocessedDocuments, BatchDocuments} from './repos';


async function main(){
  const unprocessedDocuments = new UnprocessedDocuments();
  const batchDocuments = new BatchDocuments();
  const unprocessedDocumentsQueue = new UnprocessedDocumentsQueue();

  const logger = pino({level: 'debug'});
  const composeBatch = new ComposeBatch(
    unprocessedDocuments,
    batchDocuments,
    unprocessedDocumentsQueue,
    1024,
    600,
    20
  );
  const documentBody = JSON.stringify({
    body: "Hello world"
  });
  await unprocessedDocuments.put({Key: 'hello-document', Body: documentBody});
  composeBatch.start();
}

main();
