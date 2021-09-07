const create = require('./app');
const awsServerlessExpress = require('aws-serverless-express');
const Sentry = require("@sentry/serverless");
const app = create();
const server = awsServerlessExpress.createServer(app);

if (process.env.SENTRY_DSN) {
  Sentry.AWSLambda.init({
    dsn: process.env.SENTRY_DSN,
    tracesSampleRate: 1.0,
  });
}

if (process.env.SENTRY_DSN) {
  exports.handler = Sentry.AWSLambda.wrapHandler((event, context, callback) => {
    return awsServerlessExpress.proxy(server, event, context);
  });
}
else {
  exports.handler=(event, context)=>{awsServerlessExpress.proxy(server, event, context)};
}
