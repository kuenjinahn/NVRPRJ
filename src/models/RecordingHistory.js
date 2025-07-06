import { DataTypes } from 'sequelize';

export default (sequelize) => {
  const RecordingHistory = sequelize.define('RecordingHistory', {
    id: {
      type: DataTypes.INTEGER,
      primaryKey: true,
      autoIncrement: true
    },
    fk_camera_id: {
      type: DataTypes.INTEGER,
      allowNull: false,
      defaultValue: 0,
      field: 'fk_camera_id',
    },
    scheduleId: {
      type: DataTypes.INTEGER,
      allowNull: false,
      defaultValue: 0,
      field: 'fk_schedule_id'
    },
    cameraName: {
      type: DataTypes.STRING(100),
      allowNull: true,
      field: 'camera_name'
    },
    startTime: {
      type: DataTypes.DATE,
      allowNull: true,
      field: 'start_time'
    },
    endTime: {
      type: DataTypes.DATE,
      allowNull: true,
      field: 'end_time'
    },
    duration: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0,
      field: 'duration'
    },
    filename: {
      type: DataTypes.STRING(1024),
      allowNull: true,
      field: 'file_path'
    },
    fileSize: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0,
      field: 'file_size'
    },
    recordType: {
      type: DataTypes.STRING(20),
      allowNull: true,
      field: 'record_type'
    },
    status: {
      type: DataTypes.STRING(20),
      allowNull: true,
      field: 'status'
    },
    resolution: {
      type: DataTypes.STRING(20),
      allowNull: true,
      field: 'resolution'
    },
    bitrate: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0,
      field: 'bitrate'
    },
    framerate: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0,
      field: 'framerate'
    },
    codec: {
      type: DataTypes.STRING(20),
      allowNull: true,
      field: 'codec'
    },
    createDate: {
      type: DataTypes.DATE,
      allowNull: true,
      field: 'create_date'
    },
    updateDate: {
      type: DataTypes.DATE,
      allowNull: true,
      field: 'update_date'
    }
  }, {
    tableName: 'tb_recording_history',
    timestamps: false,
    charset: 'utf8mb4',
    collate: 'utf8mb4_general_ci'
  });

  return RecordingHistory;
}; 