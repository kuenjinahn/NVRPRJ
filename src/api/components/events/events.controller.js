/* eslint-disable unicorn/prevent-abbreviations */
'use-strict';

import * as EventsModel from './events.model.js';
import path from 'path';
import fs from 'fs';
import net from 'net';

// Camera configuration
const CAMERA_IP = '175.201.204.165';
const CAMERA_PORT = 32000;

// ROI Packet functions
function buildRoiPacket(cmd, data) {
  const header = 0xFF;
  const address = 0x00;
  const cmd_h = (cmd >> 8) & 0xFF;
  const cmd_l = cmd & 0xFF;
  const data_h = (data >> 8) & 0xFF;
  const data_l = data & 0xFF;
  const payload = [address, cmd_h, cmd_l, data_h, data_l];
  const checksum = payload.reduce((a, b) => a + b, 0) & 0xFF;
  return Buffer.from([header, ...payload, checksum]);
}

function sendPacketToCamera(packet, cameraIp, cameraPort) {
  return new Promise((resolve, reject) => {
    const client = new net.Socket();
    client.setTimeout(5000);

    client.connect(cameraPort, cameraIp, () => {
      console.log('[sendPacketToCamera] Connected to camera');
      client.write(packet);
    });

    client.on('data', (data) => {
      console.log('[sendPacketToCamera] Received response:', data);
      client.destroy();
      resolve(data);
    });

    client.on('error', (err) => {
      console.error('[sendPacketToCamera] Error:', err);
      client.destroy();
      reject(err);
    });

    client.on('timeout', () => {
      console.error('[sendPacketToCamera] Timeout');
      client.destroy();
      reject(new Error('Timeout'));
    });
  });
}

async function sendRoiSetting(roiIndex, startX, startY, endX, endY, cameraIp, cameraPort, roiEnable) {
  roiIndex += 1; //인덱스에서 1씩 더해줘야함함
  try {
    console.log('[sendRoiSetting] Sending ROI settings:', {
      roiIndex,
      startX,
      startY,
      endX,
      endY,
      cameraIp,
      cameraPort,
      roiEnable
    });

    const baseAddr = 0x2320 + roiIndex * 0x10;
    const params = [
      [baseAddr + 0, startX],
      [baseAddr + 1, startY],
      [baseAddr + 2, endX],
      [baseAddr + 3, endY]
    ];

    for (const [cmd, data] of params) {
      console.log('[sendRoiSetting] Sending command:', { cmd: cmd.toString(16), data });
      const packet = buildRoiPacket(cmd, data);
      await sendPacketToCamera(packet, cameraIp, cameraPort);
    }

    // ROI Enable packet (0x2310)
    const enableCmd = 0x2310;
    const enableData = typeof roiEnable === 'string'
      ? parseInt(roiEnable, 2)
      : (typeof roiEnable === 'number' ? roiEnable : 0x3FF);
    console.log('[sendRoiSetting] Sending ROI Enable packet:', { cmd: enableCmd.toString(16), data: enableData });
    const enablePacket = buildRoiPacket(enableCmd, enableData);
    await sendPacketToCamera(enablePacket, cameraIp, cameraPort);

    console.log('[sendRoiSetting] ROI settings and enable sent successfully');
  } catch (error) {
    console.error('[sendRoiSetting] Error:', error);
    throw error;
  }
}

