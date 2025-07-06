'use-strict';

import User from '../../../models/User.js';
import AccessHistory from '../../../models/AccessHistory.js';

export const list = async () => {
  return await User.findAll();
};

export const findByName = async (userId) => {
  return await User.findOne({ where: { userId } });
};

export const createUser = async (userData) => {
  const user = {
    userId: userData.userId,
    userName: userData.userName,
    userDept: userData.userDept,
    password: userData.password,
    permissionLevel: userData.permissionLevel || 1,
    sessionTimer: userData.sessionTimer || 14400 // 4h
  };

  return await User.create(user);
};

export const patchUser = async (userId, userData) => {
  const user = await User.findOne({ where: { userId } });
  if (!user) return null;

  return await user.update(userData);
};

export const removeByName = async (userId) => {
  return await User.destroy({ where: { userId } });
};

export const getAccessHistory = async (options = {}) => {
  const whereClause = {};

  return await AccessHistory.findAll({
    where: whereClause,
    order: [['login_time', 'DESC']],
    ...options
  });
};
