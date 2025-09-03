/* eslint-disable unicorn/prefer-number-properties */
'use-strict';

import path from 'path';
// import ffmpeg from 'ffmpeg-for-homebridge';

export const uiDefaults = {
  port: 9091,
};

export const httpDefaults = {
  port: 7272,
  localhttp: false,
};

export const smtpDefaults = {
  port: 2727,
  speace_replace: '+',
};

export const ftpDefaults = {
  port: 5050,
  useFile: false,
};

export const mqttDefault = {
  tls: false,
  port: 1883,
};

export const permissionLevels = [
  'admin',
  //API
  'backup:download',
  'backup:restore',
  'cameras:access',
  'cameras:edit',
  'config:access',
  'config:edit',
  'notifications:access',
  'notifications:edit',
  'recordings:access',
  'recordings:edit',
  'settings:access',
  'settings:edit',
  'users:access',
  'users:edit',
  //CLIENT
  'camview:access',
  'dashboard:access',
  'settings:cameras:access',
  'settings:cameras:edit',
  'settings:camview:access',
  'settings:camview:edit',
  'settings:config:access',
  'settings:config:edit',
  'settings:dashboard:access',
  'settings:dashboard:edit',
  'settings:general:access',
  'settings:general:edit',
  'settings:notifications:access',
  'settings:notifications:edit',
  'settings:profile:access',
  'settings:profile:edit',
  'settings:recordings:access',
  'settings:recordings:edit',
];

// FFmpeg 경로 설정
const ffmpegPath = process.platform === 'win32' ? 'C:/ffmpeg/bin/ffmpeg.exe' : 'ffmpeg';
export const defaultVideoProcess = ffmpegPath;

export const minNodeVersion = '16.12.0';

export class ConfigSetup {
  constructor(config = {}) {
    console.log('=== ConfigSetup Constructor Debug ===');
    console.log('Input config:', config);
    console.log('config?.camera:', config?.camera);
    console.log('config?.recordings:', config?.recordings);

    // setupCamera 호출 결과를 별도로 저장하고 로깅
    const cameraConfig = ConfigSetup.setupCamera(config?.camera);
    console.log('=== setupCamera Result ===');
    console.log('cameraConfig:', cameraConfig);
    console.log('cameraConfig.ip:', cameraConfig?.ip);
    console.log('========================');

    // ConfigService.camera에 직접 설정 (config.json에는 포함하지 않음)
    if (typeof ConfigService !== 'undefined') {
      ConfigService.camera = cameraConfig;
      console.log('ConfigService.camera set to:', ConfigService.camera);
    }

    const result = {
      ...ConfigSetup.setupUi(config),
      options: ConfigSetup.setupOptions(config?.options),
      recordings: ConfigSetup.setupRecordings(config?.recordings),
      ssl: ConfigSetup.setupSsl(config?.ssl),
      http: ConfigSetup.setupHttp(config?.http),
      smtp: ConfigSetup.setupSmtp(config?.smtp),
      ftp: ConfigSetup.setupFtp(config?.ftp),
      mqtt: ConfigSetup.setupMqtt(config?.mqtt),
      cameras: ConfigSetup.setupCameras(config?.cameras),
    };

    console.log('ConfigSetup result:', result);
    console.log('Final camera config:', result.camera);
    console.log('=====================================');

    return result;
  }

  static setupUi(config = {}) {
    return {
      logLevel: config?.logLevel || 'info',
      port: config?.port || uiDefaults.port,
      atHomeSwitch: config?.atHomeSwitch || false,
    };
  }

  static setupOptions(options = {}) {
    return {
      videoProcessor: options?.videoProcessor || defaultVideoProcess,
    };
  }

  static setupSsl(ssl = {}) {
    return {
      active: Boolean(ssl?.active && ssl?.key && ssl?.cert),
      key: ssl?.key,
      cert: ssl?.cert,
    };
  }

  static setupMqtt(mqtt = {}) {
    return {
      active: Boolean(mqtt?.active && mqtt?.host),
      tls: mqtt?.tls || mqttDefault.tls,
      host: mqtt?.host,
      port: !isNaN(mqtt?.port) ? mqtt.port : mqttDefault.port,
      username: mqtt?.username,
      password: mqtt?.password,
    };
  }

  static setupHttp(http = {}) {
    return {
      active: http?.active || false,
      port: !isNaN(http?.port) ? http.port : httpDefaults.port,
      localhttp: http?.localhttp || httpDefaults.localhttp,
    };
  }

  static setupSmtp(smtp = {}) {
    return {
      active: smtp?.active || false,
      port: !isNaN(smtp?.port) ? smtp.port : smtpDefaults.port,
      space_replace: smtp?.space_replace || smtpDefaults.speace_replace,
    };
  }

  static setupFtp(ftp = {}) {
    return {
      active: ftp?.active || false,
      useFile: ftp?.useFile || ftpDefaults.useFile,
      port: !isNaN(ftp?.port) ? ftp.port : ftpDefaults.port,
    };
  }

