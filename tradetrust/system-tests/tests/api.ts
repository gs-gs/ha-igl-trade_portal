import fetch from 'node-fetch';
import { logger } from 'tests/logger';
import {
  STATUS_TRACKING_API_HOST
} from 'tests/config';


async function getStatusFromStatusTrackingAPI(url: string, key: string){
  const requestUrl = `${STATUS_TRACKING_API_HOST}${url}${key}`;
  logger.info('GET %s', requestUrl);
  const res = await fetch(requestUrl);
  const simpleRes = {
    status: res.status,
    body: await res.json()
  }
  logger.info('RESPONSE: %O', simpleRes);
  return simpleRes;
}

export async function getRevokeDocumentStatus(key: string){
  return await getStatusFromStatusTrackingAPI('/status/revoke/', key);
}

export async function getIssueDocumentStatus(key: string){
  return await getStatusFromStatusTrackingAPI('/status/issue/', key);
}
