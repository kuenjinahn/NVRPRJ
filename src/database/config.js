import { Sequelize } from 'sequelize';
import mariadbConfig from '../services/database/mariadb.config.js';

const { database, user, password, host, port } = mariadbConfig.config;

const sequelize = new Sequelize(
  database,
  user,
  password,
  {
    host,
    port,
    dialect: 'mariadb',
    logging: false,
    pool: {
      max: 5,
      min: 0,
      acquire: 30000,
      idle: 10000
    }
  }
);

export default sequelize; 