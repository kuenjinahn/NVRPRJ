'use-strict';

import fs from 'fs-extra';
import moment from 'moment';
import { customAlphabet } from 'nanoid/async';
import path from 'path';
import { Op } from 'sequelize';

import Cleartimer from '../../../common/cleartimer.js';
import Socket from '../../socket.js';
import {
  getAndStoreSnapshot,
  handleFragmentsRequests,
  storeBuffer,
  storeSnapshotFromVideo,
  storeVideo,
  storeVideoBuffer,
} from '../../../common/ffmpeg.js';

import RecordingHistoryModel from '../../../models/RecordingHistory.js';
import sequelize from '../../../models/index.js';

const nanoid = customAlphabet('1234567890abcdef', 10);
const RecordingHistory = RecordingHistoryModel(sequelize);

// 녹화 기록 전체 조회
const getAllRecordingHistory = async () => {
  return await RecordingHistory.findAll({
    order: [['start_time', 'DESC']]
  });
};

// ID로 녹화 기록 조회
const getRecordingHistoryById = async (id) => {
  return await RecordingHistory.findByPk(id);
};

// 카메라 ID로 녹화 기록 조회
const getRecordingHistoryByCameraId = async (cameraId) => {
  return await RecordingHistory.findAll({
    where: { fk_camera_id: cameraId },
    order: [['start_time', 'DESC']]
  });
};

// 녹화 기록 추가
const addRecordingHistory = async (recording) => {
  const recordData = {
    fk_camera_id: recording.cameraId,
    start_time: recording.startTime,
    end_time: recording.endTime,
    duration: recording.duration,
    file_path: recording.filePath,
    file_size: recording.fileSize,
    record_type: recording.recordType,
    status: recording.status,
    resolution: recording.resolution,
    bitrate: recording.bitrate,
    framerate: recording.framerate,
    codec: recording.codec,
    create_date: new Date(),
    update_date: new Date()
  };
  return await RecordingHistory.create(recordData);
};

// 녹화 기록 수정
const updateRecordingHistory = async (id, update) => {
  const recording = await RecordingHistory.findByPk(id);
  if (!recording) return null;

  const updateData = {
    ...update,
    update_date: new Date()
  };

  await recording.update(updateData);
  return recording;
};

// 녹화 기록 삭제
const deleteRecordingHistory = async (id) => {
  const recording = await RecordingHistory.findByPk(id);
  if (!recording) return false;
  await recording.destroy();
  return true;
};

// 기간별 녹화 기록 조회
const getRecordingHistoryByDateRange = async (startDate, endDate, cameraId = null) => {
  // console.log("====> getRecordingHistoryByDateRange startDate :", startDate);
  // console.log("====> getRecordingHistoryByDateRange endDate :", endDate);
  // console.log("====> getRecordingHistoryByDateRange cameraId :", cameraId);

  const whereClause = {
    start_time: {
      [Op.between]: [startDate, endDate]
    }
  };

  if (cameraId) {
    whereClause.fk_camera_id = cameraId;
  }
  console.log("====> whereClause :", whereClause);
  return await RecordingHistory.findAll({
    where: whereClause,
    order: [['start_time', 'DESC']]
  });
};

// 녹화 파일 생성 및 저장
const createRecording = async (data, fileBuffer) => {
  const id = await nanoid();
  const nowMoment = moment().tz('Asia/Seoul');
  const recordingTime = {
    timestamp: nowMoment.unix(),
    formattedForFile: nowMoment.format('YYYY-MM-DDTHH-mm-ss'),
    formattedForDisplay: nowMoment.format('YYYY-MM-DD HH:mm:ss'),
    dateString: nowMoment.format('YYYY-MM-DD')
  };

  const fileName = `${data.camera}_${recordingTime.formattedForFile}.mp4`;
  const filePath = path.join(data.path, fileName);

  // 녹화 기록 생성
  const recordingData = {
    cameraId: data.cameraId,
    startTime: nowMoment.toDate(),
    endTime: null,
    duration: 0,
    filePath: filePath,
    fileSize: 0,
    recordType: data.recordType || 'Video',
    status: 'recording',
    resolution: data.resolution,
    bitrate: data.bitrate,
    framerate: data.framerate,
    codec: data.codec || 'h264'
  };

  const recording = await addRecordingHistory(recordingData);

  // 파일 저장 로직
  if (fileBuffer) {
    await storeVideoBuffer(data.camera, fileBuffer, data.path, fileName, recordingTime);
    await storeSnapshotFromVideo(data.camera, data.path, fileName, data.label);
  } else {
    const isPlaceholder = true;
    const externRecording = false;
    const storeSnapshot = true;

    if (data.imgBuffer) {
      await storeBuffer(data.camera, data.imgBuffer, data.path, fileName, data.label, isPlaceholder, externRecording);
    } else {
      await getAndStoreSnapshot(data.camera, false, data.path, fileName, data.label, isPlaceholder, storeSnapshot);
    }

    if (data.prebuffering) {
      let filebuffer = Buffer.alloc(0);
      let generator = handleFragmentsRequests(data.camera);
      setTimeout(async () => {
        if (generator) {
          generator.throw();
        }
      }, data.timer * 1000);
      for await (const fileBuffer of generator) {
        filebuffer = Buffer.concat([filebuffer, Buffer.concat(fileBuffer)]);
      }
      generator = null;
      await storeVideoBuffer(data.camera, filebuffer, data.path, fileName, recordingTime);
    } else {
      await storeVideo(data.camera, data.path, fileName, data.timer, recordingTime);
    }
  }

  Socket.io.emit('recording', recording);
  Cleartimer.setRecording(id, recordingTime.timestamp);
  return recording;
};

// 녹화 파일 삭제
const removeById = async (id) => {
  try {
    const recording = await RecordingHistory.findByPk(id);
    if (!recording) {
      throw new Error('Recording not found');
    }

    // 파일 삭제
    if (recording.file_path) {
      await fs.remove(recording.file_path);
    }

    // DB에서 삭제
    await recording.destroy();
    return { success: true, id: id };
  } catch (error) {
    throw new Error(`Failed to remove recording: ${error.message}`);
  }
};

// 모든 녹화 파일 삭제
const removeAll = async () => {
  try {
    const recordings = await RecordingHistory.findAll();

    // 모든 파일 삭제
    for (const recording of recordings) {
      if (recording.file_path) {
        await fs.remove(recording.file_path);
      }
    }

    // DB에서 모든 기록 삭제
    await RecordingHistory.destroy({
      where: {},
      truncate: true
    });

    Cleartimer.stopRecordings();
    return { success: true };
  } catch (error) {
    throw new Error(`Failed to remove all recordings: ${error.message}`);
  }
};

export {
  getAllRecordingHistory,
  getRecordingHistoryById,
  getRecordingHistoryByCameraId,
  addRecordingHistory,
  updateRecordingHistory,
  deleteRecordingHistory,
  getRecordingHistoryByDateRange,
  createRecording,
  removeById,
  removeAll
};
