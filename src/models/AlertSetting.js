import { DataTypes } from 'sequelize';
import sequelize from '../database/config.js';

const AlertSetting = sequelize.define('AlertSetting', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  alert_setting_json: {
    type: DataTypes.STRING(2048),
    allowNull: true
  },
  fk_user_id: {
    type: DataTypes.INTEGER,
    allowNull: false
  },
  create_date: {
    type: DataTypes.DATE,
    allowNull: true
  },
  update_date: {
    type: DataTypes.DATE,
    allowNull: true
  }
}, {
  tableName: 'tb_alert_setting',
  timestamps: false
});

export default AlertSetting; 