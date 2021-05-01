import { logger } from 'tests/logger';
import * as Config from 'tests/config';
import { RetryableBucket } from 'tests/repos';
import { documentV2 } from 'tests/data';

describe('Issue document', ()=>{
  jest.setTimeout(600 * 1000);
  test('Valid document', async ()=>{

    const document = documentV2();

    const unprocessed = new RetryableBucket({Bucket: Config.ISSUE_UNPROCESSED_BUCKET});
    const issued = new RetryableBucket({Bucket: Config.ISSUED_BUCKET});

    const Body = JSON.stringify(document);
    const Key = 'valid-document.json';

    await unprocessed.put({Body, Key});
    await issued.get({Attempts: 10, AttemptsInterval: 10, Key});

  });

  test('Invalid document', async ()=>{

  });

  test('Mix: valid & invalid documents', async ()=>{

  });
});
