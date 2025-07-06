'use strict';

import { Sequelize } from 'sequelize';
import mariadbConfig from '../services/database/mariadb.config.js';
import Camera from './Camera.js';
import ScheduleModel from './schedule.js';

// mariadbConfig.config에서 정보 추출
const { database, user, password, host, port } = mariadbConfig.config;

const sequelize = new Sequelize(
  database,
  user,
  password,
  {
    host,
    dialect: 'mariadb',
    port,
    logging: false,
    timezone: '+09:00',  // 한국 시간대 설정
    dialectOptions: {
      timezone: '+09:00'  // MariaDB 시간대 설정
    }
  }
);

// 모델 초기화
const models = {
  Camera,
  Schedule: ScheduleModel(sequelize)
};

// 관계 초기화
Object.keys(models).forEach(modelName => {
  if (models[modelName].associate) {
    models[modelName].associate(models);
  }
});

export { sequelize, models };
export default sequelize; 