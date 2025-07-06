/* eslint-disable unicorn/prevent-abbreviations */
'use-strict';

import crypto from 'crypto';
import jwt from 'jsonwebtoken';

import ConfigService from '../../services/config/config.service.js';

import * as AuthModel from '../components/auth/auth.model.js';
import * as UserModel from '../components/users/users.model.js';

const jwtSecret = ConfigService.interface.jwt_secret;

const getBearerToken = async (userId, password) => {
  if (userId && userId !== '' && password && password !== '') {
    const user = await UserModel.findByName(userId);
    if (user) {
      let passwordFields = user.password.split('$');
      let salt = passwordFields[0];
      console.log(`===============>[getBearerToken] password: ${user.password}`);
      let hash = crypto.createHmac('sha512', salt).update(password).digest('base64');

      if (hash === passwordFields[1]) {
        const payload = {
          id: user.id,
          userId: user.userId,
          sessionTimer: user.sessionTimer,
          permissionLevel: user.permissionLevel,
          photo: user.photo,
        };

        let sessionTimer = payload.sessionTimer || 14400;
        payload.salt = crypto.randomBytes(16).toString('base64');

        const token = jwt.sign(payload, jwtSecret, { expiresIn: sessionTimer });
        await AuthModel.insert(token, user.id);

        return token;
      }
    }
  }
};

export const validJWTNeeded = async (req, res, next) => {
  if (req.query.userId && req.query.password) {
    const authorization = await getBearerToken(req.query.userId, req.query.password);
    if (authorization) {
      req.headers['authorization'] = `Bearer ${authorization}`;
    }
  }

  if (req.headers['authorization'] || req.headers['Authorization']) {
    try {
      let authHeader = req.headers['authorization'] || req.headers['Authorization'];
      let authorization = authHeader.split(/\s+/);

      if (authorization[0] !== 'Bearer') {
        return res.status(401).send({
          statusCode: 401,
          message: '인증 토큰 형식이 올바르지 않습니다.',
          error: 'INVALID_TOKEN_FORMAT'
        });
      }

      // 토큰 검증
      const decoded = jwt.verify(authorization[1], jwtSecret);

      // 토큰 만료 시간 체크
      const now = Math.floor(Date.now() / 1000);
      if (decoded.exp - now < 300) { // 5분 이내로 만료되는 경우
        // 새로운 토큰 발급
        const newToken = jwt.sign(
          {
            id: decoded.id,
            userId: decoded.userId,
            sessionTimer: decoded.sessionTimer,
            permissionLevel: decoded.permissionLevel,
            photo: decoded.photo
          },
          jwtSecret,
          { expiresIn: decoded.sessionTimer || 28800 }
        );

        // 기존 토큰 무효화
        await AuthModel.invalidateByToken(authorization[1]);
        // 새 토큰 저장
        await AuthModel.insert(newToken);

        // 응답 헤더에 새 토큰 추가
        res.setHeader('X-New-Token', newToken);
      }

      // 데이터베이스에서 토큰 유효성 확인
      const user = await AuthModel.findByToken(authorization[1]);
      if (!user || (user && !user.valid)) {
        return res.status(401).send({
          statusCode: 401,
          message: '토큰이 만료되었거나 유효하지 않습니다.',
          error: 'TOKEN_EXPIRED_OR_INVALID'
        });
      }

      req.jwt = decoded;
      return next();
    } catch (error) {
      console.error('[AUTH] JWT verification error:', error);

      let errorMessage = '인증 오류가 발생했습니다.';
      let errorCode = 'AUTH_ERROR';

      if (error.name === 'TokenExpiredError') {
        errorMessage = '토큰이 만료되었습니다. 다시 로그인해주세요.';
        errorCode = 'TOKEN_EXPIRED';
      } else if (error.name === 'JsonWebTokenError') {
        errorMessage = '유효하지 않은 토큰입니다.';
        errorCode = 'INVALID_TOKEN';
      }

      return res.status(401).send({
        statusCode: 401,
        message: errorMessage,
        error: errorCode
      });
    }
  } else {
    return res.status(401).send({
      statusCode: 401,
      message: '인증 토큰이 필요합니다.',
      error: 'TOKEN_REQUIRED'
    });
  }
};

export const validJWTOptional = async (req, res, next) => {
  if (req.query.userId && req.query.password) {
    const authorization = await getBearerToken(req.query.userId, req.query.password);
    if (authorization) {
      req.headers['authorization'] = `Bearer ${authorization}`;
    }
  }
  if (req.headers['authorization'] || req.headers['Authorization']) {
    try {
      let authHeader = req.headers['authorization'] || req.headers['Authorization'];
      let authorization = authHeader.split(/\s+/);

      if (authorization[0] === 'Bearer') {
        //check if user/token exists in database and is still valid
        const user = AuthModel.findByToken(authorization[1]);

        if (!user || (user && user.valid)) {
          req.jwt = jwt.verify(authorization[1], jwtSecret);
        }
      }
    } catch {
      return next();
    }
  }

  return next();
};
