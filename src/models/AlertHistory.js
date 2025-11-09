import { DataTypes } from 'sequelize';
import sequelize from '../database/config.js';

const AlertHistory = sequelize.define('AlertHistory', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  fk_camera_id: {
    type: DataTypes.INTEGER,
    allowNull: false,
    defaultValue: 0
  },
  alert_accur_time: {
    type: DataTypes.DATE,
    allowNull: true
  },
  alert_type: {
    type: DataTypes.STRING(5),
    allowNull: true
  },
  alert_level: {
    type: DataTypes.STRING(5),
    allowNull: true
  },
  alert_status: {
    type: DataTypes.STRING(5),
    allowNull: true
  },
  fk_detect_zone_id: {
    type: DataTypes.INTEGER,
    allowNull: true,
    defaultValue: 0
  },
  fk_process_user_id: {
    type: DataTypes.INTEGER,
    allowNull: true,
    defaultValue: 0
  },
  fk_video_receive_data_id: {
    type: DataTypes.INTEGER,
    allowNull: true,
    defaultValue: 0
  },
  alert_process_time: {
    type: DataTypes.DATE,
    allowNull: true
  },
  alert_description: {
    type: DataTypes.STRING(1024),
    allowNull: true
  },
  snapshotImages: {
    type: DataTypes.TEXT('medium'),
    allowNull: true,
    defaultValue: null
  },
  create_date: {
    type: DataTypes.DATE,
    allowNull: true
  },
  update_date: {
    type: DataTypes.DATE,
    allowNull: true
  },
  alert_info_json: {
    type: DataTypes.TEXT('medium'),
    allowNull: true
  },
  popup_close: {
    type: DataTypes.INTEGER,
    allowNull: true,
    defaultValue: 0
  }
}, {
  tableName: 'tb_alert_history',
  timestamps: false
});

export default AlertHistory; 