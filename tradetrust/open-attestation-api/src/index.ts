import app from './app';
import awsServerlessExpress from 'aws-serverless-express';

const server = awsServerlessExpress.createServer(app());

export default (event: any, context: any)=>{awsServerlessExpress.proxy(server, event, context)};
