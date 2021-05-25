import { api } from 'src/apis/status-tracking';
import { getStatusTrackingAPIConfig } from 'src/config';
import { logger } from 'src/logger';

const config = getStatusTrackingAPIConfig();

api().listen(config.PORT, config.HOST, ()=>logger.info('Status tracking api started on %s:%s', config.HOST, config.PORT));
