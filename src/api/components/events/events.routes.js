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

export default router;

