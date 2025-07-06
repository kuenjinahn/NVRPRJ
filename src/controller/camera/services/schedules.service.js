'use strict';

import { validateSchedule } from '../../../api/components/schedules/schedules.validation.js';
import LoggerService from '../../../services/logger/logger.service.js';
import ScheduleModel from '../../../models/schedule.js';
import sequelize from '../../../models/index.js';
const Schedule = ScheduleModel(sequelize);

const logger = new LoggerService('Schedules');

class SchedulesService {
  /**
   * Get schedules with optional filters
   * @param {Object} filters - Optional filters for camera_id and isActive
   * @returns {Promise<Array>} Array of schedule objects
   */
  async getSchedules(filters = {}) {
    try {
      const schedules = await Schedule.findAll({
        where: {
          isActive: 1
        },
        order: [['id', 'DESC']]
      });
      return schedules;
    } catch (error) {
      logger.error('Error getting schedules:', error);
      throw error;
    }
  }

  /**
   * Get a schedule by ID
   * @param {number} id - Schedule ID
   * @returns {Promise<Object>} Schedule object
   */
  async getScheduleById(id) {
    try {
      const schedule = await Schedule.findByPk(id);
      return schedule;
    } catch (error) {
      logger.error('Error getting schedule by ID:', error);
      throw error;
    }
  }

  /**
   * Create a new schedule
   * @param {Object} scheduleData - Data for new schedule
   * @returns {Promise<Object>} Created schedule
   */
  async createSchedule(scheduleData) {
    try {
      logger.info('Creating schedule with data:', scheduleData);

      const validationError = validateSchedule(scheduleData);
      if (validationError) {
        logger.warn('Schedule validation failed:', {
          error: validationError,
          data: scheduleData
        });
        throw new Error(validationError);
      }

      const schedule = await Schedule.create({
        ...scheduleData,
        create_date: new Date(),
        update_date: new Date()
      });

      logger.info('Schedule created successfully:', {
        id: schedule.id,
        cameraName: schedule.cameraName,
        source: schedule.source
      });

      return schedule;
    } catch (error) {
      logger.error('Failed to create schedule:', error);
      throw error;
    }
  }

  /**
   * Update an existing schedule
   * @param {number} id - Schedule ID
   * @param {Object} scheduleData - Updated schedule data
   * @returns {Promise<Object>} Updated schedule
   */
  async updateSchedule(id, scheduleData) {
    try {
      logger.info('Updating schedule with data:', { id, scheduleData });

      const schedule = await Schedule.findByPk(id);
      if (!schedule) {
        throw new Error('Schedule not found');
      }

      await schedule.update({
        ...scheduleData,
        update_date: new Date()
      });

      logger.info('Schedule updated successfully:', { id, updatedSchedule: schedule });
      return schedule;
    } catch (error) {
      logger.error('Error updating schedule:', error);
      throw error;
    }
  }

  /**
   * Delete a schedule
   * @param {number} id - Schedule ID
   * @returns {Promise<boolean>} True if deletion successful
   */
  async deleteSchedule(id) {
    try {
      logger.info('Attempting to delete schedule:', { id });

      const schedule = await Schedule.findByPk(id);
      if (!schedule) {
        logger.warn('Schedule not found for deletion:', { id });
        throw new Error('Schedule not found');
      }

      await schedule.destroy();

      logger.info('Schedule deleted successfully:', {
        id: id,
        deletedSchedule: schedule
      });

      return true;
    } catch (error) {
      logger.error('Error deleting schedule:', error);
      throw error;
    }
  }

  /**
   * Toggle schedule active status
   * @param {number} id - Schedule ID
   * @returns {Promise<Object>} Updated schedule
   */
  async toggleSchedule(id) {
    try {
      logger.info('Toggling schedule status for id:', id);

      const schedule = await Schedule.findByPk(id);
      if (!schedule) {
        throw new Error('Schedule not found');
      }

      const updatedSchedule = {
        ...schedule,
        isActive: !schedule.isActive,
        update_date: new Date()
      };

      await schedule.update(updatedSchedule);

      logger.info('Schedule status toggled successfully:', {
        id,
        isActive: updatedSchedule.isActive
      });
      return updatedSchedule;
    } catch (error) {
      logger.error('Error toggling schedule status:', error);
      throw error;
    }
  }

  /**
   * Get active schedules
   * @returns {Promise<Array>} Array of active schedule objects
   */
  async getActiveSchedules() {
    try {
      const schedules = await Schedule.findAll({
        where: {
          isActive: 1
        },
        order: [['id', 'DESC']]
      });
      return schedules;
    } catch (error) {
      logger.error('Error getting active schedules:', error);
      throw error;
    }
  }

  /**
   * Get schedules by camera ID
   * @param {number} cameraId - Camera ID
   * @returns {Promise<Array>} Array of schedule objects
   */
  async getSchedulesByCameraId(cameraId) {
    try {
      const schedules = await Schedule.findAll({
        where: {
          fk_camera_id: cameraId
        },
        order: [['id', 'DESC']]
      });
      return schedules;
    } catch (error) {
      logger.error('Error getting schedules by camera ID:', error);
      throw error;
    }
  }
}

const schedulesService = new SchedulesService();
export default schedulesService; 