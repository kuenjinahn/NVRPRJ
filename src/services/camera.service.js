import db from '../models/index.js';

class CameraService {
  async getAllCameras() {
    return await db.Camera.findAll();
  }

  async getCameraById(id) {
    return await db.Camera.findByPk(id);
  }

  async createCamera(cameraData) {
    return await db.Camera.create(cameraData);
  }

  async updateCamera(id, cameraData) {
    const camera = await db.Camera.findByPk(id);
    if (!camera) {
      throw new Error('Camera not found');
    }
    return await camera.update(cameraData);
  }

  async deleteCamera(id) {
    const camera = await db.Camera.findByPk(id);
    if (!camera) {
      throw new Error('Camera not found');
    }
    await camera.destroy();
    return true;
  }
}

export default new CameraService(); 