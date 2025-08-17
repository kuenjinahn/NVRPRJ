'use-strict';

import * as AlertModel from './alerts.model.js';
import AlertSetting from '../../../models/AlertSetting.js';
import db from '../../../models/index.js'; // Sequelize instance
import AlertHistory from '../../../models/AlertHistory.js';
import { Op, fn, col, literal } from 'sequelize';

export const insert = async (req, res) => {
  try {
    await AlertModel.createAlert(req.body);

    res.status(201).send({
      statusCode: 201,
      message: 'Alert created successfully',
    });
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const list = async (req, res, next) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const pageSize = parseInt(req.query.pageSize) || 10;
    const offset = (page - 1) * pageSize;
    const limit = pageSize;

    // 필터 처리
    const where = {};
    if (req.query.status) where.alert_status = req.query.status;
    if (req.query.level) where.alert_level = req.query.level;
    if (req.query.startDate && req.query.endDate) {
      where.alert_accur_time = { [Op.between]: [req.query.startDate, req.query.endDate] };
    }
    if (req.query.search) {
      where.alert_description = { [Op.like]: `%${req.query.search}%` };
    }

    const { count, rows } = await AlertModel.list({ where, offset, limit });
    res.locals.items = rows;
    res.locals.totalItems = count;
    return next();
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const getById = async (req, res) => {
  try {
    const alert = await AlertModel.findById(req.params.id);

    if (!alert) {
      return res.status(404).send({
        statusCode: 404,
        message: 'Alert not found',
      });
    }

    res.status(200).send(alert);
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const patchById = async (req, res) => {
  try {
    const alert = await AlertModel.findById(req.params.id);

    if (!alert) {
      return res.status(404).send({
        statusCode: 404,
        message: 'Alert not found',
      });
    }

    await AlertModel.updateAlert(req.params.id, req.body);

    res.status(204).send({});
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const removeById = async (req, res) => {
  try {
    const alert = await AlertModel.findById(req.params.id);

    if (!alert) {
      return res.status(404).send({
        statusCode: 404,
        message: 'Alert not found',
      });
    }

    await AlertModel.removeById(req.params.id);

    res.status(204).send({});
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const getByCamera = async (req, res) => {
  try {
    const alerts = await AlertModel.getAlertsByCamera(req.params.cameraId);

    res.status(200).send(alerts);
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const getByStatus = async (req, res) => {
  try {
    const alerts = await AlertModel.getAlertsByStatus(req.params.status);

    res.status(200).send(alerts);
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const getAlertSettings = async (req, res) => {
  try {
    const fk_user_id = 1; // 고정값으로 설정
    const setting = await AlertSetting.findOne({ where: { fk_user_id } });
    res.json({ result: setting });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const saveAlertSettings = async (req, res) => {
  try {
    const { alert_setting_json } = req.body.settings;
    const fk_user_id = 1; // 고정값으로 설정
    console.log('----------> saveAlertSettings', req.body);
    let setting = await AlertSetting.findOne({ where: { fk_user_id } });
    if (setting) {
      // update
      await setting.update({
        alert_setting_json,
        update_date: new Date()
      });
    } else {
      // insert
      setting = await AlertSetting.create({
        alert_setting_json,
        fk_user_id,
        create_date: new Date(),
        update_date: new Date()
      });
    }
    res.json({ result: setting });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const getWeeklyStats = async (req, res) => {
  try {
    const [results] = await db.sequelize.query(`
      SELECT
        DATE(alert_accur_time) as date,
        SUM(alert_level = 1) as '1',
        SUM(alert_level = 2) as '2',
        SUM(alert_level = 3) as '3',
        SUM(alert_level = 4) as '4',
        SUM(alert_level = 5) as '5'
      FROM tb_alert_history
      WHERE alert_accur_time >= CURDATE() - INTERVAL 6 DAY
      GROUP BY DATE(alert_accur_time)
      ORDER BY date ASC
    `);
    res.json({ result: results });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

// 최근 7일간의 알림 건수 집계
export const recentAlertCount = async (req, res) => {
  console.log('----------> recentAlertCount');
  try {
    const today = new Date();
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(today.getDate() - 6);

    const results = await AlertHistory.findAll({
      attributes: [
        [fn('DATE', col('alert_accur_time')), 'date'],
        [fn('COUNT', col('id')), 'count']
      ],
      where: {
        alert_accur_time: {
          [Op.gte]: sevenDaysAgo
        }
      },
      group: [fn('DATE', col('alert_accur_time'))],
      order: [[literal('date'), 'ASC']]
    });
    res.json({ result: results });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

export { AlertSetting }; 