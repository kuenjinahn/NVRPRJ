'use-strict';

import crypto from 'crypto';
import fs from 'fs-extra';
import path from 'path';

import {
  uiDefaults,
  defaultVideoProcess,
  permissionLevels,
  minNodeVersion,
  httpDefaults,
  ftpDefaults,
  mqttDefault,
  smtpDefaults,
  ConfigSetup,
} from './config.defaults.js';

import Camera from '../../models/Camera.js';

export default class ConfigService {
  static #secretPath;

  static name = 'camera.ui';
  static configJson = {};
  static restarted = false;

  //camera.ui env
  static storagePath;
  static configPath;
  static databasePath;
  static databaseUserPath;
  static databaseFilePath;
  static logPath;
  static logFile;
  static recordingsPath;
  static reportsPath;

  static debugEnabled;
  static version;

  //server env
  static minimumNodeVersion;
  static serviceMode;

  static env = {};

  // Recordings configuration
  static recordings = {};

  // Camera configuration
  static camera = {};

  //defaults
  static ui = {
    port: uiDefaults.port,
    logLevel: '2',
    ssl: false,
    mqtt: false,
    topics: new Map(),
    http: false,
    smtp: false,
    options: {
      videoProcessor: defaultVideoProcess,
    },
    cameras: [],
    version: '',
  };

  static interface = {
    permissionLevels: permissionLevels,
    jwt_secret: null,
  };

  constructor(configJson) {
    ConfigService.#secretPath = path.resolve(process.env.CUI_STORAGE_PATH, '.camera.ui.secrets');

    //camera.ui env
    ConfigService.storagePath = process.env.CUI_STORAGE_PATH;
    ConfigService.configPath = process.env.CUI_STORAGE_CONFIG_FILE;
    ConfigService.databasePath = process.env.CUI_STORAGE_DATABASE_PATH;
    ConfigService.databaseUserPath = process.env.CUI_STORAGE_DATABASE_USER_PATH;
    ConfigService.databaseFilePath = process.env.CUI_STORAGE_DATABASE_FILE;
    ConfigService.logPath = process.env.CUI_STORAGE_LOG_PATH;
    ConfigService.logFile = process.env.CUI_STORAGE_LOG_FILE;
    ConfigService.recordingsPath = process.env.CUI_STORAGE_RECORDINGS_PATH;
    ConfigService.reportsPath = process.env.CUI_STORAGE_REPORTS_PATH;

    ConfigService.debugEnabled = process.env.CUI_LOG_MODE === '2';
    ConfigService.version = process.env.CUI_VERSION;

    switch (process.env.CUI_LOG_MODE) {
      case '1':
        ConfigService.logLevel = 'info';
        break;
      case '2':
        ConfigService.logLevel = 'debug';
        break;
      case '3':
        ConfigService.logLevel = 'warn';
        break;
      case '4':
        ConfigService.logLevel = 'error';
        break;
      default:
        ConfigService.logLevel = 'info';
        break;
    }

    //server env
    ConfigService.minimumNodeVersion = minNodeVersion;
    ConfigService.serviceMode = process.env.CUI_SERVICE_MODE === '2';

    ConfigService.env = {
      moduleName: process.env.CUI_MODULE_NAME,
      global: process.env.CUI_MODULE_GLOBAL === '1',
      sudo: process.env.CUI_MODULE_SUDO === '1',
    };

    //defaults
    ConfigService.ui.version = process.env.CUI_MODULE_VERSION;

    const config = new ConfigSetup(configJson);
    ConfigService.configJson = { ...config };

    // Note: parseConfig is now async, but constructor cannot be async
    // We'll call it synchronously for now, but it should be called async in the main startup
    ConfigService.parseConfig(config).catch(error => {
      console.error('Error parsing config:', error);
    });

    fs.ensureFileSync(ConfigService.configPath);
    fs.writeJSONSync(ConfigService.configPath, config, { spaces: 2 });

    return {
      ui: ConfigService.ui,
      json: ConfigService.configJson,
    };
  }

  static async parseConfig(config = {}) {
    ConfigService.#config(config);
    ConfigService.#configInterface();

    // Load cameras from database instead of config
    await ConfigService.#configCamerasFromDB();

    if (config.options) {
      ConfigService.#configOptions(config.options);
    }

    if (config.camera) {
      ConfigService.#configCamera(config.camera);
    }

    if (config.recordings) {
      ConfigService.#configRecordings(config.recordings);
    }

    if (config.ssl) {
      ConfigService.#configSSL(config.ssl);
    }

    if (config.http) {
      ConfigService.#configHTTP(config.http);
    }

    if (config.smtp) {
      ConfigService.#configSMTP(config.smtp);
    }

    if (config.ftp) {
      ConfigService.#configFTP(config.ftp);
    }

    if (config.mqtt) {
      ConfigService.#configMQTT(config.mqtt);
    }
  }

