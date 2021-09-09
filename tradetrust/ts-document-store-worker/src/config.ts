import fs from 'fs';
import _ from 'lodash';


function get_env_or_file_value(envVarName: string):string{
  const envVarValue = process.env[envVarName];
  if(envVarValue && fs.existsSync(envVarValue)){
    return fs.readFileSync(envVarValue).toString();
  }else{
    return envVarValue || '';
  }
}

export interface IAWSConfig{
  readonly AWS_ENDPOINT_URL?: string
}

export const getAWSEnvConfig = (): IAWSConfig => ({
  AWS_ENDPOINT_URL: process.env.AWS_ENDPOINT_URL
})

export interface IBatchedTaskConfig {
  readonly UNPROCESSED_QUEUE_URL: string
  readonly INVALID_BUCKET_NAME: string
  readonly UNPROCESSED_BUCKET_NAME: string
  readonly BATCH_BUCKET_NAME: string

  readonly MESSAGE_WAIT_TIME: number,
  readonly MESSAGE_VISIBILITY_TIMEOUT: number,

  readonly BATCH_SIZE_BYTES: number,
  readonly BATCH_TIME_SECONDS: number,

  readonly RESTORE_ATTEMPTS: number,
  readonly RESTORE_ATTEMPTS_INTERVAL_SECONDS: number,

  readonly COMPOSE_ATTEMPTS: number,
  readonly COMPOSE_ATTEMPTS_INTERVAL_SECONDS: number,

  readonly SAVE_ATTEMPTS: number,
  readonly SAVE_ATTEMPTS_INTERVAL_SECONDS: number
}

export const getBatchedTaskEnvConfig = (): IBatchedTaskConfig =>({
  MESSAGE_WAIT_TIME: parseInt(process.env.MESSAGE_WAIT_TIME??'1'),
  MESSAGE_VISIBILITY_TIMEOUT: parseInt(process.env.MESSAGE_VISIBILITY_TIMEOUT??'60'),
  UNPROCESSED_QUEUE_URL: process.env.UNPROCESSED_QUEUE_URL??'',
  INVALID_BUCKET_NAME: process.env.INVALID_BUCKET_NAME??'',
  UNPROCESSED_BUCKET_NAME: process.env.UNPROCESSED_BUCKET_NAME??'',
  BATCH_BUCKET_NAME: process.env.BATCH_BUCKET_NAME??'',
  // default 100 MB
  BATCH_SIZE_BYTES: parseInt(process.env.BATCH_SIZE_BYTES??'104857600'),
  // 10 minutes
  BATCH_TIME_SECONDS: parseInt(process.env.BATCH_TIME_SECONDS??'600'),

  RESTORE_ATTEMPTS: parseInt(process.env.RESTORE_ATTEMPTS??'10'),
  RESTORE_ATTEMPTS_INTERVAL_SECONDS: parseInt(process.env.RESTORE_ATTEMPTS_INTERVAL_SECONDS??'60'),

  COMPOSE_ATTEMPTS: parseInt(process.env.COMPOSE_ATTEMPTS??'10'),
  COMPOSE_ATTEMPTS_INTERVAL_SECONDS: parseInt(process.env.RESTORE_ATTEMPTS_INTERVAL_SECONDS??'60'),

  SAVE_ATTEMPTS: parseInt(process.env.SAVE_ATTEMPTS??'10'),
  SAVE_ATTEMPTS_INTERVAL_SECONDS: parseInt(process.env.SAVE_ATTEMPTS_INTERVAL_SECONDS??'60')
})

export interface IIssueTaskConfig{
  readonly ISSUED_BUCKET_NAME: string,
  readonly ISSUE_ATTEMPTS: number,
  readonly ISSUE_ATTEMPTS_INTERVAL_SECONDS: number,
}

export const getIssueTaskEnvConfig = ():IIssueTaskConfig =>({
  ISSUED_BUCKET_NAME: process.env.ISSUED_BUCKET_NAME??'',
  ISSUE_ATTEMPTS: parseInt(process.env.ISSUE_ATTEMPTS??'10'),
  ISSUE_ATTEMPTS_INTERVAL_SECONDS: parseInt(process.env.ISSUE_ATTEMPTS_INTERVAL_SECONDS??'60')
})

export interface IRevokeTaskConfig{
  readonly REVOKED_BUCKET_NAME: string,
  readonly REVOKE_ATTEMPTS: number,
  readonly REVOKE_ATTEMPTS_INTERVAL_SECONDS: number,
}

