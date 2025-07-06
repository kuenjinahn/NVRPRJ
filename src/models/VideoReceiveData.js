import { DataTypes } from 'sequelize';
import sequelize from '../database/config.js';

const VideoReceiveData = sequelize.define('VideoReceiveData', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  fk_camera_id: {
    type: DataTypes.INTEGER,
    allowNull: false
  },
  create_date: {
    type: DataTypes.DATE,
    allowNull: false,
    defaultValue: DataTypes.NOW
  },
  data_raw: {
    type: DataTypes.TEXT('long'),
    allowNull: true,
    get() {
      const val = this.getDataValue('data_raw');
      try {
        return val ? JSON.parse(val) : null;
      } catch {
        return null;
      }
    }
  },
  data_value: {
    type: DataTypes.TEXT('long'),
    allowNull: true,
    get() {
      const val = this.getDataValue('data_value');
      try {
        return val ? JSON.parse(val) : null;
      } catch {
        return null;
      }
    }
  }
}, {
  tableName: 'tb_video_receive_data',
  timestamps: false
});

export default VideoReceiveData; 