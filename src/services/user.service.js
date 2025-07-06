import db from '../models/index.js';

class UserService {
  async getAllUsers() {
    return await db.User.findAll();
  }

  async getUserById(id) {
    return await db.User.findByPk(id);
  }

  async createUser(userData) {
    return await db.User.create(userData);
  }

  async updateUser(id, userData) {
    const user = await db.User.findByPk(id);
    if (!user) {
      throw new Error('User not found');
    }
    return await user.update(userData);
  }

  async deleteUser(id) {
    const user = await db.User.findByPk(id);
    if (!user) {
      throw new Error('User not found');
    }
    await user.destroy();
    return true;
  }
}

export default new UserService(); 