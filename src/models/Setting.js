import { DataTypes } from 'sequelize';

export default (sequelize) => {
  const Setting = sequelize.define('Setting', {
    id: {
      type: DataTypes.STRING(36),
      primaryKey: true,
      allowNull: false
    },
    category: {
      type: DataTypes.STRING(50),
      allowNull: true
    },
    settings: {
      type: DataTypes.JSON,
      allowNull: true,
      validate: {
        isValidJSON(value) {
          if (value !== null && typeof value !== 'object') {
            throw new Error('settings must be a valid JSON object');
          }
        }
      }
    },
    created_at: {
      type: DataTypes.DATE,
      allowNull: false,
      defaultValue: DataTypes.NOW
    },
    updated_at: {
      type: DataTypes.DATE,
      allowNull: false,
      defaultValue: DataTypes.NOW
    }
  }, {
    tableName: 'settings',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: 'updated_at',
    charset: 'latin1',
    collate: 'latin1_general_ci'
  });

  return Setting;
}; 