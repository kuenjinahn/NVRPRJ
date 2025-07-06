import { DataTypes } from 'sequelize';

export default (sequelize) => {
  const EventHistory = sequelize.define('EventHistory', {
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
    camera_name: {
      type: DataTypes.STRING(255),
      allowNull: false,
      defaultValue: '0'
    },
    event_accur_time: {
      type: DataTypes.DATE,
      allowNull: true
    },
    event_type: {
      type: DataTypes.STRING(5),
      allowNull: true
    },
    event_data_json: {
      type: DataTypes.TEXT('medium'),
      allowNull: true
    },
    fk_detect_zone_id: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0
    },
    detected_image_url: {
      type: DataTypes.STRING(255),
      allowNull: true,
      defaultValue: ''
    },
    create_date: {
      type: DataTypes.DATE,
      allowNull: true
    }
  }, {
    tableName: 'tb_event_history',
    timestamps: false
  });

  return EventHistory;
}; 
