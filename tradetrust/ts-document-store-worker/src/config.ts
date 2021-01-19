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
  readonly BLOCKCHAIN_GAS_PRICE: string
  readonly BLOCKCHAIN_GAS_PRICE_REFRESH_RATE: number

  readonly DOCUMENT_STORE_OWNER_PRIVATE_KEY: string
  readonly DOCUMENT_STORE_OWNER_PUBLIC_KEY: string
  readonly DOCUMENT_STORE_ADDRESS: string

  readonly UNPROCESSED_QUEUE_URL: string
  readonly UNPROCESSED_BUCKET_NAME: string
  readonly ISSUED_BUCKET_NAME: string
  readonly BATCH_BUCKET_NAME: string
}


const config:ConfigInterface = {
  AWS_ENDPOINT_URL: process.env.AWS_ENDPOINT_URL,
  UNPROCESSED_QUEUE_URL: process.env.UNPROCESSED_QUEUE_URL || '',
  UNPROCESSED_BUCKET_NAME: process.env.UNPROCESSED_BUCKET_NAME || '',
  BATCH_BUCKET_NAME: process.env.BATCH_BUCKET_NAME || '',
  ISSUED_BUCKET_NAME: process.env.ISSUED_BUCKET_NAME || '',

  BLOCKCHAIN_ENDPOINT: process.env.BLOCKCHAIN_ENDPOINT || '',
  BLOCKCHAIN_GAS_PRICE: process.env.BLOCKCHAIN_GAS_PRICE || '',
  BLOCKCHAIN_GAS_PRICE_REFRESH_RATE: parseInt(process.env.BLOCKCHAIN_GAS_PRICE_REFRESH_RATE || '10'),

  DOCUMENT_STORE_ADDRESS: get_env_or_file_value('DOCUMENT_STORE_ADDRESS'),
  DOCUMENT_STORE_OWNER_PUBLIC_KEY: process.env.DOCUMENT_STORE_OWNER_PUBLIC_KEY || '',
  DOCUMENT_STORE_OWNER_PRIVATE_KEY: process.env.DOCUMENT_STORE_OWNER_PRIVATE_KEY || ''
}

export default config;