  static setupCameras(cameras = []) {
    return (
      cameras
        // include only cameras with given name, videoConfig and source
        .filter((camera) => camera.name && camera.videoConfig?.source)
        .map((camera) => {
          const sourceArguments = camera.videoConfig.source.split(/\s+/);

          if (!sourceArguments.includes('-i')) {
            camera.videoConfig.source = false;
          }

          if (camera.videoConfig.subSource) {
            const stillArguments = camera.videoConfig.subSource.split(/\s+/);

            if (!stillArguments.includes('-i')) {
              camera.videoConfig.subSource = camera.videoConfig.source;
            }
          } else {
            camera.videoConfig.subSource = camera.videoConfig.source;
          }

          if (camera.videoConfig.stillImageSource) {
            const stillArguments = camera.videoConfig.stillImageSource.split(/\s+/);

            if (!stillArguments.includes('-i')) {
              camera.videoConfig.stillImageSource = camera.videoConfig.source;
            }
          } else {
            camera.videoConfig.stillImageSource = camera.videoConfig.source;
          }

          // homebridge
          camera.recordOnMovement = camera.recordOnMovement !== undefined ? camera.recordOnMovement : !camera.hsv;

          camera.motionTimeout =
            camera.motionTimeout === undefined || !(camera.motionTimeout >= 0) ? 15 : camera.motionTimeout;

          camera.motionDelay = camera.motionDelay && camera.motionDelay <= 10 ? camera.motionDelay : undefined;

          // validate prebufferLength
          camera.prebufferLength =
            camera.prebufferLength >= 4 && camera.prebufferLength <= 8 ? camera.prebufferLength : 4;

          // setup video analysis
          camera.videoanalysis = {
            active: camera.videoanalysis?.active || false,
          };

          // setup mqtt
          camera.smtp = camera.smtp || {
            email: camera.name,
          };

          // setup mqtt
          camera.mqtt = camera.mqtt || {};

          return camera;
        })
        // exclude cameras with invalid videoConfig, source
        .filter((camera) => camera.videoConfig?.source)
    );
  }

  static setupCamera(camera = {}) {
    console.log('=== setupCamera Debug ===');
    console.log('Input camera config:', camera);
    console.log('camera?.ip:', camera?.ip);
    console.log('camera?.port:', camera?.port);
    console.log('camera?.rtsp:', camera?.rtsp);

    // config.ini 파일에서 직접 [CAMERA] 섹션 읽기
    let cameraConfig = { ...camera };

    try {
      const fs = require('fs-extra');
      // config.ini 파일을 직접 지정 (CUI_STORAGE_CONFIG_FILE은 config.json용)
      const configPath = './config.ini';
      console.log('[setupCamera] Config file path:', configPath);

      if (fs.existsSync(configPath)) {
        const configContent = fs.readFileSync(configPath, 'utf8');
        console.log('[setupCamera] Config file content (first 500 chars):', configContent.substring(0, 500));

        // INI 파일 파싱
        const lines = configContent.split('\n');
        let currentSection = '';
        let cameraSection = {};

        for (const line of lines) {
          const trimmedLine = line.trim();

          // 섹션 헤더 확인
          if (trimmedLine.startsWith('[') && trimmedLine.endsWith(']')) {
            currentSection = trimmedLine.slice(1, -1);
            console.log('[setupCamera] Found section:', currentSection);
          }
          // CAMERA 섹션의 키-값 쌍 파싱
          else if (currentSection === 'CAMERA' && trimmedLine.includes('=')) {
            const [key, value] = trimmedLine.split('=').map(s => s.trim());
            cameraSection[key] = value;
            console.log('[setupCamera] Found camera config:', key, '=', value);
          }
        }

        console.log('[setupCamera] Parsed camera section:', cameraSection);

        // config.ini에서 읽은 값으로 cameraConfig 업데이트
        if (cameraSection.ip) {
          cameraConfig.ip = cameraSection.ip;
        }
        if (cameraSection.port) {
          cameraConfig.port = parseInt(cameraSection.port);
        }
        if (cameraSection.rtsp) {
          cameraConfig.rtsp = cameraSection.rtsp;
        }

        console.log('[setupCamera] Updated camera config from config.ini:', cameraConfig);
      } else {
        console.warn('[setupCamera] Config file not found at:', configPath);
      }
    } catch (error) {
      console.error('[setupCamera] Error reading config.ini:', error);
    }

    const result = {
      ip: cameraConfig.ip || '175.201.204.166',
      port: parseInt(cameraConfig.port) || 32000,
      rtsp: cameraConfig.rtsp || `rtsp://root:bw84218899!@${cameraConfig.ip || '175.201.204.166'}:554/cam0_0`
    };

    console.log('Final camera config result:', result);
    console.log('=============================');

    return result;
  }

