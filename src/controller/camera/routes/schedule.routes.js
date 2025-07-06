import express from 'express';
import { ScheduleService } from '../services/schedule.service';

const router = express.Router();
const scheduleService = new ScheduleService();

// 스케줄 목록 조회
router.get('/api/schedules', async (req, res) => {
  try {
    console.log('/api/schedules start...');
    const schedules = await scheduleService.getSchedules();
    res.json(schedules);
  } catch (error) {
    console.error('Failed to fetch schedules:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// 스케줄 생성
router.post('/api/schedules', async (req, res) => {
  try {
    const schedule = await scheduleService.createSchedule(req.body);
    res.status(201).json(schedule);
  } catch (error) {
    console.error('Failed to create schedule:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// 스케줄 수정
router.put('/api/api/schedules/:id', async (req, res) => {
  try {
    const schedule = await scheduleService.updateSchedule(
      parseInt(req.params.id),
      req.body
    );
    res.json(schedule);
  } catch (error) {
    console.error('Failed to update schedule:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// 스케줄 삭제
router.delete('/api/schedules/:id', async (req, res) => {
  try {
    await scheduleService.deleteSchedule(parseInt(req.params.id));
    res.status(204).send();
  } catch (error) {
    console.error('Failed to delete schedule:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// 스케줄 상태 토글
router.patch('/api/schedules/:id/toggle', async (req, res) => {
  try {
    const result = await scheduleService.toggleScheduleStatus(
      parseInt(req.params.id),
      req.body.isActive
    );
    res.json(result);
  } catch (error) {
    console.error('Failed to toggle schedule status:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router; 