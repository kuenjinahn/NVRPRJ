'use-strict';

import Camera from '../../../models/Camera.js';
import sequelize from '../../../models/index.js';
import Ping from '../../../common/ping.js';
import { exec } from 'child_process';
import { promisify } from 'util';
import { getAndStoreSnapshot } from '../../../common/ffmpeg.js';
const execAsync = promisify(exec);

// JSON 파싱 헬퍼 함수
const parseJsonFields = (data) => {
  const jsonFields = ['videoConfig', 'mqtt', 'smtp', 'videoanalysis'];
  jsonFields.forEach(field => {
    if (typeof data[field] === 'string') {
      try {
        data[field] = JSON.parse(data[field]);
      } catch (e) {
        data[field] = null;
      }
    }
  });
  return data;
};

// 모든 카메라 조회 (기존 list 함수와의 호환성을 위해)
const list = async () => {
  const cameras = await Camera.findAll({
    order: [['name', 'ASC']]
  });
  return cameras.map(camera => parseJsonFields(camera.toJSON()));
};

// 모든 카메라 조회
const getAllCameras = async () => {
  const cameras = await Camera.findAll({
    order: [['name', 'ASC']]
  });
  return cameras.map(camera => parseJsonFields(camera.toJSON()));
};

// ID로 카메라 조회
const getCameraById = async (id) => {
  const camera = await Camera.findByPk(id);
  return camera ? parseJsonFields(camera.toJSON()) : null;
};

// 이름으로 카메라 조회
const findByName = async (name) => {
  const camera = await Camera.findOne({
    where: { name: name }
  });
  return camera ? parseJsonFields(camera.toJSON()) : null;
};

// 이름으로 카메라 설정 조회
const getSettingsByName = async (name) => {
  const camera = await Camera.findOne({
    where: { name: name },
    attributes: ['settings']
  });

  if (!camera) return null;

  const data = camera.toJSON();
  if (data.settings && typeof data.settings === 'string') {
    try {
      data.settings = JSON.parse(data.settings);
    } catch (e) {
      console.error('Error parsing settings JSON:', e);
      data.settings = null;
    }
  }

  return data;
};

// 카메라 추가
const addCamera = async (cameraData) => {
  const data = {
    name: cameraData.name,
    motionTimeout: cameraData.motionTimeout || 15,
    recordOnMovement: cameraData.recordOnMovement || false,
    prebuffering: cameraData.prebuffering || false,
    videoConfig: typeof cameraData.videoConfig === 'object' ? JSON.stringify(cameraData.videoConfig) : cameraData.videoConfig,
    mqtt: typeof cameraData.mqtt === 'object' ? JSON.stringify(cameraData.mqtt) : (cameraData.mqtt || null),
    smtp: typeof cameraData.smtp === 'object' ? JSON.stringify(cameraData.smtp) : (cameraData.smtp || null),
    videoanalysis: typeof cameraData.videoanalysis === 'object' ? JSON.stringify(cameraData.videoanalysis) : (cameraData.videoanalysis || null),
    prebufferLength: cameraData.prebufferLength || 4,
    settings: typeof cameraData.settings === 'object' ? JSON.stringify(cameraData.settings) : cameraData.settings,
    create_date: new Date(),
    update_dt: new Date()
  };
  const camera = await Camera.create(data);
  return parseJsonFields(camera.toJSON());
};

// createCamera is an alias for addCamera for backward compatibility
const createCamera = addCamera;

// 카메라 수정
const updateCamera = async (id, updateData) => {
  const camera = await Camera.findByPk(id);
  if (!camera) return null;

  const data = {
    ...updateData,
    update_dt: new Date()
  };

  // JSON 필드 처리
  const jsonFields = ['videoConfig', 'mqtt', 'smtp', 'videoanalysis', 'settings'];
  jsonFields.forEach(field => {
    if (data[field] && typeof data[field] === 'object') {
      data[field] = JSON.stringify(data[field]);
    }
  });

  await camera.update(data);
  return parseJsonFields(camera.toJSON());
};

// 카메라 삭제
const deleteCamera = async (id) => {
  const camera = await Camera.findByPk(id);
  if (!camera) return false;
  await camera.destroy();
  return true;
};

// 카메라 설정 업데이트
const updateCameraSettings = async (id, settings) => {
  const camera = await Camera.findByPk(id);
  if (!camera) return null;

  const updateData = {
    videoConfig: typeof settings.videoConfig === 'object' ? JSON.stringify(settings.videoConfig) : (settings.videoConfig || camera.videoConfig),
    mqtt: typeof settings.mqtt === 'object' ? JSON.stringify(settings.mqtt) : (settings.mqtt || camera.mqtt),
    smtp: typeof settings.smtp === 'object' ? JSON.stringify(settings.smtp) : (settings.smtp || camera.smtp),
    videoanalysis: typeof settings.videoanalysis === 'object' ? JSON.stringify(settings.videoanalysis) : (settings.videoanalysis || camera.videoanalysis),
    update_dt: new Date()
  };

  await camera.update(updateData);
  return parseJsonFields(camera.toJSON());
};

// 카메라 동작 설정 업데이트
const updateCameraMotionSettings = async (id, settings) => {
  const camera = await Camera.findByPk(id);
  if (!camera) return null;

  const updateData = {
    motionTimeout: settings.motionTimeout || camera.motionTimeout,
    recordOnMovement: settings.recordOnMovement || camera.recordOnMovement,
    prebuffering: settings.prebuffering || camera.prebuffering,
    prebufferLength: settings.prebufferLength || camera.prebufferLength,
    update_dt: new Date()
  };

  await camera.update(updateData);
  return parseJsonFields(camera.toJSON());
};

// 이름으로 카메라 삭제
const removeByName = async (name) => {
  const camera = await Camera.findOne({
    where: { name: name }
  });
  if (!camera) return false;
  await camera.destroy();
  return true;
};

// 모든 카메라 삭제
const removeAll = async () => {
  await Camera.destroy({
    where: {},
    truncate: true
  });
  return true;
};

const pingCamera = async (camera, timeout) => {
  timeout = (Number.parseInt(timeout) || 0) < 1 ? 1 : Number.parseInt(timeout);
  return await Ping.status(camera, timeout);
};


const requestSnapshot = async (camera, fromSubSource) => {
  camera = parseJsonFields(camera);
  return await getAndStoreSnapshot(camera, fromSubSource);
};

export {
  list,
  getAllCameras,
  getCameraById,
  findByName,
  getSettingsByName,
  addCamera,
  createCamera,
  updateCamera,
  deleteCamera,
  updateCameraSettings,
  updateCameraMotionSettings,
  removeByName,
  removeAll,
  pingCamera,
  requestSnapshot
};
