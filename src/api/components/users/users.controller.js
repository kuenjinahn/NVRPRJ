/* eslint-disable unicorn/prevent-abbreviations */
'use-strict';

import crypto from 'crypto';
import multer from 'multer';

import ConfigService from '../../../services/config/config.service.js';

import * as UserModel from './users.model.js';

export const insert = async (req, res) => {
  try {
    const userExist = await UserModel.findByName(req.body.userId);

    if (userExist) {
      return res.status(409).send({
        statusCode: 409,
        message: 'User already exists',
      });
    }

    const users = await UserModel.list();

    if (users.some((usr) => usr.permissionLevel === 2) && req.body.permissionLevel === 2) {
      return res.status(409).send({
        statusCode: 409,
        message: 'User with ADMIN permission level already exists',
      });
    }

    let salt = crypto.randomBytes(16).toString('base64');
    let hash = crypto.createHmac('sha512', salt).update(req.body.password).digest('base64');

    req.body.password = salt + '$' + hash;

    await UserModel.createUser(req.body);

    res.status(201).send({
      userId: req.body.userId,
      userName: req.body.userName,
      userDept: req.body.userDept,
      permissionLevel: req.body.permissionLevel,
    });
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const list = async (req, res, next) => {
  try {
    let result = await UserModel.list();

    for (const user of result) {
      delete user.password;
    }

    res.locals.items = result;

    return next();
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const getByName = async (req, res) => {
  try {
    const user = await UserModel.findByName(req.params.name);

    if (!user) {
      return res.status(404).send({
        statusCode: 404,
        message: 'User not exists',
      });
    }

    delete user.password;

    res.status(200).send(user);
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const patchByName = async (req, res) => {
  try {
    console.log('patchByName req.params:', req.params);
    let user = await UserModel.findByName(req.params.userId);
    console.log('patchByName user:', user);
    if (!user) {
      return res.status(404).send({
        statusCode: 404,
        message: 'User not exists',
      });
    }
    console.log('1patchByName req.body:', req.body);
    if (req.body === undefined || Object.keys(req?.body).length === 0) {
      return res.status(400).send({
        statusCode: 400,
        message: 'Bad request',
      });
    }
    console.log('2patchByName req.body:', req.body);
    if (req.body.userId && req.params.userId !== req.body.userId) {
      user = await UserModel.findByName(req.body.userId);

      if (user) {
        return res.status(422).send({
          statusCode: 422,
          message: 'User already exists',
        });
      }
    }
    console.log('patchByName req.body.password:', req.body.password);
    if (req.body.password) {
      let salt = crypto.randomBytes(16).toString('base64');
      let hash = crypto.createHmac('sha512', salt).update(req.body.password).digest('base64');
      req.body.password = salt + '$' + hash;
    }
    console.log('patchByName req.body:', req.body);
    await UserModel.patchUser(req.params.userId, req.body);
    console.log('patchByName res.status(204).send({});');
    res.status(204).send({});
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const removeByName = async (req, res) => {
  try {
    const user = await UserModel.findByName(req.params.userId);

    if (!user) {
      return res.status(404).send({
        statusCode: 404,
        message: 'User not exists',
      });
    }

    if (user.permissionLevel === 2) {
      return res.status(409).send({
        statusCode: 409,
        message: 'User with ADMIN permission level can not be removed',
      });
    }

    await UserModel.removeByName(req.params.userId);

    res.status(204).send({});
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};

export const getAccessHistory = async (req, res) => {
  try {
    const accessHistory = await UserModel.getAccessHistory();

    res.status(200).send(accessHistory);
  } catch (error) {
    res.status(500).send({
      statusCode: 500,
      message: error.message,
    });
  }
};
