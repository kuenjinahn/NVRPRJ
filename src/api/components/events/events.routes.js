'use strict';

import * as EventsController from './events.controller.js';
import LoggerService from '../../../services/logger/logger.service.js';
import express, { Router } from 'express';

const router = Router();
const { log } = LoggerService;

// Pelco-D 패킷 생성 함수
function createPelcoDPacket(address = 0x01, command1, command2, data1, data2) {
  const sync = 0xFF;
  const checksum = (address + command1 + command2 + data1 + data2) % 256;
  return Buffer.from([sync, address, command1, command2, data1, data2, checksum]);
}

// PNT 프로토콜 패킷 생성 함수 (Python 소스 기반)
function createPNTPacket(pid, dataBytes = []) {
  const RMID = 0xB8;  // 184
  const TMID = 0xAC;  // 172
  const PNT_ID = 0x01; // 장치 Address는 내부 고정(비노출)

  const data = Array.isArray(dataBytes) ? dataBytes : [];
  const base = [RMID, TMID, PNT_ID, pid, data.length, ...data];

  // 체크섬 계산 (2의 보수)
  const total = base.reduce((sum, byte) => (sum + byte) & 0xFF, 0);
  const checksum = ((~total) + 1) & 0xFF;

  return Buffer.from([...base, checksum]);
}

// 16비트 정수를 리틀 엔디안 바이트 배열로 변환
function intToLE16(n) {
  n &= 0xFFFF;
  return [n & 0xFF, (n >> 8) & 0xFF];
}

// PNT 프로토콜 PID 상수
const PNT_PID = {
  PRESET_SAVE: 24,      // 0x18
  PRESET_RECALL: 25,    // 0x19
  TOUR: 46,             // 0x2E (1 = start, 0 = stop)
  SET_EACH_TOUR_DATA: 222  // 0xDE: [D0=preset(1~8), D1~D2= speed(rpm LSB/MSB), D3=delay(1~255s)]
};

// TCP로 패킷 전송 함수
async function sendTCPPacket(ip, port, packet) {
  return new Promise((resolve, reject) => {
    import('net').then(({ default: net }) => {
      const client = new net.Socket();

      client.connect(port, ip, () => {
        log.info(`PTZ TCP 연결 성공: ${ip}:${port}`);
        client.write(packet);
        client.end();
        resolve(true);
      });

      client.on('error', (err) => {
        log.error(`PTZ TCP 연결 오류: ${ip}:${port}`, err);
        client.destroy();
        reject(err);
      });

      client.on('close', () => {
        log.info(`PTZ TCP 연결 종료: ${ip}:${port}`);
      });

      // 5초 타임아웃
      setTimeout(() => {
        client.destroy();
        reject(new Error('PTZ TCP 연결 타임아웃'));
      }, 5000);
    }).catch(err => {
      log.error('Net module import 오류:', err);
      reject(new Error('Net module을 불러올 수 없습니다'));
    });
  });
}

// eventHistory CRUD
router.get('/eventHistory', EventsController.getAllEventHistory);
router.get('/eventHistory/:id', EventsController.getEventHistoryById);
router.post('/eventHistory', EventsController.addEventHistory);
router.put('/eventHistory/:id', EventsController.updateEventHistory);
router.delete('/eventHistory/:id', EventsController.deleteEventHistory);

// 이미지 파일 제공 API (POST, body에서 path 받음)
router.post('/image', EventsController.getImageFile);

// EventSetting API
router.get('/eventSetting/:id', EventsController.getEventSetting);
router.get('/eventSetting', EventsController.getEventSetting);
router.post('/eventSetting', EventsController.createEventSetting);
router.put('/eventSetting/:id', EventsController.updateEventSetting);


// EventDetectionZone API
router.put('/detectionZone/inPageZone', EventsController.updateInPageZone);
router.get('/detectionZone', EventsController.getAllDetectionZones);
router.get('/detectionZone/:id', EventsController.getDetectionZoneById);
router.get('/detectionZone/camera/:cameraId', EventsController.getDetectionZonesByCameraId);
router.post('/detectionZone', EventsController.addDetectionZone);
router.put('/detectionZone/:id', EventsController.updateDetectionZone);
router.delete('/detectionZone/:id', EventsController.deleteDetectionZone);

