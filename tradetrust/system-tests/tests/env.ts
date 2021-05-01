const LOG_LEVEL:string = process.env.LOG_LEVEL??'info';
const DOCUMENT_STORE_ADDRESS:string = process.env.DOCUMENT_STORE_ADDRESS??'';
const AWS_ENDPOINT_URL:string = process.env.AWS_ENDPOINT_URL??'';


export {
  LOG_LEVEL,
  DOCUMENT_STORE_ADDRESS,
  AWS_ENDPOINT_URL
}
