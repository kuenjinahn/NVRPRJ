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
  // 인증 검증을 우회하고 무조건 통과
  return next();
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
