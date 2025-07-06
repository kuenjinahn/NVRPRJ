import { DataTypes } from 'sequelize';

export default (sequelize) => {
  const EventSetting = sequelize.define('EventSetting', {
    id: {
      type: DataTypes.INTEGER,
      primaryKey: true,
      autoIncrement: true
    },
    temperature_json: {
      type: DataTypes.STRING(1024),
      allowNull: true,
      defaultValue: null
    },
    alert_json: {
      type: DataTypes.STRING(1024),
      allowNull: true,
      defaultValue: null
    },
    object_json: {
      type: DataTypes.STRING(1024),
      allowNull: true,
      defaultValue: null
    },
    system_json: {
      type: DataTypes.STRING(1024),
      allowNull: true,
      defaultValue: null
    },
    in_page_zone: {
      type: DataTypes.INTEGER,
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
    }
  }, {
    tableName: 'tb_event_setting',
    timestamps: false
  });

  return EventSetting;
}; 