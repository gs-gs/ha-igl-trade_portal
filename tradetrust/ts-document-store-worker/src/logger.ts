import _ from 'lodash';
import { LEVEL } from 'triple-beam';
import * as Sentry from "@sentry/node";
import Transport from 'winston-transport';
import { createLogger, format, transports } from 'winston';

interface SeverityOptions {
  [key: string]: Sentry.Severity;
}

const SENTRY_LEVELS_MAP: SeverityOptions = {
  silly: Sentry.Severity.Debug,
  verbose: Sentry.Severity.Debug,
  info: Sentry.Severity.Info,
  debug: Sentry.Severity.Debug,
  warn: Sentry.Severity.Warning,
  error: Sentry.Severity.Error,
};


interface SentryTransportOptions extends Transport.TransportStreamOptions{
  sentry: Sentry.NodeOptions,
  levels: {
    breadcrumbs: Array<string>
    event: Array<string>
  }
}


class CapturedError extends Error{
  constructor(stack: string){
    super();
    this.stack = stack;
  }
}

class SentryTransport extends Transport{
  private options: SentryTransportOptions;

  constructor(options: SentryTransportOptions){
    super(options);
    Sentry.init(options.sentry);
    this.options = options;
  }

  log(info: any, next: CallableFunction){
    this.format?.transform(info);

    const level = info[LEVEL as any];

    const error = info.stack?new CapturedError(info.stack): undefined;
    const message = {...info, ...{level: SENTRY_LEVELS_MAP[level]}};
    if(error){
      delete message['stack'];
    }

    if(this.options.levels.breadcrumbs.includes(level)){
      if(error){
        message.message = `${info.message}\n${error.stack}`
      }
      Sentry.addBreadcrumb(message);
    }else if(this.options.levels.event.includes(level)){
      if(error){
        Sentry.addBreadcrumb(message);
        Sentry.captureException(error);
      }else{
        Sentry.captureEvent(message);
      }
    }
    next();
  }

  end(...args: any[]) {
    Sentry.flush().then(() => {
      super.end(...args);
    });
  }

}


const LOGGER_OPTS = {
  level: 'info',
  transports: new Array<Transport>()
}


if(process.env.NODE_ENV !== 'production'){
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
}else if(process.env.SENTRY_DSN){
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

const logger = createLogger(LOGGER_OPTS);

export { logger };
