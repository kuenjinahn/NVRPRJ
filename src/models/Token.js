import { Model, DataTypes } from 'sequelize';
import sequelize from './index.js';

class Token extends Model { }

Token.init(
  {
    id: {
      type: DataTypes.INTEGER,
      primaryKey: true,
      autoIncrement: true
    },
    token: {
      type: DataTypes.STRING(2048),
      allowNull: false,
      unique: true
    },
    valid: {
      type: DataTypes.BOOLEAN,
      allowNull: false,
      defaultValue: true
    }
  },
  {
    sequelize,
    modelName: 'Token',
    tableName: 'tokens',
    timestamps: true
  }
);

export default Token; 