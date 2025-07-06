import { DataTypes } from 'sequelize';
import sequelize from '../database/config.js';

const Camera = sequelize.define('Camera', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  name: {
    type: DataTypes.STRING(255),
    allowNull: false
  },
  motionTimeout: {
    type: DataTypes.INTEGER,
    defaultValue: 15
  },
  recordOnMovement: {
    type: DataTypes.BOOLEAN,
    defaultValue: false
  },
  prebuffering: {
    type: DataTypes.BOOLEAN,
    defaultValue: false
  },
  videoConfig: {
    type: DataTypes.TEXT('long'),
    allowNull: false
  },
  mqtt: {
    type: DataTypes.TEXT('long'),
    allowNull: true
  },
  smtp: {
    type: DataTypes.TEXT('long'),
    allowNull: true
  },
  videoanalysis: {
    type: DataTypes.TEXT('long'),
    allowNull: true
  },
  settings: {
    type: DataTypes.TEXT('long'),
    allowNull: true
  },
  prebufferLength: {
    type: DataTypes.INTEGER,
    defaultValue: 4
  },
  create_date: {
    type: DataTypes.DATE,
    allowNull: false
  },
  update_dt: {
    type: DataTypes.DATE,
    allowNull: false
  }
}, {
  tableName: 'tb_cameras',
  timestamps: false,
  charset: 'latin1',
  collate: 'latin1_general_ci'
});

export default Camera; 
