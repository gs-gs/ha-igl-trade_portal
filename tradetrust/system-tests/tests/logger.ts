import pino from "pino";

const logger = pino({level: 'debug', timestamp: false, name: 'root'});

export {
  logger
}
