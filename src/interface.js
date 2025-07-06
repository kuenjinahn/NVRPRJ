import compareVersions from 'compare-versions';
import { EventEmitter } from 'events';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import dotenv from 'dotenv';

import ConfigService from './services/config/config.service.js';
import LoggerService from './services/logger/logger.service.js';
import Database from './api/database.js';
import db from './models/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables from root directory
dotenv.config({ path: join(__dirname, '../../.env') });

const { log } = LoggerService;

export default class Interface extends EventEmitter {
  constructor() {
    super();
    this.config = ConfigService.interface;
    this.database = new Database();
    this.server = undefined;
  }

  async start() {
    try {
      console.log('[interface.js] start() 진입');
      logOrConsole('Starting camera.ui...');

      // Initialize MariaDB connection
      console.log('[interface.js] DB authenticate start');
      await db.sequelize.authenticate();
      console.log('[interface.js] DB authenticate done');

      // Initialize interface
      console.log('[interface.js] initializeInterface() 호출');
      await this.initializeInterface();
      console.log('[interface.js] initializeInterface() 완료');

      // Initialize database
      console.log('[interface.js] database.start() 호출');
      await this.database.start();
      // console.log('[interface.js] database.start() 완료');

      logOrConsole('camera.ui started successfully');
    } catch (error) {
      logOrConsole('Error in interface.js start(): ' + error.message, true);
      process.exit(1);
    }
  }

  async initializeInterface() {
    console.log('[interface.js] initializeInterface() 진입');
    const Server = (await import('./api/index.js')).default;
    this.server = new Server(this);

    // 포트 정보 안전하게 추출
    const port =
      (this.config && this.config.ui && this.config.ui.port) ||
      (this.config && this.config.port) ||
      (typeof ConfigService !== 'undefined' && ConfigService.ui && ConfigService.ui.port) ||
      3000;

    if (this.server && typeof this.server.listen === 'function') {
      this.server.listen(port, () => {
        console.log(`[interface.js] Server listening on port ${port}`);
      });
    } else {
      console.log('[interface.js] 서버 인스턴스가 없거나 listen 메서드가 없습니다.');
    }
    return true;
  }
}

function logOrConsole(msg, isError = false) {
  if (typeof log !== 'undefined' && log && typeof log.info === 'function' && !isError) {
    log.info(msg, 'System', 'system');
  } else if (typeof log !== 'undefined' && log && typeof log.error === 'function' && isError) {
    log.error(msg, 'System', 'system');
  } else {
    if (isError) {
      console.error(msg);
    } else {
      console.log(msg);
    }
  }
} 