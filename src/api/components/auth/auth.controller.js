/* eslint-disable unicorn/prevent-abbreviations */
'use-strict';

import crypto from 'crypto';
import jwt from 'jsonwebtoken';

import ConfigService from '../../../services/config/config.service.js';
import AccessHistory from '../../../models/AccessHistory.js';
import User from '../../../models/User.js';

import Database from '../../database.js';
import Socket from '../../socket.js';

import * as AuthModel from './auth.model.js';

const jwtSecret = ConfigService.interface.jwt_secret;

// 클라이언트 IP 추출 함수 (디버깅 추가)
const getClientIp = (req) => {
  console.log('=== IP Debug Info ===');
  console.log('req.headers:', req.headers);
  console.log('req.ip:', req.ip);
  console.log('req.connection.remoteAddress:', req.connection?.remoteAddress);
  console.log('req.socket.remoteAddress:', req.socket?.remoteAddress);

  // X-Forwarded-For 헤더에서 첫 번째 IP 추출
  const xForwardedFor = req.headers['x-forwarded-for'];
  if (xForwardedFor) {
    const ips = xForwardedFor.split(',').map(ip => ip.trim());
    console.log('X-Forwarded-For IPs:', ips);
    return ips[0];
  }

  // X-Real-IP 헤더 확인
  if (req.headers['x-real-ip']) {
    console.log('Using X-Real-IP:', req.headers['x-real-ip']);
    return req.headers['x-real-ip'];
  }

  // 기본 HTTP 헤더들 확인
  const possibleHeaders = [
    'x-client-ip',
    'x-forwarded',
    'x-cluster-client-ip',
    'forwarded-for',
    'forwarded',
    'cf-connecting-ip'
  ];

  for (const header of possibleHeaders) {
    if (req.headers[header]) {
      console.log(`Using ${header}:`, req.headers[header]);
      return req.headers[header];
    }
  }

  // req.connection.remoteAddress 확인
  if (req.connection && req.connection.remoteAddress) {
    let ip = req.connection.remoteAddress;
    console.log('Raw connection IP:', ip);
    // IPv6에서 IPv4 매핑된 주소 처리
    if (ip.includes('::ffff:')) {
      ip = ip.split('::ffff:')[1];
      console.log('Converted IPv4:', ip);
    }
    return ip;
  }

  // req.socket.remoteAddress 확인
  if (req.socket && req.socket.remoteAddress) {
    let ip = req.socket.remoteAddress;
    console.log('Raw socket IP:', ip);
    if (ip.includes('::ffff:')) {
      ip = ip.split('::ffff:')[1];
      console.log('Converted IPv4:', ip);
    }
    return ip;
  }

  // Express의 req.ip 사용
  if (req.ip) {
    let ip = req.ip;
    console.log('Express req.ip:', ip);
    if (ip.includes('::ffff:')) {
      ip = ip.split('::ffff:')[1];
      console.log('Converted IPv4:', ip);
    }
    return ip;
  }

  console.log('Using fallback IP: 127.0.0.1');
  return '127.0.0.1';
};

export const check = (req, res) => {
  try {
    res.status(200).send({
      status: 'OK',
    });
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const login = async (req, res) => {
  try {
    // 기본 세션 타이머를 8시간으로 설정 (28800초)
    let sessionTimer = req.body.sessionTimer || 28800;
    let salt = crypto.randomBytes(16).toString('base64');

    req.body.salt = salt;

    let token = jwt.sign(req.body, jwtSecret, { expiresIn: sessionTimer });
    await AuthModel.insert(token);

    // userId로 userName 조회
    const user = await User.findOne({ where: { userId: req.body.userId } });
    const userName = user ? user.userName : req.body.userId;

    // AccessHistory에 로그인 기록 추가
    await AccessHistory.create({
      userId: req.body.userId,
      userName: userName,
      token: token,
      ip_address: getClientIp(req),
      access_type: 1, // 로그인
      login_time: new Date(),
      logout_time: new Date(),
      create_date: new Date()
    });

    // 토큰 만료 5분 전에 자동으로 갱신
    if (sessionTimer / 3600 <= 25) {
      setTimeout(() => {
        AuthModel.invalidateByToken(token);
        Socket.io.emit('invalidToken', token);
      }, (sessionTimer - 300) * 1000); // 5분(300초) 전에 만료 처리
    }

    res.status(201).send({
      access_token: token,
      token_type: 'Bearer',
      expires_in: sessionTimer,
      expires_at: new Date((Date.now() / 1000 + sessionTimer) * 1000),
      refresh_token: crypto.randomBytes(40).toString('hex') // 리프레시 토큰 추가
    });
  } catch (error) {
    console.error('[LOGIN ERROR]', error);
    res.status(500).send({
      statusCode: 500,
      message: '로그인 처리 중 오류가 발생했습니다.',
      error: error.message
    });
  }
};

export const logout = async (req, res) => {
  try {
    let authHeader = req.headers['authorization'] || req.headers['Authorization'];
    let authorization = authHeader ? authHeader.split(/\s+/) : false;

    let token = authorization && authorization[0] === 'Bearer' ? authorization[1] : false;

    if (token) {
      // 토큰에서 사용자 정보 추출
      const decoded = jwt.verify(token, jwtSecret);

      // userId로 userName 조회
      const user = await User.findOne({ where: { userId: decoded.userId } });
      const userName = user ? user.userName : decoded.userId;

      // AccessHistory에 로그아웃 기록 추가
      await AccessHistory.create({
        userId: decoded.userId,
        userName: userName,
        token: token,
        ip_address: getClientIp(req),
        access_type: 2, // 로그아웃
        login_time: new Date(),
        logout_time: new Date(),
        create_date: new Date()
      });

      await AuthModel.invalidateByToken(token);
    }

    await Database.interfaceDB.write();

    res.sendStatus(200);
  } catch (error) {
    console.error('[LOGOUT ERROR]', error);
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const logoutAll = async (req, res) => {
  try {
    AuthModel.invalidateAll();
    await Database.interfaceDB.write();
    res.sendStatus(200);
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};
