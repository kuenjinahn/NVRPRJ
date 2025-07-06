import { DataTypes } from 'sequelize';
import sequelize from '../database/config.js';

const User = sequelize.define('User', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  userId: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
  userName: {
    type: DataTypes.STRING,
    allowNull: false
  },
  userDept: {
    type: DataTypes.STRING,
    allowNull: false
  },
  password: {
    type: DataTypes.STRING,
    allowNull: false
  },
  permissionLevel: {
    type: DataTypes.INTEGER,
    allowNull: false,
    defaultValue: 1
  },
  sessionTimer: {
    type: DataTypes.INTEGER,
    allowNull: true
  }
}, {
  tableName: 'tb_users',
  timestamps: true
});

export default User; 