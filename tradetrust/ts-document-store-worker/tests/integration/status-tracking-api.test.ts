import chai from 'chai';
import chaiHttp from 'chai-http';
import { Bucket } from 'src/repos';
import { api } from 'src/apis/status-tracking';
import { getStatusTrackingAPIConfig } from 'src/config';
import { clearBucket } from 'tests/utils';


chai.use(chaiHttp);
chai.should();


describe('Status tracking API', ()=>{
  const app = api();
  const config = getStatusTrackingAPIConfig();
  async function getRepos(){
    await clearBucket(config.ISSUE_UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.ISSUE_BATCH_BUCKET_NAME);
    await clearBucket(config.ISSUE_INVALID_BUCKET_NAME);
    await clearBucket(config.ISSUED_BUCKET_NAME);

    await clearBucket(config.REVOKE_UNPROCESSED_BUCKET_NAME);
    await clearBucket(config.REVOKE_BATCH_BUCKET_NAME);
    await clearBucket(config.REVOKE_INVALID_BUCKET_NAME);
    await clearBucket(config.REVOKED_BUCKET_NAME);

    return {
      issue: {
        unprocessed: new Bucket(config.ISSUE_UNPROCESSED_BUCKET_NAME),
        batch: new Bucket(config.ISSUE_BATCH_BUCKET_NAME),
        invalid: new Bucket(config.ISSUE_INVALID_BUCKET_NAME),
        processed: new Bucket(config.ISSUED_BUCKET_NAME)
      },
      revoke: {
        unprocessed: new Bucket(config.REVOKE_UNPROCESSED_BUCKET_NAME),
        batch: new Bucket(config.REVOKE_BATCH_BUCKET_NAME),
        invalid: new Bucket(config.REVOKE_INVALID_BUCKET_NAME),
        processed: new Bucket(config.REVOKED_BUCKET_NAME)
      }
    }
  }

  async function testStatus(props:{
    status: string,
    repo: Bucket,
    key: string,
    body: string,
    url: string
  }){
    await props.repo.put({Key:props.key, Body:props.body});
    const res = await chai.request(app).get(`${props.url}${props.key}`);
    expect(res.status).toBe(200);
    res.body.should.deep.equal({
      status: props.status
    });
  }

  test('status pending', async ()=>{
    const repos = await getRepos();
    await testStatus({
      status: 'pending',
      repo: repos.issue.unprocessed,
      key: 'unprocessed-issue-document',
      body: 'unprocessed-issue-document-body',
      url: '/status/issue/'
    });

    await testStatus({
      status: 'pending',
      repo: repos.revoke.unprocessed,
      key: 'unprocessed-revoke-document',
      body: 'unprocessed-revoke-document-body',
      url: '/status/revoke/'
    });
  })
  test('status processing', async ()=>{
    const repos = await getRepos();
    await testStatus({
      status: 'processing',
      repo: repos.issue.batch,
      key: 'unprocessed-issue-document',
      body: 'unprocessed-issue-document-body',
      url: '/status/issue/'
    });

    await testStatus({
      status: 'processing',
      repo: repos.revoke.batch,
      key: 'unprocessed-revoke-document',
      body: 'unprocessed-revoke-document-body',
      url: '/status/revoke/'
    });
  })
  test('status processed', async ()=>{
    const repos = await getRepos();
    await testStatus({
      status: 'processed',
      repo: repos.issue.processed,
      key: 'unprocessed-issue-document',
      body: 'unprocessed-issue-document-body',
      url: '/status/issue/'
    });

    await testStatus({
      status: 'processed',
      repo: repos.revoke.processed,
      key: 'unprocessed-revoke-document',
      body: 'unprocessed-revoke-document-body',
      url: '/status/revoke/'
    });
  })
  test('status invalid', async ()=>{
    const repos = await getRepos();
    await testStatus({
      status: 'invalid',
      repo: repos.issue.invalid,
      key: 'unprocessed-issue-document',
      body: 'unprocessed-issue-document-body',
      url: '/status/issue/'
    });

    await testStatus({
      status: 'invalid',
      repo: repos.revoke.invalid,
      key: 'unprocessed-revoke-document',
      body: 'unprocessed-revoke-document-body',
      url: '/status/revoke/'
    });
  })
  test('status not found', async ()=>{
    // clearing repos
    await getRepos();
    let Key, res;
    Key = 'not-found-document';

    res = await chai.request(app).get(`/status/issue/${Key}`);
    expect(res.status).toBe(404);

    res = await chai.request(app).get(`/status/revoke/${Key}`);
    expect(res.status).toBe(404);
  })
});
