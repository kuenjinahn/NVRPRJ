/* eslint-disable unicorn/prevent-abbreviations */
'use-strict';

import * as RecordingsModel from './recordings.model.js';

// 녹화 기록 생성
export const insert = async (req, res) => {
  try {
    const recording = await RecordingsModel.createRecording(req.body);
    res.status(201).send(recording);
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

// 녹화 기록 목록 조회
export const list = async (req, res) => {
  try {
    let recordings;

    if (req.query.startDate && req.query.endDate) {
      // 기간별 녹화 기록 조회
      const startDate = new Date(req.query.startDate);
      const endDate = new Date(req.query.endDate);

      if (req.query.cameraIds) {
        // 여러 카메라 ID 처리
        const cameraIds = Array.isArray(req.query.cameraIds)
          ? req.query.cameraIds
          : [req.query.cameraIds];

        // 각 카메라별로 녹화 기록을 병렬로 조회
        recordings = await Promise.all(
          cameraIds.map(cameraId =>
            RecordingsModel.getRecordingHistoryByDateRange(startDate, endDate, cameraId)
          )
        );
        // 결과 병합 및 중복 제거
        recordings = recordings.flat().filter((record, index, self) =>
          index === self.findIndex(r => r.id === record.id)
        );
      } else if (req.query.cameraId) {
        // 단일 카메라 ID로 조회
        recordings = await RecordingsModel.getRecordingHistoryByDateRange(
          startDate,
          endDate,
          req.query.cameraId
        );
      } else {
        // 날짜 범위만 지정된 경우 전체 카메라 조회
        recordings = await RecordingsModel.getRecordingHistoryByDateRange(
          startDate,
          endDate
        );
      }
    } else if (req.query.cameraId) {
      // 특정 카메라의 전체 녹화 기록 조회
      recordings = await RecordingsModel.getRecordingHistoryByCameraId(req.query.cameraId);
    } else {
      // 전체 녹화 기록 조회
      recordings = await RecordingsModel.getAllRecordingHistory();
    }

    res.status(200).send(recordings);
  } catch (error) {
    console.error('Error in list recordings:', error);
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

// 특정 녹화 기록 조회
export const getById = async (req, res) => {
  try {
    const recording = await RecordingsModel.getRecordingHistoryById(req.params.id);

    if (!recording) {
      return res.status(404).send({
        statusCode: 404,
        message: 'Recording not found',
      });
    }

    res.status(200).send(recording);
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

// 녹화 기록 수정
export const update = async (req, res) => {
  try {
    const recording = await RecordingsModel.updateRecordingHistory(req.params.id, req.body);

    if (!recording) {
      return res.status(404).send({
        statusCode: 404,
        message: 'Recording not found',
      });
    }

    res.status(200).send(recording);
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

// 녹화 기록 삭제
export const removeById = async (req, res) => {
  try {
    const result = await RecordingsModel.removeById(req.params.id);

    if (!result.success) {
      return res.status(404).send({
        statusCode: 404,
        message: 'Recording not found',
      });
    }

    res.status(204).send();
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

// 모든 녹화 기록 삭제
export const removeAll = async (req, res) => {
  try {
    await RecordingsModel.removeAll();
    res.status(204).send();
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};
