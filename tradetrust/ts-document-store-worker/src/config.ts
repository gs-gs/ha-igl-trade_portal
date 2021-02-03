import fs from 'fs';


function get_env_or_file_value(envVarName: string):string{
  const envVarValue = process.env[envVarName];
  if(envVarValue && fs.existsSync(envVarValue)){
    return fs.readFileSync(envVarValue).toString();
  }else{
    return envVarValue || '';
  }
}


interface ConfigInterface{
  readonly AWS_ENDPOINT_URL?: string

  readonly BLOCKCHAIN_ENDPOINT: string

  readonly DOCUMENT_STORE_OWNER_PRIVATE_KEY: string
  readonly DOCUMENT_STORE_ADDRESS: string

  readonly UNPROCESSED_QUEUE_URL: string
  readonly UNPROCESSED_BUCKET_NAME: string
  readonly ISSUED_BUCKET_NAME: string
  readonly BATCH_BUCKET_NAME: string

  readonly MESSAGE_WAIT_TIME: number,
  readonly MESSAGE_VISIBILITY_TIMEOUT: number,
  readonly TRANSACTION_TIMEOUT_SECONDS: number,
  readonly TRANSACTION_CONFIRMATION_THRESHOLD: number,

  readonly GAS_PRICE_MULTIPLIER: number,
  readonly GAS_PRICE_LIMIT_GWEI: number,

  readonly BATCH_SIZE_BYTES: number,
  readonly BATCH_TIME_SECONDS: number,

  readonly ISSUE_ATTEMPTS: number,
  readonly ISSUE_ATTEMPTS_INTERVAL_SECONDS: number,

  readonly SAVE_ATTEMPTS: number,
  readonly SAVE_ATTEMPTS_INTERVAL_SECONDS: number
}


const config:ConfigInterface = {
  AWS_ENDPOINT_URL: process.env.AWS_ENDPOINT_URL,
  UNPROCESSED_QUEUE_URL: process.env.UNPROCESSED_QUEUE_URL??'',
  UNPROCESSED_BUCKET_NAME: process.env.UNPROCESSED_BUCKET_NAME??'',
  BATCH_BUCKET_NAME: process.env.BATCH_BUCKET_NAME??'',
  ISSUED_BUCKET_NAME: process.env.ISSUED_BUCKET_NAME??'',

  BLOCKCHAIN_ENDPOINT: process.env.BLOCKCHAIN_ENDPOINT??'',

  DOCUMENT_STORE_ADDRESS: get_env_or_file_value('DOCUMENT_STORE_ADDRESS'),
  DOCUMENT_STORE_OWNER_PRIVATE_KEY: process.env.DOCUMENT_STORE_OWNER_PRIVATE_KEY??'',

  MESSAGE_WAIT_TIME: parseInt(process.env.MESSAGE_WAIT_TIME??'1'),
  MESSAGE_VISIBILITY_TIMEOUT: parseInt(process.env.MESSAGE_VISIBILITY_TIMEOUT??'60'),
  TRANSACTION_TIMEOUT_SECONDS: parseInt(process.env.TRANSACTION_TIMEOUT_SECONDS??'600'),
  TRANSACTION_CONFIRMATION_THRESHOLD: parseInt(process.env.TRANSACTION_CONFIRMATION_THRESHOLD??'12'),
  // 1.2
  GAS_PRICE_MULTIPLIER: parseFloat(process.env.GAS_PRICE_MULTIPLIER??'1.2'),
  GAS_PRICE_LIMIT_GWEI: parseInt(process.env.GAS_PRICE_LIMIT_GWEI??'200'),
  // default 100 MB
  BATCH_SIZE_BYTES: parseInt(process.env.MAX_BATCH_SIZE_BYTES??'104857600'),
  // 10 minutes
  BATCH_TIME_SECONDS: parseInt(process.env.MAX_BATCH_TIME_SECONDS??'600'),

  SAVE_ATTEMPTS: parseInt(process.env.SAVE_ATTEMPTS??'10'),
  SAVE_ATTEMPTS_INTERVAL_SECONDS: parseInt(process.env.SAVE_ATTEMPTS_INTERVAL_SECONDS??'60'),

  ISSUE_ATTEMPTS: parseInt(process.env.ISSUE_ATTEMPTS??'10'),
  ISSUE_ATTEMPTS_INTERVAL_SECONDS: parseInt(process.env.ISSUE_ATTEMPTS_INTERVAL_SECONDS??'60')
}

export default config;
