import app from './app';
import awsServerlessExpress from 'aws-serverless-express';
import Sentry from "@sentry/serverless";
const server = awsServerlessExpress.createServer(app());

if (process.env.SENTRY_DSN) {
  Sentry.AWSLambda.init({
    dsn: process.env.SENTRY_DSN,
    tracesSampleRate: 1.0,
  });
}

let handler = null;

if (process.env.SENTRY_DSN) {
  handler = Sentry.AWSLambda.wrapHandler(async (event: any, context: any) => {
    return awsServerlessExpress.proxy(server, event, context);
  });
}
else {
  handler = (event: any, context: any)=>{awsServerlessExpress.proxy(server, event, context)};
}

export default handler;