  static async #configCamerasFromDB() {
    try {
      ConfigService.ui.topics.clear();

      // Load cameras from database
      const dbCameras = await Camera.findAll({
        order: [['create_date', 'ASC']]
      });

      ConfigService.ui.cameras = dbCameras.map((dbCamera) => {
        // Parse JSON fields from database
        const camera = {
          name: dbCamera.name,
          motionTimeout: dbCamera.motionTimeout,
          recordOnMovement: dbCamera.recordOnMovement,
          prebuffering: dbCamera.prebuffering,
          prebufferLength: dbCamera.prebufferLength,
          videoConfig: dbCamera.videoConfig ? JSON.parse(dbCamera.videoConfig) : {},
          mqtt: dbCamera.mqtt ? JSON.parse(dbCamera.mqtt) : {},
          smtp: dbCamera.smtp ? JSON.parse(dbCamera.smtp) : {},
          videoanalysis: dbCamera.videoanalysis ? JSON.parse(dbCamera.videoanalysis) : {},
          settings: dbCamera.settings ? JSON.parse(dbCamera.settings) : {}
        };

        // Configure MQTT topics
        if (camera.mqtt.motionTopic) {
          const mqttOptions = {
            motionTopic: camera.mqtt.motionTopic,
            motionMessage: camera.mqtt.motionMessage !== undefined ? camera.mqtt.motionMessage : 'ON',
            motionResetMessage: camera.mqtt.motionResetMessage !== undefined ? camera.mqtt.motionResetMessage : 'OFF',
            camera: camera.name,
            motion: true,
          };

          ConfigService.ui.topics.set(mqttOptions.motionTopic, mqttOptions);
        }

        if (camera.mqtt.motionResetTopic && camera.mqtt.motionResetTopic !== camera.mqtt.motionTopic) {
          const mqttOptions = {
            motionResetTopic: camera.mqtt.motionResetTopic,
            motionResetMessage: camera.mqtt.motionResetMessage !== undefined ? camera.mqtt.motionResetMessage : 'OFF',
            camera: camera.name,
            motion: true,
            reset: true,
          };

          ConfigService.ui.topics.set(mqttOptions.motionResetTopic, mqttOptions);
        }

        if (
          camera.mqtt.doorbellTopic &&
          camera.mqtt.doorbellTopic !== camera.mqtt.motionTopic &&
          camera.mqtt.doorbellTopic !== camera.mqtt.motionResetTopic
        ) {
          const mqttOptions = {
            doorbellTopic: camera.mqtt.doorbellTopic,
            doorbellMessage: camera.mqtt.doorbellMessage !== undefined ? camera.mqtt.doorbellMessage : 'ON',
            camera: camera.name,
            doorbell: true,
          };

          ConfigService.ui.topics.set(mqttOptions.doorbellTopic, mqttOptions);
        }

        return camera;
      });
    } catch (error) {
      console.error('Error loading cameras from database:', error);
      ConfigService.ui.cameras = [];
    }
  }

  static async writeToConfig(target, configJson) {
    let config = ConfigService.configJson;

    if (configJson) {
      if (config[target]) {
        config[target] = configJson;
      } else if (!target) {
        config = configJson;
      } else {
        throw new Error(`Can not save config, "${target}" not found in config!`, 'Config', 'system');
      }
    } else {
      throw new Error('Can not save config, no config defined!', 'Config', 'system');
    }

    config = new ConfigSetup(config);
    ConfigService.configJson = { ...config };

    fs.writeJSONSync(ConfigService.configPath, config, { spaces: 2 });

    await ConfigService.parseConfig(config);
  }

  static #config(config = {}) {
    if (Number.parseInt(config.port)) {
      ConfigService.ui.port = config.port;
    }
  }

  static #configInterface() {
    const generateJWT = () => {
      const secrets = {
        jwt_secret: crypto.randomBytes(32).toString('hex'),
      };

      ConfigService.interface.jwt_secret = secrets.jwt_secret;

      fs.ensureFileSync(ConfigService.#secretPath);
      fs.writeJsonSync(ConfigService.#secretPath, secrets, { spaces: 2 });
    };

    if (fs.pathExistsSync(ConfigService.#secretPath)) {
      try {
        const secrets = fs.readJsonSync(ConfigService.#secretPath);

        if (!secrets.jwt_secret) {
          generateJWT();
        } else {
          ConfigService.interface.jwt_secret = secrets.jwt_secret;
        }
      } catch {
        generateJWT();
      }
    } else {
      generateJWT();
    }
  }

  static #configSSL(ssl = {}) {
    if (!ssl.active) {
      return;
    }

    if (ssl.key && ssl.cert) {
      ConfigService.ui.ssl = {
        key: fs.readFileSync(ssl.key, 'utf8'),
        cert: fs.readFileSync(ssl.cert, 'utf8'),
      };
    }
  }

  static #configOptions(options = {}) {
    if (options.videoProcessor) {
      ConfigService.ui.options.videoProcessor = options.videoProcessor;
    }
  }

  static #configCamera(camera = {}) {
    // Store camera config for access by other services
    ConfigService.camera = camera;

    // Log the camera config for debugging
    console.log('=== Camera Config Debug ===');
    console.log('Raw camera config:', JSON.stringify(camera, null, 2));
    console.log('Camera IP:', camera?.ip);
    console.log('Camera Port:', camera?.port);
    console.log('Camera RTSP:', camera?.rtsp);
    console.log('ConfigService.camera:', ConfigService.camera);
    console.log('==============================');
  }

  static #configRecordings(recordings = {}) {
    // Store recordings config for access by other services
    ConfigService.recordings = recordings;

    // Log the recordings config for debugging
    console.log('=== Recordings Config Debug ===');
    console.log('Raw recordings config:', JSON.stringify(recordings, null, 2));
    console.log('HLS enabled:', recordings?.hls?.enabled);
    console.log('HLS segment duration:', recordings?.hls?.segmentDuration);
    console.log('HLS max segments:', recordings?.hls?.maxSegments);
    console.log('ConfigService.recordings:', ConfigService.recordings);
    console.log('ConfigService.camera:', ConfigService.camera);
    console.log('==============================');
  }

  static #configHTTP(http = {}) {
    if (!http.active) {
      return;
    }

    ConfigService.ui.http = {
      port: http.port || httpDefaults.port,
      localhttp: http.localhttp !== undefined ? http.localhttp : httpDefaults.localhttp,
    };
  }

  static #configSMTP(smtp = {}) {
    if (!smtp.active) {
      return;
    }

    ConfigService.ui.smtp = {
      port: smtp.port || smtpDefaults.port,
      space_replace: smtp.space_replace || smtpDefaults.speace_replace,
    };
  }

  static #configFTP(ftp = {}) {
    if (!ftp.active) {
      return;
    }

    ConfigService.ui.ftp = {
      port: ftp.port || ftpDefaults.port,
      useFile: ftp.useFile !== undefined ? ftp.useFile : ftpDefaults.useFile,
    };
  }

  static #configMQTT(mqtt = {}) {
    if (!mqtt.active || !mqtt.host) {
      return;
    }

    ConfigService.ui.mqtt = {
      tls: mqtt.tls !== undefined ? mqtt.tls : mqttDefault.tls,
      host: mqtt.host,
      port: mqtt.port || mqttDefault.port,
      username: mqtt.username || mqttDefault.username,
      password: mqtt.password || mqttDefault.password,
    };
  }

  // Keep the original method for backward compatibility but mark as deprecated
  static #configCameras(cameras = []) {
    console.warn('configCameras method is deprecated. Use configCamerasFromDB instead.');
    ConfigService.ui.topics.clear();

    ConfigService.ui.cameras = cameras.map((camera) => {
      if (camera.mqtt.motionTopic) {
        const mqttOptions = {
          motionTopic: camera.mqtt.motionTopic,
          motionMessage: camera.mqtt.motionMessage !== undefined ? camera.mqtt.motionMessage : 'ON',
          motionResetMessage: camera.mqtt.motionResetMessage !== undefined ? camera.mqtt.motionResetMessage : 'OFF',
          camera: camera.name,
          motion: true,
        };

        ConfigService.ui.topics.set(mqttOptions.motionTopic, mqttOptions);
      }

      if (camera.mqtt.motionResetTopic && camera.mqtt.motionResetTopic !== camera.mqtt.motionTopic) {
        const mqttOptions = {
          motionResetTopic: camera.mqtt.motionResetTopic,
          motionResetMessage: camera.mqtt.motionResetMessage !== undefined ? camera.mqtt.motionResetMessage : 'OFF',
          camera: camera.name,
          motion: true,
          reset: true,
        };

        ConfigService.ui.topics.set(mqttOptions.motionResetTopic, mqttOptions);
      }

      if (
        camera.mqtt.doorbellTopic &&
        camera.mqtt.doorbellTopic !== camera.mqtt.motionTopic &&
        camera.mqtt.doorbellTopic !== camera.mqtt.motionResetTopic
      ) {
        const mqttOptions = {
          doorbellTopic: camera.mqtt.doorbellTopic,
          doorbellMessage: camera.mqtt.doorbellMessage !== undefined ? camera.mqtt.doorbellMessage : 'ON',
          camera: camera.name,
          doorbell: true,
        };

        ConfigService.ui.topics.set(mqttOptions.doorbellTopic, mqttOptions);
      }

      return camera;
    });
  }

  // Public method to reload cameras from database
  static async reloadCameras() {
    await ConfigService.#configCamerasFromDB();
  }
}
