import { DataTypes } from 'sequelize';
import sequelize from '../database/config.js';

const AccessHistory = sequelize.define('AccessHistory', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  userId: {
    type: DataTypes.STRING,
    allowNull: false
  },
  userName: {
    type: DataTypes.STRING,
    allowNull: false
  },
  token: {
    type: DataTypes.STRING,
    allowNull: false
  },
  ip_address: {
    type: DataTypes.STRING(50),
    allowNull: false
  },
  access_type: {
    type: DataTypes.INTEGER,
    allowNull: false
  },
  login_time: {
    type: DataTypes.DATE,
    allowNull: false
  },
  logout_time: {
    type: DataTypes.DATE,
    allowNull: false
  },
  create_date: {
    type: DataTypes.DATE,
    allowNull: false
  }
}, {
  tableName: 'tb_access_history',
  timestamps: false
});

export default AccessHistory; 