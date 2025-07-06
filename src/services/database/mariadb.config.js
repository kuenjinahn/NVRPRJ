// src/services/database/mariadb.config.js
import mariadb from 'mariadb';
import ConfigService from '../config/config.service.js';
import LoggerService from '../logger/logger.service.js';

const { log } = LoggerService;

// 기본 데이터베이스 설정
//20.41.121.184
const dbConfig = {
  host: 'localhost',
  port: 3306,
  user: 'dbadmin',
  password: 'p#ssw0rd',
  database: 'nvrdb',
  connectionLimit: 10,
  connectTimeout: 10000
};

// MariaDB 연결 풀 생성
const pool = mariadb.createPool(dbConfig);

// MariaDB 설정 객체
const config = {
  // 기본적으로 MariaDB 사용 여부
  enabled: true,
  // 데이터 동기화 여부
  sync: true,
  // 데이터베이스 연결 설정
  ...dbConfig,
  // 연결 테스트 함수
  testConnection: async () => {
    let conn;
    try {
      conn = await pool.getConnection();
      await conn.ping();
      log.info('MariaDB 연결 성공');
      return true;
    } catch (error) {
      log.error('MariaDB 연결 실패:', error);
      return false;
    } finally {
      if (conn) {
        await conn.release();
      }
    }
  }
};

// config 객체만 export 하도록 수정
export default { config };