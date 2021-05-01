import { logger } from 'tests/logger';
import * as AWS from 'tests/aws';
import * as Config from 'tests/config';


const S3 = AWS.S3();
const SQS = AWS.SQS();

describe('issue-document', ()=>{
  test('test', async ()=>{
    await S3.putObject({
      Bucket: Config.ISSUE_UNPROCESSED_BUCKET,
      Body: 'TEST FILE',
      Key: 'test-file.json'
    }).promise();
    logger.info('File sent');
  });
});
