'use-strict';

import Database from '../../database.js';
import Token from '../../../models/Token.js';

export const list = () => {
  return Database.tokens.chain.get('tokens').value();
};

export const insert = async (token) => {
  try {
    return await Token.create({ token, valid: true });
  } catch (error) {
    console.error('Error inserting token:', error);
    throw error;
  }
};

export const findByToken = async (token) => {
  try {
    return await Token.findOne({ where: { token: token } });
  } catch (error) {
    console.error('Error finding token:', error);
    throw error;
  }
};

export const invalidateToken = async (token) => {
  try {
    return await Token.update(
      { valid: false },
      { where: { token: token } }
    );
  } catch (error) {
    console.error('Error invalidating token:', error);
    throw error;
  }
};

export const invalidateAll = () => {
  let users = Database.tokensDB.chain.get('tokens').value();

  for (const user of users) {
    user.valid = false;
  }

  return Database.tokensDB.chain.get('tokens').set(users).value();
};

export const invalidateByToken = async (token) => {
  try {
    return await Token.update(
      { valid: false },
      { where: { token: token } }
    );
  } catch (error) {
    console.error('Error invalidating token:', error);
    throw error;
  }
};
