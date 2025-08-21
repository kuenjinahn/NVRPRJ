'use-strict';

import os from 'os';
import fs from 'fs-extra';
import path from 'path';

import ConfigService from '../../../services/config/config.service.js';

import Database from '../../database.js';

import CameraController from '../../../controller/camera/camera.controller.js';

export const show = async (user, target) => {
  // config.ini에서 [WEB] 섹션 정보 읽기
  let webConfig = {};
  try {
    const configIniPath = path.join(process.cwd(), 'config.ini');
    if (fs.existsSync(configIniPath)) {
      const configContent = fs.readFileSync(configIniPath, 'utf8');

      // [WEB] 섹션에서 IP, 포트, 버전 추출
      const webMatch = configContent.match(/\[WEB\]\s*\n\s*ip\s*=\s*([^\n]+)/);
      const portMatch = configContent.match(/\[WEB\]\s*\n\s*ip\s*=\s*([^\n]+)\s*\n\s*port\s*=\s*([^\n]+)/);
      const versionMatch = configContent.match(/\[WEB\]\s*\n\s*ip\s*=\s*([^\n]+)\s*\n\s*port\s*=\s*([^\n]+)\s*\n\s*version\s*=\s*([^\n]+)/);

      if (webMatch && webMatch[1]) {
        webConfig.ip = webMatch[1].trim();
        webConfig.port = portMatch && portMatch[2] ? portMatch[2].trim() : '9091';
        webConfig.version = versionMatch && versionMatch[3] ? versionMatch[3].trim() : '1.0.0';
      }
    }
  } catch (error) {
    console.warn('Failed to read config.ini:', error.message);
    webConfig = { ip: 'localhost', port: '9091', version: '1.0.0' };
  }

  let info = {
    timestamp: new Date().toISOString(),
    platform: os.platform(),
    node: process.version,
    version: ConfigService.ui.version,
    firstStart: await Database.interfaceDB.chain.get('firstStart').cloneDeep().value(),
    language: ConfigService.ui.language,
    theme: ConfigService.ui.theme,
    serviceMode: ConfigService.serviceMode,
    env: ConfigService.env,
    web: webConfig, // config.ini의 [WEB] 섹션 정보 추가
  };

  switch (target) {
    case 'config':
      if (user && user.permissionLevel.includes('admin')) {
        info = {
          ...info,
          ...ConfigService.configJson,
        };
      }
      break;
    case 'ui':
      if (user && user.permissionLevel.includes('admin')) {
        info = {
          ...info,
          ...ConfigService.ui,
        };
      }
      break;
    case 'interface':
      if (user && user.permissionLevel.includes('admin')) {
        info = {
          ...info,
          ...ConfigService.interface,
        };
      }
      break;
    case 'all':
      if (user && user.permissionLevel.includes('admin')) {
        info = {
          ...info,
          ...ConfigService.ui,
          ...ConfigService.interface,
          ...ConfigService.configJson,
        };
      }
      break;
    default:
      break;
  }

  return info;
};

export const patchConfig = async (configJson) => {
  Database.controller.emit('config', configJson);
  ConfigService.writeToConfig(false, configJson);
  await Database.writeConfigCamerasToDB();

  if (ConfigService.ui.cameras) {
    for (const camera of ConfigService.ui.cameras) {
      CameraController.reconfigureController(camera.name);
    }
  }
};
