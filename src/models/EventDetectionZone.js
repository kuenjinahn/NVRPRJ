import { DataTypes } from 'sequelize';

export default (sequelize) => {
  const EventDetectionZone = sequelize.define('EventDetectionZone', {
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
    zone_desc: {
      type: DataTypes.STRING(255),
      allowNull: false,
      defaultValue: '0'
    },
    zone_type: {
      type: DataTypes.STRING(5),
      allowNull: true
    },
    zone_segment_json: {
      type: DataTypes.STRING(255),
      allowNull: false,
      defaultValue: '0'
    },
    zone_params_json: {
      type: DataTypes.STRING(255),
      allowNull: false,
      defaultValue: '0'
    },
    zone_active: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 0
    },
    alert_level: {
      type: DataTypes.INTEGER,
      allowNull: true,
      defaultValue: 1
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
    tableName: 'tb_event_detection_zone',
    timestamps: false
  });

  return EventDetectionZone;
}; 