export const getAllEventHistory = async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const pageSize = parseInt(req.query.pageSize) || 10;
    const offset = (page - 1) * pageSize;
    const limit = pageSize;

    const { startDate, endDate, label } = req.query;
    const filters = {
      startDate: startDate ? new Date(startDate) : null,
      endDate: endDate ? new Date(endDate) : null,
      label,
      offset,
      limit
    };
    const { count, rows } = await EventsModel.getAllEventHistory(filters);
    const totalItems = count;
    const totalPages = Math.ceil(totalItems / pageSize);
    const pagination = {
      currentPage: page,
      pageSize: pageSize,
      totalPages: totalPages,
      totalItems: totalItems,
      nextPage: page < totalPages ? `${req.path}?page=${page + 1}` : null,
      prevPage: page > 1 ? `${req.path}?page=${page - 1}` : null,
    };
    res.json({ pagination, result: rows });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const getEventHistoryById = async (req, res) => {
  try {
    const data = await EventsModel.getEventHistoryById(req.params.id);
    if (!data) return res.status(404).json({ error: 'Not found' });
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const addEventHistory = async (req, res) => {
  try {
    const event = req.body;
    if (!event.id) {
      return res.status(400).json({ error: 'id is required' });
    }
    const result = await EventsModel.addEventHistory(event);
    res.status(201).json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const updateEventHistory = async (req, res) => {
  try {
    const result = await EventsModel.updateEventHistory(req.params.id, req.body);
    if (!result) return res.status(404).json({ error: 'Not found' });
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const deleteEventHistory = async (req, res) => {
  try {
    const result = await EventsModel.deleteEventHistory(req.params.id);
    if (!result) return res.status(404).json({ error: 'Not found' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

// 이미지 파일 제공 API
export const getImageFile = (req, res) => {
  let filePath = req.body.path;
  console.log('[getImageFile] process.cwd():', process.cwd());
  if (!filePath) {
    console.log('[getImageFile] No path specified');
    return res.status(400).send('No path specified');
  }
  // filePath에서 ../ 제거
  filePath = filePath.replace(/\.\.\//g, '');
  const absPath = path.resolve(filePath);
  console.log('[getImageFile] absPath:', absPath);
  fs.access(absPath, fs.constants.R_OK, (err) => {
    if (err) {
      console.log(`[getImageFile] File not found: ${absPath}`);
      return res.status(404).send('File not found');
    }
    // 파일이 존재하면 크기와 데이터 확인
    fs.stat(absPath, (err, stats) => {
      if (err) {
        console.log(`[getImageFile] fs.stat error: ${err}`);
      } else {
        console.log(`[getImageFile] File exists: ${absPath}, size: ${stats.size} bytes`);
        if (stats.size === 0) {
          console.log('[getImageFile] File is empty');
        } else {
          // 파일 데이터 일부 읽어서 로그
          fs.readFile(absPath, (err, data) => {
            if (err) {
              console.log(`[getImageFile] fs.readFile error: ${err}`);
            } else {
              console.log(`[getImageFile] File read success, data length: ${data.length}`);
            }
            // 파일 전송
            res.sendFile(absPath);
          });
          return;
        }
      }
      // 파일 전송 (빈 파일이거나 stat 에러)
      res.sendFile(absPath);
    });
  });
};

export const getEventSetting = async (req, res) => {
  try {
    const id = req.params.id;
    const data = await EventsModel.getEventSetting(id);
    if (!data) return res.status(404).json({ error: 'Not found' });
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const updateEventSetting = async (req, res) => {
  try {
    const id = req.params.id;
    const result = await EventsModel.updateEventSetting(id, req.body);
    if (!result) return res.status(404).json({ error: 'Not found' });
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const updateInPageZone = async (req, res) => {
  try {
    const { in_page_zone } = req.body;

    if (in_page_zone === undefined || in_page_zone === null) {
      return res.status(400).json({ error: 'in_page_zone is required' });
    }

    // in_page_zone 값이 0 또는 1인지 확인
    if (![0, 1].includes(in_page_zone)) {
      return res.status(400).json({ error: 'in_page_zone must be 0 or 1' });
    }

    const result = await EventsModel.updateInPageZone(in_page_zone);
    res.json({ success: true, in_page_zone: result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const createEventSetting = async (req, res) => {
  try {
    const result = await EventsModel.createEventSetting(req.body);
    res.status(201).json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

// EventDetectionZone API
export const getAllDetectionZones = async (req, res) => {
  try {
    const data = await EventsModel.getAllDetectionZones();
    const formattedData = data.map(zone => ({
      id: zone.id,
      cameraId: zone.fk_camera_id,
      description: zone.zone_desc,
      type: zone.zone_type,
      regions: JSON.parse(zone.zone_segment_json || '[]'),
      options: JSON.parse(zone.zone_params_json || '{}'),
      active: zone.zone_active,
      alertLevel: zone.alert_level,
      createDate: zone.create_date,
      updateDate: zone.update_date
    }));
    res.json(formattedData);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const getDetectionZoneById = async (req, res) => {
  try {
    const data = await EventsModel.getDetectionZoneById(req.params.id);
    if (!data) return res.status(404).json({ error: 'Not found' });

    const formattedData = {
      id: data.id,
      cameraId: data.fk_camera_id,
      description: data.zone_desc,
      type: data.zone_type,
      regions: JSON.parse(data.zone_segment_json || '[]'),
      options: JSON.parse(data.zone_params_json || '{}'),
      active: data.zone_active,
      createDate: data.create_date,
      updateDate: data.update_date
    };
    res.json(formattedData);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const getDetectionZonesByCameraId = async (req, res) => {
  try {
    const data = await EventsModel.getDetectionZonesByCameraId(req.params.cameraId);
    const formattedData = data.map(zone => ({
      id: zone.id,
      cameraId: zone.fk_camera_id,
      description: zone.zone_desc,
      type: zone.zone_type,
      regions: JSON.parse(zone.zone_segment_json || '[]'),
      options: JSON.parse(zone.zone_params_json || '{}'),
      active: zone.zone_active,
      createDate: zone.create_date,
      updateDate: zone.update_date
    }));
    res.json(formattedData);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const addDetectionZone = async (req, res) => {
  try {
    const zoneData = {
      cameraId: req.body.cameraId,
      description: req.body.description,
      type: req.body.type,
      regions: req.body.regions,
      options: req.body.options,
      active: req.body.active
    };

    const regionCoords = zoneData.regions[0]?.coords || [];
    const startX = Math.min(...regionCoords.map(coord => coord[0]));
    const startY = Math.min(...regionCoords.map(coord => coord[1]));
    const endX = Math.max(...regionCoords.map(coord => coord[0]));
    const endY = Math.max(...regionCoords.map(coord => coord[1]));

    console.log('[addDetectionZone] converted coordinates:', {
      startX,
      startY,
      endX,
      endY,
      originalRegions: zoneData.regions
    });

    console.log('[addDetectionZone] zoneData:', zoneData);
    const result = await EventsModel.addDetectionZone(zoneData);

    if (result) {
      try {
        await sendRoiSetting(req.body.roiIndex, startX, startY, endX, endY, CAMERA_IP, CAMERA_PORT, req.body.roiEnable);
      } catch (roiError) {
        console.error('[addDetectionZone] ROI setting error:', roiError);
        // Continue even if ROI setting fails
      }
    }

    res.status(201).json(result);
  } catch (err) {
    console.error('[addDetectionZone] Error:', err);
    res.status(500).json({ error: err.message });
  }
};

export const updateDetectionZone = async (req, res) => {
  try {
    const zoneData = {
      cameraId: req.body.cameraId,
      description: req.body.description,
      type: req.body.type,
      regions: req.body.regions,
      options: req.body.options,
      active: req.body.active,
      roiIndex: req.body.roiIndex
    };
    console.log('[updateDetectionZone] zoneData:', zoneData);

    const regionCoords = zoneData.regions[0]?.coords || [];
    const startX = Math.min(...regionCoords.map(coord => coord[0])) + 7;
    const startY = Math.min(...regionCoords.map(coord => coord[1])) + 2;
    const endX = Math.max(...regionCoords.map(coord => coord[0])) - 2;
    const endY = Math.max(...regionCoords.map(coord => coord[1]));

    console.log('[updateDetectionZone] converted coordinates:', {
      startX,
      startY,
      endX,
      endY,
      originalRegions: zoneData.regions
    });

    const result = await EventsModel.updateDetectionZone(req.params.id, zoneData);
    if (!result) return res.status(404).json({ error: 'Not found' });

    try {
      await sendRoiSetting(req.body.roiIndex, startX, startY, endX, endY, CAMERA_IP, CAMERA_PORT, req.body.roiEnable);
    } catch (roiError) {
      console.error('[updateDetectionZone] ROI setting error:', roiError);
      // Continue even if ROI setting fails
    }

    res.json(result);
  } catch (err) {
    console.error('[updateDetectionZone] Error:', err);
    res.status(500).json({ error: err.message });
  }
};

export const deleteDetectionZone = async (req, res) => {
  try {
    const result = await EventsModel.deleteDetectionZone(req.params.id);
    if (!result) return res.status(404).json({ error: 'Not found' });

    const roiEnable = req.query.roiEnable;
    const roiIndex = req.query.roiIndex;
    if (roiEnable !== undefined && roiIndex !== undefined) {
      try {
        await sendRoiSetting(roiIndex, 0, 0, 0, 0, CAMERA_IP, CAMERA_PORT, roiEnable);
      } catch (roiError) {
        console.error('[deleteDetectionZone] ROI setting error:', roiError);
        // Continue even if ROI setting fails
      }
    }

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

