'use strict';

import scheduleService from '../../../controller/camera/services/schedules.service.js';
import LoggerService from '../../../services/logger/logger.service.js';

const logger = new LoggerService('Schedules');

// Basic error handler wrapper
const errorHandler = (fn) => async (req, res, next) => {
  try {
    await fn(req, res, next);
  } catch (error) {
    logger.error('[Schedules] Error:', error.message);
    res.status(500).json({ error: error.message });
  }
};

/**
 * Get all schedules with optional filters
 */
export const getSchedules = errorHandler(async (req, res) => {
  try {
    const filters = {
      camera_name: req.query.camera_name,
      isActive: req.query.isActive !== undefined ? req.query.isActive === 'true' : undefined
    };

    const schedules = await scheduleService.getSchedules(filters);

    // 명시적으로 상태 코드와 응답을 설정
    res.status(200).json(schedules || []);
  } catch (error) {
    logger.error('Error getting schedules:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * Create a new schedule
 */
export const createSchedule = errorHandler(async (req, res) => {
  // Log the incoming request data
  logger.info('Received schedule creation request:', {
    originalData: req.body,
    headers: req.headers,
    method: req.method,
    url: req.originalUrl
  });

  const { cameraName, days, startTime, endTime, recordingType, isActive, source, fk_camera_id, bitrate } = req.body;

  // Transform the data to match backend expectations
  const transformedData = {
    cameraName,
    days_of_week: days,
    start_time: startTime,
    end_time: endTime,
    recording_type: recordingType,
    isActive: isActive !== undefined ? isActive : true,
    recoding_bitrate: bitrate,
    source,
    fk_camera_id
  };

  // Log the transformed data
  logger.info('Transformed schedule data:', transformedData);

  const schedule = await scheduleService.createSchedule(transformedData);

  // Log the created schedule
  logger.info('Schedule created successfully:', schedule);

  res.status(201).json(schedule);
});

/**
 * Update an existing schedule
 */
export const updateSchedule = errorHandler(async (req, res) => {
  // Log the incoming update request
  logger.info('Received schedule update request:', {
    id: req.params.id,
    originalData: req.body,
    headers: req.headers,
    method: req.method,
    url: req.originalUrl
  });

  const { cameraName, days, startTime, endTime, recordingType, isActive, source, fk_camera_id, bitrate } = req.body;
  // Transform the data to match backend expectations
  const transformedData = {
    cameraName,
    days_of_week: days,
    start_time: startTime,
    end_time: endTime,
    recording_type: recordingType,
    isActive: isActive !== undefined ? isActive : true,
    recoding_bitrate: bitrate,
    source,
    fk_camera_id
  };

  // Log the transformed data
  logger.info('Transformed update data:', transformedData);

  const schedule = await scheduleService.updateSchedule(req.params.id, transformedData);

  // Log the updated schedule
  logger.info('Schedule updated successfully:', schedule);

  res.status(200).json(schedule);
});

/**
 * Delete a schedule
 */
export const deleteSchedule = errorHandler(async (req, res) => {
  await scheduleService.deleteSchedule(req.params.id);
  res.status(204).send();
});

/**
 * Toggle schedule active status
 */
export const toggleSchedule = errorHandler(async (req, res) => {
  const schedule = await scheduleService.toggleSchedule(req.params.id);
  res.status(200).json(schedule);
}); 