// PTZ 제어 API
/**
 * @swagger
 * /api/ptz/move:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PTZ 카메라 이동 제어
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *          schema:
 *            type: object
 *            required:
 *              - direction
 *              - ip
 *              - port
 *            properties:
 *              direction:
 *                type: string
 *                enum: [up, down, left, right]
 *                description: 이동 방향
 *              speed:
 *                type: number
 *                minimum: 1
 *                maximum: 63
 *                default: 32
 *                description: 이동 속도
 *              ip:
 *                type: string
 *                description: 카메라 IP 주소
 *              port:
 *                type: number
 *                description: 카메라 포트
 *     responses:
 *       200:
 *         description: PTZ 이동 명령 전송 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/move', async (req, res) => {
  try {
    const { direction, speed, ip, port } = req.body;

    if (!direction || !ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: direction, ip, port'
      });
    }

    log.info(`PTZ Move command: ${direction}, speed: ${speed}, target: ${ip}:${port}`);

    let command1, command2, data1, data2;

    // Pelco-D 명령어 매핑
    switch (direction) {
      case 'up':
        command1 = 0x00; command2 = 0x08; data1 = 0x00; data2 = speed || 32;
        break;
      case 'down':
        command1 = 0x00; command2 = 0x10; data1 = 0x00; data2 = speed || 32;
        break;
      case 'left':
        command1 = 0x00; command2 = 0x04; data1 = speed || 32; data2 = 0x00;
        break;
      case 'right':
        command1 = 0x00; command2 = 0x02; data1 = speed || 32; data2 = 0x00;
        break;
      default:
        return res.status(400).json({
          success: false,
          message: `지원하지 않는 이동 방향: ${direction}`
        });
    }

    const packet = createPelcoDPacket(0x01, command1, command2, data1, data2);
    log.info(`PTZ Move packet: ${direction}, speed: ${speed || 32}, packet: ${packet.toString('hex')}`);

    await sendTCPPacket(ip, port, packet);

    res.json({
      success: true,
      message: 'PTZ 이동 명령 전송 완료',
      data: {
        direction,
        speed: speed || 32,
        ip,
        port,
        packet: packet.toString('hex')
      }
    });

  } catch (error) {
    log.error('PTZ Move Error:', error);
    res.status(500).json({
      success: false,
      message: 'PTZ 이동 명령 전송 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/stop:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PTZ 카메라 정지
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *          schema:
 *            type: object
 *            required:
 *              - ip
 *              - port
 *            properties:
 *              ip:
 *                type: string
 *                description: 카메라 IP 주소
 *              port:
 *                type: number
 *                description: 카메라 포트
 *     responses:
 *       200:
 *         description: PTZ 정지 명령 전송 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/stop', async (req, res) => {
  try {
    const { ip, port } = req.body;

    if (!ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: ip, port'
      });
    }

    log.info(`PTZ Stop command: target: ${ip}:${port}`);

    const packet = createPelcoDPacket(0x01, 0x00, 0x00, 0x00, 0x00);
    log.info(`PTZ Stop packet: ${packet.toString('hex')}`);

    await sendTCPPacket(ip, port, packet);

    res.json({
      success: true,
      message: 'PTZ 정지 명령 전송 완료',
      data: {
        command: 'stop',
        ip,
        port,
        packet: packet.toString('hex')
      }
    });

  } catch (error) {
    log.error('PTZ Stop Error:', error);
    res.status(500).json({
      success: false,
      message: 'PTZ 정지 명령 전송 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/zoom:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PTZ 카메라 줌 제어
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *          schema:
 *            type: object
 *            required:
 *              - direction
 *              - ip
 *              - port
 *            properties:
 *              direction:
 *                type: string
 *                enum: [in, out]
 *                description: 줌 방향
 *              ip:
 *                type: string
 *                description: 카메라 IP 주소
 *              port:
 *                type: number
 *                description: 카메라 포트
 *     responses:
 *       200:
 *         description: PTZ 줌 명령 전송 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/zoom', async (req, res) => {
  try {
    const { direction, ip, port } = req.body;

    if (!direction || !ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: direction, ip, port'
      });
    }

    log.info(`PTZ Zoom command: ${direction}, target: ${ip}:${port}`);

    let command1, command2, data1, data2;

    switch (direction) {
      case 'in':
        command1 = 0x00; command2 = 0x20; data1 = 0x00; data2 = 0x00;
        break;
      case 'out':
        command1 = 0x00; command2 = 0x40; data1 = 0x00; data2 = 0x00;
        break;
      default:
        return res.status(400).json({
          success: false,
          message: `지원하지 않는 줌 방향: ${direction}`
        });
    }

    const packet = createPelcoDPacket(0x01, command1, command2, data1, data2);
    log.info(`PTZ Zoom packet: ${direction}, packet: ${packet.toString('hex')}`);

    await sendTCPPacket(ip, port, packet);

    res.json({
      success: true,
      message: 'PTZ 줌 명령 전송 완료',
      data: {
        direction,
        ip,
        port,
        packet: packet.toString('hex')
      }
    });

  } catch (error) {
    log.error('PTZ Zoom Error:', error);
    res.status(500).json({
      success: false,
      message: 'PTZ 줌 명령 전송 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/focus:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PTZ 카메라 포커스 제어
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *          schema:
 *            type: object
 *            required:
 *              - direction
 *              - ip
 *              - port
 *            properties:
 *              direction:
 *                type: string
 *                enum: [in, out]
 *                description: 포커스 방향
 *              ip:
 *                type: string
 *                description: 카메라 IP 주소
 *              port:
 *                type: number
 *                description: 카메라 포트
 *     responses:
 *       200:
 *         description: PTZ 포커스 명령 전송 완료
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/focus', async (req, res) => {
  try {
    const { direction, ip, port } = req.body;

    if (!direction || !ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: direction, ip, port'
      });
    }

    log.info(`PTZ Focus command: ${direction}, target: ${ip}:${port}`);

    let command1, command2, data1, data2;

    switch (direction) {
      case 'in':
        command1 = 0x00; command2 = 0x80; data1 = 0x00; data2 = 0x00;
        break;
      case 'out':
        command1 = 0x00; command2 = 0x01; data1 = 0x00; data2 = 0x00;
        break;
      default:
        return res.status(400).json({
          success: false,
          message: `지원하지 않는 포커스 방향: ${direction}`
        });
    }

    const packet = createPelcoDPacket(0x01, command1, command2, data1, data2);
    log.info(`PTZ Focus packet: ${direction}, packet: ${packet.toString('hex')}`);

    await sendTCPPacket(ip, port, packet);

    res.json({
      success: true,
      message: 'PTZ 포커스 명령 전송 완료',
      data: {
        direction,
        ip,
        port,
        packet: packet.toString('hex')
      }
    });

  } catch (error) {
    log.error('PTZ Focus Error:', error);
    res.status(500).json({
      success: false,
      message: 'PTZ 포커스 명령 전송 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/wiper:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PTZ 카메라 와이퍼 제어
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *          schema:
 *            required:
 *              - action
 *              - ip
 *              - port
 *            properties:
 *              action:
 *                type: string
 *                enum: [on, off]
 *                description: 와이퍼 동작
 *              ip:
 *                type: string
 *                description: 카메라 IP 주소
 *              port:
 *                type: number
 *                description: 카메라 포트
 *     responses:
 *       200:
 *         description: PTZ 와이퍼 명령 전송 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/wiper', async (req, res) => {
  try {
    const { action, ip, port } = req.body;

    if (!action || !ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: action, ip, port'
      });
    }

    log.info(`PTZ Wiper command: ${action}, target: ${ip}:${port}`);

    let preset;

    switch (action) {
      case 'on':
        preset = 184; // 와이퍼 ON 프리셋
        break;
      case 'off':
        preset = 183; // 와이퍼 OFF 프리셋
        break;
      default:
        return res.status(400).json({
          success: false,
          message: `지원하지 않는 와이퍼 동작: ${action}`
        });
    }

    // Pelco-D Preset Call 명령어
    const packet = createPelcoDPacket(0x01, 0x00, 0x07, 0x00, preset);
    log.info(`PTZ Wiper packet: ${action}, preset: ${preset}, packet: ${packet.toString('hex')}`);

    await sendTCPPacket(ip, port, packet);

    res.json({
      success: true,
      message: `PTZ 와이퍼 ${action.toUpperCase()} 명령 전송 완료`,
      data: {
        action,
        preset,
        ip,
        port,
        packet: packet.toString('hex')
      }
    });

  } catch (error) {
    log.error('PTZ Wiper Error:', error);
    res.status(500).json({
      success: false,
      message: 'PTZ 와이퍼 명령 전송 실패',
      error: error.message
    });
  }
});

// =========================
// PNT 프리셋 및 투어 API
// =========================

/**
 * @swagger
 * /api/ptz/preset/save:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PNT 프리셋 저장
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - presetNumber
 *               - ip
 *               - port
 *             properties:
 *               presetNumber:
 *                 type: number
 *                 minimum: 1
 *                 maximum: 8
 *                 description: 프리셋 번호 (1-8)
 *               ip:
 *                 type: string
 *                 description: 카메라 IP 주소
 *               port:
 *                 type: number
 *                 description: 카메라 포트
 *     responses:
 *       200:
 *         description: 프리셋 저장 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/preset/save', async (req, res) => {
  try {
    const { presetNumber, ip, port } = req.body;

    if (!presetNumber || !ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: presetNumber, ip, port'
      });
    }

    if (presetNumber < 1 || presetNumber > 8) {
      return res.status(400).json({
        success: false,
        message: '프리셋 번호는 1-8 사이여야 합니다'
      });
    }

    log.info(`PNT Preset Save: ${presetNumber}, target: ${ip}:${port}`);

    const packet = createPNTPacket(PNT_PID.PRESET_SAVE, [presetNumber & 0xFF]);
    log.info(`PNT Preset Save packet: ${packet.toString('hex')}`);

    await sendTCPPacket(ip, port, packet);

    res.json({
      success: true,
      message: `프리셋 ${presetNumber} 저장 완료`,
      data: {
        presetNumber,
        ip,
        port,
        packet: packet.toString('hex')
      }
    });

  } catch (error) {
    log.error('PNT Preset Save Error:', error);
    res.status(500).json({
      success: false,
      message: '프리셋 저장 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/preset/recall:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PNT 프리셋 호출
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - presetNumber
 *               - ip
 *               - port
 *             properties:
 *               presetNumber:
 *                 type: number
 *                 minimum: 1
 *                 maximum: 8
 *                 description: 프리셋 번호 (1-8)
 *               ip:
 *                 type: string
 *                 description: 카메라 IP 주소
 *               port:
 *                 type: number
 *                 description: 카메라 포트
 *     responses:
 *       200:
 *         description: 프리셋 호출 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/preset/recall', async (req, res) => {
  try {
    const { presetNumber, ip, port } = req.body;

    if (!presetNumber || !ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: presetNumber, ip, port'
      });
    }

    if (presetNumber < 1 || presetNumber > 8) {
      return res.status(400).json({
        success: false,
        message: '프리셋 번호는 1-8 사이여야 합니다'
      });
    }

    log.info(`PNT Preset Recall: ${presetNumber}, target: ${ip}:${port}`);

    const packet = createPNTPacket(PNT_PID.PRESET_RECALL, [presetNumber & 0xFF]);
    log.info(`PNT Preset Recall packet: ${packet.toString('hex')}`);

    await sendTCPPacket(ip, port, packet);

    res.json({
      success: true,
      message: `프리셋 ${presetNumber} 호출 완료`,
      data: {
        presetNumber,
        ip,
        port,
        packet: packet.toString('hex')
      }
    });

  } catch (error) {
    log.error('PNT Preset Recall Error:', error);
    res.status(500).json({
      success: false,
      message: '프리셋 호출 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/tour/start:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PNT 투어 시작
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - ip
 *               - port
 *             properties:
 *               ip:
 *                 type: string
 *                 description: 카메라 IP 주소
 *               port:
 *                 type: number
 *                 description: 카메라 포트
 *     responses:
 *       200:
 *         description: 투어 시작 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/tour/start', async (req, res) => {
  try {
    const { ip, port } = req.body;

    if (!ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: ip, port'
      });
    }

    log.info(`PNT Tour Start: target: ${ip}:${port}`);

    const packet = createPNTPacket(PNT_PID.TOUR, [1]);
    log.info(`PNT Tour Start packet: ${packet.toString('hex')}`);

    await sendTCPPacket(ip, port, packet);

    res.json({
      success: true,
      message: '투어 시작 완료',
      data: {
        ip,
        port,
        packet: packet.toString('hex')
      }
    });

  } catch (error) {
    log.error('PNT Tour Start Error:', error);
    res.status(500).json({
      success: false,
      message: '투어 시작 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/tour/stop:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PNT 투어 정지
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - ip
 *               - port
 *             properties:
 *               ip:
 *                 type: string
 *                 description: 카메라 IP 주소
 *               port:
 *                 type: number
 *                 description: 카메라 포트
 *     responses:
 *       200:
 *         description: 투어 정지 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/tour/stop', async (req, res) => {
  try {
    const { ip, port } = req.body;

    if (!ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: ip, port'
      });
    }

    log.info(`PNT Tour Stop: target: ${ip}:${port}`);

    const packet = createPNTPacket(PNT_PID.TOUR, [0]);
    log.info(`PNT Tour Stop packet: ${packet.toString('hex')}`);

    await sendTCPPacket(ip, port, packet);

    res.json({
      success: true,
      message: '투어 정지 완료',
      data: {
        ip,
        port,
        packet: packet.toString('hex')
      }
    });

  } catch (error) {
    log.error('PNT Tour Stop Error:', error);
    res.status(500).json({
      success: false,
      message: '투어 정지 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/tour/step:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PNT 투어 스텝 설정
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - presetNumber
 *               - speedRpm
 *               - delaySec
 *               - ip
 *               - port
 *             properties:
 *               presetNumber:
 *                 type: number
 *                 minimum: 1
 *                 maximum: 8
 *                 description: 프리셋 번호 (1-8)
 *               speedRpm:
 *                 type: number
 *                 description: 투어 속도 (RPM)
 *               delaySec:
 *                 type: number
 *                 minimum: 1
 *                 maximum: 255
 *                 description: 지연 시간 (초)
 *               ip:
 *                 type: string
 *                 description: 카메라 IP 주소
 *               port:
 *                 type: number
 *                 description: 카메라 포트
 *     responses:
 *       200:
 *         description: 투어 스텝 설정 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/tour/step', async (req, res) => {
  try {
    const { presetNumber, speedRpm, delaySec, ip, port } = req.body;

    if (!presetNumber || !speedRpm || !delaySec || !ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: presetNumber, speedRpm, delaySec, ip, port'
      });
    }

    if (presetNumber < 1 || presetNumber > 8) {
      return res.status(400).json({
        success: false,
        message: '프리셋 번호는 1-8 사이여야 합니다'
      });
    }

    if (delaySec < 1 || delaySec > 255) {
      return res.status(400).json({
        success: false,
        message: '지연 시간은 1-255 초 사이여야 합니다'
      });
    }

    log.info(`PNT Tour Step: preset=${presetNumber}, speed=${speedRpm}rpm, delay=${delaySec}s, target: ${ip}:${port}`);

    // 속도를 리틀 엔디안으로 변환
    const [speedLSB, speedMSB] = intToLE16(speedRpm);
    const delay = Math.max(1, Math.min(255, Math.floor(delaySec)));

    const packet = createPNTPacket(PNT_PID.SET_EACH_TOUR_DATA, [
      presetNumber & 0xFF,
      speedLSB,
      speedMSB,
      delay
    ]);

    log.info(`PNT Tour Step packet: ${packet.toString('hex')}`);

    await sendTCPPacket(ip, port, packet);

    res.json({
      success: true,
      message: `투어 스텝 설정 완료 (Preset ${presetNumber})`,
      data: {
        presetNumber,
        speedRpm,
        delaySec: delay,
        ip,
        port,
        packet: packet.toString('hex')
      }
    });

  } catch (error) {
    log.error('PNT Tour Step Error:', error);
    res.status(500).json({
      success: false,
      message: '투어 스텝 설정 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/tour/setup:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PNT 투어 전체 설정 (1-3 스텝)
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - speedRpm
 *               - delaySec
 *               - ip
 *               - port
 *             properties:
 *               speedRpm:
 *                 type: number
 *                 description: 투어 속도 (RPM)
 *               delaySec:
 *                 type: number
 *                 minimum: 1
 *                 maximum: 255
 *                 description: 지연 시간 (초)
 *               ip:
 *                 type: string
 *                 description: 카메라 IP 주소
 *               port:
 *                 type: number
 *                 description: 카메라 포트
 *     responses:
 *       200:
 *         description: 투어 설정 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/tour/setup', async (req, res) => {
  try {
    const { speedRpm, delaySec, ip, port } = req.body;

    if (!speedRpm || !delaySec || !ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: speedRpm, delaySec, ip, port'
      });
    }

    if (delaySec < 1 || delaySec > 255) {
      return res.status(400).json({
        success: false,
        message: '지연 시간은 1-255 초 사이여야 합니다'
      });
    }

    log.info(`PNT Tour Setup: speed=${speedRpm}rpm, delay=${delaySec}s, target: ${ip}:${port}`);

    const results = [];
    const delay = Math.max(1, Math.min(255, Math.floor(delaySec)));

    // 1-3번 프리셋에 대해 투어 스텝 설정
    for (let preset = 1; preset <= 3; preset++) {
      const [speedLSB, speedMSB] = intToLE16(speedRpm);

      const packet = createPNTPacket(PNT_PID.SET_EACH_TOUR_DATA, [
        preset,
        speedLSB,
        speedMSB,
        delay
      ]);

      log.info(`PNT Tour Step ${preset} packet: ${packet.toString('hex')}`);

      await sendTCPPacket(ip, port, packet);

      results.push({
        preset,
        speedRpm,
        delaySec: delay,
        packet: packet.toString('hex')
      });
    }

    res.json({
      success: true,
      message: '투어 설정 완료 (Preset 1-3)',
      data: {
        speedRpm,
        delaySec: delay,
        ip,
        port,
        results
      }
    });

  } catch (error) {
    log.error('PNT Tour Setup Error:', error);
    res.status(500).json({
      success: false,
      message: '투어 설정 실패',
      error: error.message
    });
  }
});

export default router;

