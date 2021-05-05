import fs from 'fs';

function get_env_or_file_value(envVarName: string):string{
  const envVarValue = process.env[envVarName];
  if(envVarValue && fs.existsSync(envVarValue)){
    return fs.readFileSync(envVarValue).toString();
  }else{
    return envVarValue || '';
  }
}


const LOG_LEVEL:string = process.env.LOG_LEVEL??'info';
const DOCUMENT_STORE_ADDRESS:string = get_env_or_file_value('DOCUMENT_STORE_ADDRESS');
const AWS_ENDPOINT_URL:string = process.env.AWS_ENDPOINT_URL??'';


export {
  LOG_LEVEL,
  DOCUMENT_STORE_ADDRESS,
  AWS_ENDPOINT_URL
}
