import _ from 'lodash';
import Transport from 'winston-transport';
import { createLogger, format, transports } from 'winston';
import { SentryTransport } from 'src/logger-sentry-transport';

const LOGGER_OPTS = {
  level: 'info',
  transports: new Array<Transport>()
}


if(process.env.SENTRY_DSN && process.env.USE_SENTRY){
  /* istanbul ignore next */
  LOGGER_OPTS.transports.push(new SentryTransport({
    format: format.combine(
      format.errors({stack: true}),
      format.splat()
    ),
    levels: {
      event: [
        'error'
      ],
      breadcrumbs: [
        'info',
        'warn'
      ]
    },
    sentry: {
      dsn: process.env.SENTRY_DSN
    }
  }));
}


if(process.env.CONSOLE_LOGS || LOGGER_OPTS.transports.length == 0){
  LOGGER_OPTS.transports.push(new transports.Console({
    format: format.combine(
      format.errors({stack: true}),
      format.splat(),
      format.colorize(),
      format.align(),
      format.printf(info=>{
        return `${info.level}:${info.message}${info.stack?'\n'+info.stack:''}`
      })
    )
  }))
}


const logger = createLogger(LOGGER_OPTS);

export { logger };
