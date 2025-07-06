/* eslint-disable unicorn/prevent-abbreviations */
'use-strict';

import crypto from 'crypto';

import ConfigService from '../../services/config/config.service.js';
import LoggerService from '../../services/logger/logger.service.js';
import User from '../../models/User.js';
import Token from '../../models/Token.js';

import * as UserModel from '../components/users/users.model.js';

const { log } = LoggerService;
const validPermissions = ConfigService.interface.permissionLevels;

function generateToken(length = 64) {
  return crypto.randomBytes(length).toString('hex');
}

const loginAttempt = () => {
  log.warn(
    `Failed login attempt! If you have forgotten your password you can reset to the default of master/master by removing the user in the database and then restarting camera.ui`,
    'Interface',
    'interface'
  );
};

export const hasAuthValidFields = (req, res, next) => {
  let errors = [];

  if (req.body) {
    if (!req.body.userId) {
      errors.push('Missing userId field');
    }
    if (!req.body.password) {
      errors.push('Missing password field');
    }

    if (errors.length) {
      return res.status(400).send({ errors: errors.join(',') });
    } else {
      return next();
    }
  } else {
    return res.status(400).send({ errors: 'Missing userId and password fields' });
  }
};

export const hasValidFields = (req, res, next) => {
  let errors = [];

  if (req.body) {
    if (!req.body.userId) {
      errors.push('Missing userId field');
    }

    if (!req.body.password) {
      errors.push('Missing password field');
    }

    if (req.body.permissionLevel && !req.body.permissionLevel.some((level) => validPermissions.includes(level))) {
      errors.push('Permission level is not valid');
    }

    return errors.length > 0
      ? res.status(422).send({
        statusCode: 422,
        message: errors.join(','),
      })
      : next();
  } else {
    return res.status(400).send({
      statusCode: 400,
      message: 'Bad request',
    });
  }
};

export const isPasswordAndUserMatch = async (req, res, next) => {
  try {
    const user = await User.findOne({ where: { userId: req.body.userId } });

    if (!user) {
      loginAttempt();
      return res.status(403).send({
        statusCode: 403,
        message: 'Forbidden',
      });
    } else if (!user?.password) {
      loginAttempt();
      return res.status(403).send({
        statusCode: 403,
        message: 'Password missing',
      });
    } else {
      let passwordFields = user.password.split('$');
      let salt = passwordFields[0];
      let hash = crypto.createHmac('sha512', salt).update(req.body.password).digest('base64');

      if (hash === passwordFields[1]) {
        req.body = {
          id: user.id,
          userId: user.userId,
          sessionTimer: user.sessionTimer,
          permissionLevel: user.permissionLevel,
          photo: user.photo,
        };

        return next();
      } else {
        loginAttempt();
        return res.status(401).send({
          statusCode: 401,
          message: 'Invalid userId or password',
        });
      }
    }
  } catch (error) {
    console.error('Error in isPasswordAndUserMatch:', error);
    return res.status(500).send({
      statusCode: 500,
      message: 'Internal server error',
    });
  }
};