export const getRevokeTaskEnvConfig = ():IRevokeTaskConfig =>({
  REVOKED_BUCKET_NAME: process.env.REVOKED_BUCKET_NAME??'',
  REVOKE_ATTEMPTS: parseInt(process.env.REVOKE_ATTEMPTS??'10'),
  REVOKE_ATTEMPTS_INTERVAL_SECONDS: parseInt(process.env.REVOKE_ATTEMPTS_INTERVAL_SECONDS??'60')
})

export interface ITransactionTaskConfig{
  readonly GAS_PRICE_MULTIPLIER: number,
  readonly GAS_PRICE_LIMIT_GWEI: number,

  readonly TRANSACTION_TIMEOUT_SECONDS: number,
  readonly TRANSACTION_CONFIRMATION_THRESHOLD: number
}

export const getTransactionTaskEnvConfig = ():ITransactionTaskConfig=>({
  TRANSACTION_TIMEOUT_SECONDS: parseInt(process.env.TRANSACTION_TIMEOUT_SECONDS??'600'),
  TRANSACTION_CONFIRMATION_THRESHOLD: parseInt(process.env.TRANSACTION_CONFIRMATION_THRESHOLD??'12'),
  // 1.2
  GAS_PRICE_MULTIPLIER: parseFloat(process.env.GAS_PRICE_MULTIPLIER??'1.2'),
  GAS_PRICE_LIMIT_GWEI: parseInt(process.env.GAS_PRICE_LIMIT_GWEI??'200')
})

export interface IDocumentStoreTaskConfig{
  readonly BLOCKCHAIN_ENDPOINT: string

  readonly DOCUMENT_STORE_OWNER_PUBLIC_KEY: string,
  readonly DOCUMENT_STORE_OWNER_PRIVATE_KEY: string
  readonly DOCUMENT_STORE_ADDRESS: string
}

export const getDocumentStoreTaskEnvConfig = ():IDocumentStoreTaskConfig =>({
  BLOCKCHAIN_ENDPOINT: process.env.BLOCKCHAIN_ENDPOINT??'',
  DOCUMENT_STORE_ADDRESS: get_env_or_file_value('DOCUMENT_STORE_ADDRESS'),
  DOCUMENT_STORE_OWNER_PUBLIC_KEY: process.env.DOCUMENT_STORE_OWNER_PUBLIC_KEY??'',
  DOCUMENT_STORE_OWNER_PRIVATE_KEY: process.env.DOCUMENT_STORE_OWNER_PRIVATE_KEY??''
});

export interface ISignerTaskConfig{
  PRIVATE_KEY: string,
  PUBLIC_KEY: string
}

export const getSignerTaskEnvConfig = ():ISignerTaskConfig =>({
  PRIVATE_KEY: process.env.PRIVATE_KEY??'',
  PUBLIC_KEY: process.env.PUBLIC_KEY??''
})

export interface IBatchedIssueConfig extends IAWSConfig, IBatchedTaskConfig, IDocumentStoreTaskConfig, ITransactionTaskConfig, IIssueTaskConfig{}

export const getBatchedIssueEnvConfig = (): IBatchedIssueConfig => ({
  ...getAWSEnvConfig(),
  ...getBatchedTaskEnvConfig(),
  ...getDocumentStoreTaskEnvConfig(),
  ...getTransactionTaskEnvConfig(),
  ...getIssueTaskEnvConfig()
});

export interface IBatchedRevokeConfig extends IAWSConfig, IBatchedTaskConfig, IDocumentStoreTaskConfig, ITransactionTaskConfig, IRevokeTaskConfig{}

export const getBatchedRevokeEnvConfig = (): IBatchedRevokeConfig => ({
  ...getAWSEnvConfig(),
  ...getBatchedTaskEnvConfig(),
  ...getDocumentStoreTaskEnvConfig(),
  ...getTransactionTaskEnvConfig(),
  ...getRevokeTaskEnvConfig()
});

export interface IBatchedSignerConfig extends IAWSConfig, IBatchedTaskConfig, IDocumentStoreTaskConfig, IIssueTaskConfig{}

export const getBatchedSignerEnvConfig = (): IBatchedSignerConfig => ({
  ...getAWSEnvConfig(),
  ...getBatchedTaskEnvConfig(),
  ...getDocumentStoreTaskEnvConfig(),
  ...getIssueTaskEnvConfig()
});


export const hideSecrets = (config: any, secrets?: Array<string>): any => {
  secrets = secrets??['DOCUMENT_STORE_OWNER_PRIVATE_KEY'];
  config = _.cloneDeep(config);
  for(let key of secrets){
    let original = config[key];
    if(original !== undefined){
      original = original.toString();
      config[key] = '*'.repeat(original.length)
    }
  }
  return config;
}
