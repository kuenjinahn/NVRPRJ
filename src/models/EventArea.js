import { DataTypes } from 'sequelize';

export default (sequelize) => {
  const EventArea = sequelize.define('EventArea', {
    cameraId: {
      type: DataTypes.INTEGER,
      allowNull: false
    },
    options: {
      type: DataTypes.JSON,
      allowNull: false
    },
    regions: {
      type: DataTypes.JSON,
      allowNull: false
    },
    description: {
      type: DataTypes.STRING,
      allowNull: false
    }
  });

  return EventArea;
}; 
