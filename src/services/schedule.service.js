import db from '../models/index.js';

class ScheduleService {
  async getAllSchedules() {
    return await db.Schedule.findAll();
  }

  async getScheduleById(id) {
    return await db.Schedule.findByPk(id);
  }

  async createSchedule(scheduleData) {
    return await db.Schedule.create(scheduleData);
  }

  async updateSchedule(id, scheduleData) {
    const schedule = await db.Schedule.findByPk(id);
    if (!schedule) {
      throw new Error('Schedule not found');
    }
    return await schedule.update(scheduleData);
  }

  async deleteSchedule(id) {
    const schedule = await db.Schedule.findByPk(id);
    if (!schedule) {
      throw new Error('Schedule not found');
    }
    await schedule.destroy();
    return true;
  }
}

export default new ScheduleService(); 