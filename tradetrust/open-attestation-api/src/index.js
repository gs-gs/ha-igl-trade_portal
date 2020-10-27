const create = require('./app');
const awsServerlessExpress = require('aws-serverless-express');

const app = create();
const server = awsServerlessExpress.createServer(app);

exports.handler=(event, context)=>{awsServerlessExpress.proxy(server, event, context)};