  static setupRecordings(recordings = {}) {
    // config.ini 파일에서 직접 [recordings] 섹션 읽기
    let recordingsConfig = { ...recordings };

    try {
      const fs = require('fs-extra');
      const configPath = './config.ini';
      console.log('[setupRecordings] Config file path:', configPath);

      if (fs.existsSync(configPath)) {
        const configContent = fs.readFileSync(configPath, 'utf8');

        // INI 파일 파싱
        const lines = configContent.split('\n');
        let currentSection = '';
        let recordingsSection = {};

        for (const line of lines) {
          const trimmedLine = line.trim();

          // 섹션 헤더 확인
          if (trimmedLine.startsWith('[') && trimmedLine.endsWith(']')) {
            currentSection = trimmedLine.slice(1, -1);
          }
          // RECORDINGS 섹션의 키-값 쌍 파싱
          else if (currentSection === 'recordings' && trimmedLine.includes('=')) {
            const [key, value] = trimmedLine.split('=').map(s => s.trim());
            recordingsSection[key] = value;
            console.log('[setupRecordings] Found recordings config:', key, '=', value);
          }
        }

        console.log('[setupRecordings] Parsed recordings section:', recordingsSection);

        // config.ini에서 읽은 값으로 recordingsConfig 업데이트
        if (recordingsSection.hls_enabled !== undefined) {
          recordingsConfig.hls_enabled = recordingsSection.hls_enabled;
        }
        if (recordingsSection.hls_segmentDuration !== undefined) {
          recordingsConfig.hls_segmentDuration = recordingsSection.hls_segmentDuration;
        }
        if (recordingsSection.hls_maxSegments !== undefined) {
          recordingsConfig.hls_maxSegments = recordingsSection.hls_maxSegments;
        }
        if (recordingsSection.hls_deleteSegments !== undefined) {
          recordingsConfig.hls_deleteSegments = recordingsSection.hls_deleteSegments;
        }
        if (recordingsSection.hls_quality !== undefined) {
          recordingsConfig.hls_quality = recordingsSection.hls_quality;
        }
        if (recordingsSection.hls_bitrate !== undefined) {
          recordingsConfig.hls_bitrate = recordingsSection.hls_bitrate;
        }
        if (recordingsSection.hls_segmentSize !== undefined) {
          recordingsConfig.hls_segmentSize = recordingsSection.hls_segmentSize;
        }
        if (recordingsSection.hls_autoCleanup !== undefined) {
          recordingsConfig.hls_autoCleanup = recordingsSection.hls_autoCleanup;
        }
        if (recordingsSection.hls_cleanupInterval !== undefined) {
          recordingsConfig.hls_cleanupInterval = recordingsSection.hls_cleanupInterval;
        }
        if (recordingsSection.hls_segmentType !== undefined) {
          recordingsConfig.hls_segmentType = recordingsSection.hls_segmentType;
        }
        if (recordingsSection.hls_flags !== undefined) {
          recordingsConfig.hls_flags = recordingsSection.hls_flags;
        }
        console.log('[setupRecordings] Updated recordings config from config.ini:', recordingsConfig);
      } else {
        console.warn('[setupRecordings] Config file not found at:', configPath);
      }
    } catch (error) {
      console.error('[setupRecordings] Error reading config.ini:', error);
    }

    return {
      path: recordingsConfig?.path || './outputs/nvr/recordings',
      retention: recordingsConfig?.retention || 3600,
      maxFileSize: recordingsConfig?.maxFileSize || '10GB',
      hls: {
        enabled: recordingsConfig?.hls_enabled === 'true' || recordingsConfig?.hls?.enabled || false,
        segmentDuration: parseInt(recordingsConfig?.hls_segmentDuration) || recordingsConfig?.hls?.segmentDuration || 3600, // 기본값 1시간
        maxSegments: parseInt(recordingsConfig?.hls_maxSegments) || recordingsConfig?.hls?.maxSegments || 24, // 24시간 = 24개
        deleteSegments: recordingsConfig?.hls_deleteSegments === 'true' || recordingsConfig?.hls?.deleteSegments || true,
        quality: recordingsConfig?.hls_quality || recordingsConfig?.hls?.quality || 'medium',
        bitrate: recordingsConfig?.hls_bitrate || recordingsConfig?.hls?.bitrate || '1024k',
        segmentSize: recordingsConfig?.hls_segmentSize || recordingsConfig?.hls?.segmentSize || '4MB', // 기본값 4MB
        autoCleanup: recordingsConfig?.hls_autoCleanup === 'true' || recordingsConfig?.hls?.autoCleanup || true,
        cleanupInterval: parseInt(recordingsConfig?.hls_cleanupInterval) || recordingsConfig?.hls?.cleanupInterval || 3600, // 기본값 1시간
        segmentType: recordingsConfig?.hls_segmentType || recordingsConfig?.hls?.segmentType || 'mpegts', // 명시적으로 mpegts 타입 지정
        flags: recordingsConfig?.hls_flags || recordingsConfig?.hls?.flags || 'delete_segments+append_list', // 세그먼트 자동 삭제 활성화
      },
    };
  }
}
