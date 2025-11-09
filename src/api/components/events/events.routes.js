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

// Digest 인증을 위한 헬퍼 함수
async function createDigestAuth(username, password, method, uri, realm, nonce, qop, nc, cnonce) {
  const crypto = await import('crypto');

  // HA1 = MD5(username:realm:password)
  const ha1 = crypto.createHash('md5').update(`${username}:${realm}:${password}`).digest('hex');

  // HA2 = MD5(method:uri)
  const ha2 = crypto.createHash('md5').update(`${method}:${uri}`).digest('hex');

  // response = MD5(HA1:nonce:nc:cnonce:qop:HA2)
  const response = crypto.createHash('md5').update(`${ha1}:${nonce}:${nc}:${cnonce}:${qop}:${ha2}`).digest('hex');

  return `Digest username="${username}", realm="${realm}", nonce="${nonce}", uri="${uri}", qop=${qop}, nc=${nc}, cnonce="${cnonce}", response="${response}"`;
}

// Digest 인증을 사용한 HTTP 요청 함수
async function makeDigestRequest(url, username, password, options = {}) {
  const axios = (await import('axios')).default;
  const crypto = await import('crypto');

  log.info(`[인증] 요청 시작: ${url}`);

  // 먼저 Basic 인증 시도
  try {
    log.info(`[인증] Basic 인증 시도`);
    const response = await axios.get(url, {
      ...options,
      auth: {
        username: username,
        password: password
      }
    });
    log.info(`[인증] Basic 인증 성공: ${response.status}`);
    return response;
  } catch (basicError) {
    log.info(`[인증] Basic 인증 실패: ${basicError.response?.status}`);

    // Basic 인증 실패 시 Digest 인증 시도
    if (basicError.response && basicError.response.status === 401) {
      const wwwAuthenticate = basicError.response.headers['www-authenticate'];
      log.info(`[인증] WWW-Authenticate 헤더: ${wwwAuthenticate}`);

      if (wwwAuthenticate && wwwAuthenticate.startsWith('Digest')) {
        // Digest 인증 파라미터 파싱
        const realmMatch = wwwAuthenticate.match(/realm="([^"]+)"/);
        const nonceMatch = wwwAuthenticate.match(/nonce="([^"]+)"/);
        const qopMatch = wwwAuthenticate.match(/qop="([^"]+)"/);

        log.info(`[인증] Digest 파싱 결과 - realm: ${realmMatch?.[1]}, nonce: ${nonceMatch?.[1]}, qop: ${qopMatch?.[1]}`);

        if (realmMatch && nonceMatch && qopMatch) {
          const realm = realmMatch[1];
          const nonce = nonceMatch[1];
          const qop = qopMatch[1];

          // cnonce와 nc 생성
          const cnonce = crypto.randomBytes(16).toString('hex');
          const nc = '00000001';

          // URI 추출
          const urlObj = new URL(url);
          const uri = urlObj.pathname + urlObj.search;

          log.info(`[인증] Digest URI: ${uri}, cnonce: ${cnonce}, nc: ${nc}`);

          // Digest 인증 헤더 생성
          const authHeader = await createDigestAuth(username, password, 'GET', uri, realm, nonce, qop, nc, cnonce);
          log.info(`[인증] Digest 헤더: ${authHeader}`);

          // Digest 인증으로 두 번째 요청
          log.info(`[인증] Digest 인증 요청 시작`);
          return await axios.get(url, {
            ...options,
            headers: {
              ...options.headers,
              'Authorization': authHeader
            }
          });
        } else {
          log.error(`[인증] Digest 파라미터 파싱 실패 - realm: ${!!realmMatch}, nonce: ${!!nonceMatch}, qop: ${!!qopMatch}`);
        }
      } else {
        log.error(`[인증] Digest 인증이 아닙니다: ${wwwAuthenticate}`);
      }
    }
    throw basicError;
  }
}

// PNT 프로토콜 PID 상수 (명세 V4.1 준수)
// PID 타입: R=Read only, W=Parameter change(EEprom write), C=Command(Pan/tilt movement or action)
const PNT_PID = {
  // 0~100: 1 Byte 데이터
  PRESET_SAVE: 24,      // 0x18 - 프리셋 저장 (C: Command, 1 Byte)
  PRESET_RECALL: 25,    // 0x19 - 프리셋 호출 (C: Command, 1 Byte)
  ALARM_RESET: 26,      // 0x1A - 알람 리셋 (C: Command, 1 Byte)
  AUTO_SCAN_CMD: 27,    // 0x1B - 자동 스캔 명령 (C: Command, 1 Byte)
  PRESET_ACK: 32,       // 0x20 - 프리셋 호출 응답 (R: Read only, 1 Byte)
  TOUR: 46,             // 0x2E - 투어 제어 (C: Command, 1 Byte: 1=start, 0=stop)

  // 101~191: 2 Bytes 데이터
  // (해당 범위의 PID들은 2바이트 데이터 사용)

  // 192~253: N Bytes 데이터
  SET_EACH_TOUR_DATA: 222,  // 0xDE: W: Parameter change, N Bytes [D0=preset(1~8), D1~D2=speed(rpm LSB/MSB), D3=delay(1~255s)]
  PRESET_DATA: 200,     // 0xC8 - 프리셋 데이터 (R: Read only, N Bytes: Pan, Tilt, Zoom, Focus)
  LIMIT_POSI_DATA: 202  // 0xCA - PAN/TILT 제한 위치 데이터 (R: Read only, N Bytes)
};


// TCP로 패킷 전송 함수 (PNT 서버와 양방향 통신)
async function sendTCPPacket(ip, port, packet) {
  return new Promise((resolve, reject) => {
    import('net').then(({ default: net }) => {
      const client = new net.Socket();
      let responseData = Buffer.alloc(0);
      let isResolved = false;
      const startTime = Date.now();

      // 연결 타임아웃 설정 (5초)
      client.setTimeout(5000);

      // 연결 시도
      client.connect(port, ip, () => {
        log.info(`PTZ TCP 연결 성공: ${ip}:${port}`);
        client.write(packet);
        log.info(`PNT 패킷 전송: ${packet.toString('hex')}`);
      });

      client.on('data', (data) => {
        responseData = Buffer.concat([responseData, data]);
        log.info(`PNT 서버 응답 수신: ${data.toString('hex')}`);

        // 응답 수신 시 즉시 처리
        if (!isResolved) {
          isResolved = true;
          setTimeout(() => {
            client.destroy();
            resolve(parsePNTResponse(responseData));
          }, 100); // 100ms 대기 후 연결 종료
        }
      });

      client.on('close', () => {
        log.info(`PTZ TCP 연결 종료: ${ip}:${port}`);
        if (!isResolved) {
          isResolved = true;
          if (responseData.length > 0) {
            resolve(parsePNTResponse(responseData));
          } else {
            // 응답이 없어도 성공으로 처리 (PNT 서버가 응답하지 않는 경우)
            resolve({ success: true, message: '명령 전송 완료 (응답 없음)' });
          }
        }
      });

      client.on('error', (err) => {
        log.error(`PTZ TCP 연결 오류: ${ip}:${port}`, err);
        if (!isResolved) {
          isResolved = true;
          client.destroy();
          reject(err);
        }
      });

      client.on('timeout', () => {
        log.error(`PTZ TCP 연결 타임아웃: ${ip}:${port}`);
        if (!isResolved) {
          isResolved = true;
          client.destroy();
          reject(new Error('PTZ TCP 연결 타임아웃'));
        }
      });

      // 추가 안전장치: 3초 후 응답이 없으면 성공으로 처리
      setTimeout(() => {
        if (!isResolved) {
          isResolved = true;
          log.info(`PNT 명령 전송 완료 (타임아웃): ${ip}:${port}`);
          client.destroy();
          resolve({ success: true, message: '명령 전송 완료 (타임아웃)' });
        }
      }, 3000);

    }).catch(err => {
      log.error(`[PNT 모듈 오류] Net module import 실패: ${err.message}`);
      reject(new Error('Net module을 불러올 수 없습니다'));
    });
  });
}

// PNT 서버 응답 파싱 함수
function parsePNTResponse(responseData) {
  try {
    if (responseData.length < 6) {
      return { success: false, message: '응답 데이터가 너무 짧습니다' };
    }

    // PNT 프로토콜 응답 패킷 구조: [RMID, TMID, PNT_ID, PID, LEN, DATA..., CHECKSUM]
    const rmid = responseData[0];
    const tmid = responseData[1];
    const pnt_id = responseData[2];
    const pid = responseData[3];
    const dataLen = responseData[4];
    const payload = responseData.slice(5, 5 + dataLen);
    const checksum = responseData[5 + dataLen];

    // 응답 코드 확인
    if (payload.length > 0) {
      const responseCode = payload[0];

      // 프리셋 데이터 응답 (PID 200 - 0xC8) - 매뉴얼 표준
      if (pid === PNT_PID.PRESET_DATA && responseCode === 0x00 && payload.length >= 9) {
        // 매뉴얼에 따른 9바이트 데이터 구조 파싱
        // D0: 프리셋 번호, D1,2: Pan, D3,4: Tilt, D5,6: Zoom, D7,8: Focus
        const presetNum = payload[1];
        const pan = (payload[3] << 8) | payload[2];
        const tilt = (payload[5] << 8) | payload[4];
        const zoom = (payload[7] << 8) | payload[6];
        const focus = (payload[9] << 8) | payload[8];

        // 부호 있는 정수로 변환 (16비트)
        const signedPan = pan > 32767 ? pan - 65536 : pan;
        const signedTilt = tilt > 32767 ? tilt - 65536 : tilt;

        return {
          success: true,
          message: '프리셋 데이터 조회 성공',
          presetNumber: presetNum,
          ptzValues: {
            pan: signedPan,
            tilt: signedTilt,
            zoom: zoom,
            focus: focus
          }
        };
      }

      // 일반 응답 코드 처리
      switch (responseCode) {
        case 0x00:
          return { success: true, message: '명령 실행 성공' };
        case 0x01:
          return { success: false, message: '잘못된 명령어' };
        case 0x02:
          return { success: false, message: '잘못된 매개변수' };
        case 0x03:
          return { success: false, message: '장치 사용 중' };
        case 0x04:
          return { success: false, message: '구현되지 않음' };
        case 0xFF:
          return { success: false, message: '일반 오류' };
        default:
          return { success: true, message: `응답 코드: 0x${responseCode.toString(16)}` };
      }
    }

    return { success: true, message: '응답 수신 완료' };
  } catch (error) {
    log.error('PNT 응답 파싱 오류:', error);
    return { success: false, message: '응답 파싱 실패' };
  }
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
    const { direction, speed, ip } = req.body;
    const port = 33000; // PNT 서버 포트 고정

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
    const { ip } = req.body;
    const port = 33000; // PNT 서버 포트 고정

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
    const { direction, ip } = req.body;
    const port = 33000; // PNT 서버 포트 고정

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
    const { direction, ip } = req.body;
    const port = 33000; // PNT 서버 포트 고정

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
    const { action, ip } = req.body;
    const port = 33000; // PNT 서버 포트 고정

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
// 웹 API 기반 PTZ 제어 API (포트 80)
// =========================

/**
 * @swagger
 * /api/ptz/getPosition:
 *   get:
 *     tags: [PTZ Control]
 *     summary: PTZ 현재 위치 조회 (웹 API)
 *     parameters:
 *       - in: query
 *         name: ip
 *         required: true
 *         schema:
 *           type: string
 *         description: 카메라 IP 주소
 *       - in: query
 *         name: ptzNumber
 *         required: false
 *         schema:
 *           type: number
 *           minimum: 1
 *           maximum: 3
 *           default: 1
 *         description: 'PTZ 번호 (1-3, 기본값: 1)'
 *     responses:
 *       200:
 *         description: PTZ 위치 조회 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.get('/ptz/getPosition', async (req, res) => {
  try {
    const { ip, ptzNumber = 1 } = req.query;

    if (!ip) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: ip'
      });
    }

    // PTZ 번호 유효성 검사
    const ptzNum = parseInt(ptzNumber);
    if (ptzNum < 1 || ptzNum > 3) {
      return res.status(400).json({
        success: false,
        message: 'PTZ 번호는 1-3 사이여야 합니다'
      });
    }

    log.info(`[웹 API] PTZ 현재 위치 조회: ${ip}:80, PTZNumber=${ptzNum}`);

    // 웹 API 호출: http://IP:80/api/ptz.cgi?PTZNumber={ptzNumber}&GetPTZPosition=do
    const apiUrl = `http://${ip}:80/api/ptz.cgi?PTZNumber=${ptzNum}&GetPTZPosition=do`;

    // Digest 인증을 사용한 요청
    const response = await makeDigestRequest(apiUrl, 'root', 'cctv1350!!', {
      timeout: 5000
    });

    const responseText = response.data;
    log.info(`[웹 API] 응답: ${responseText}`);

    // 응답 파싱: PTZ.{ptzNumber}.Position=345.88,38.00,1.0000
    const positionMatch = responseText.match(new RegExp(`PTZ\\.${ptzNum}\\.Position=([^,]+),([^,]+),([^,]+)`));

    if (!positionMatch) {
      throw new Error(`위치 정보를 파싱할 수 없습니다. 응답: ${responseText}`);
    }

    const pan = parseFloat(positionMatch[1]);
    const tilt = parseFloat(positionMatch[2]);
    const zoom = parseFloat(positionMatch[3]);

    log.info(`[웹 API] 파싱된 위치: Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}`);

    res.json({
      success: true,
      message: 'PTZ 현재 위치 조회 성공',
      data: {
        ip,
        port: 80,
        ptzValues: {
          pan,
          tilt,
          zoom
        },
        rawResponse: responseText
      }
    });

  } catch (error) {
    log.error('[웹 API] PTZ 위치 조회 오류:', error);
    res.status(500).json({
      success: false,
      message: 'PTZ 위치 조회 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/setPosition:
 *   post:
 *     tags: [PTZ Control]
 *     summary: PTZ 절대 위치 설정 (웹 API)
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - ip
 *               - pan
 *               - tilt
 *               - zoom
 *               - presetNumber
 *             properties:
 *               ip:
 *                 type: string
 *                 description: 카메라 IP 주소
 *               pan:
 *                 type: number
 *                 minimum: 0
 *                 maximum: 359
 *                 description: Pan 값 (0-359)
 *               tilt:
 *                 type: number
 *                 minimum: -90
 *                 maximum: 90
 *                 description: Tilt 값 (-90-90)
 *               zoom:
 *                 type: number
 *                 minimum: 1
 *                 description: Zoom 값 (1-Max Zoom)
 *               presetNumber:
 *                 type: number
 *                 minimum: 1
 *                 maximum: 3
 *                 description: 프리셋 번호 (1-3)
 *     responses:
 *       200:
 *         description: PTZ 위치 설정 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/setPosition', async (req, res) => {
  try {
    const { ip, pan, tilt, zoom, presetNumber } = req.body;

    if (!ip || pan === undefined || tilt === undefined || zoom === undefined || !presetNumber) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: ip, pan, tilt, zoom, presetNumber'
      });
    }

    // 프리셋 번호 유효성 검사
    if (presetNumber < 1 || presetNumber > 3) {
      return res.status(400).json({
        success: false,
        message: '프리셋 번호는 1-3 사이여야 합니다'
      });
    }


    log.info(`[웹 API] PTZ 위치 설정: ${ip}:80, Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}, Preset=${presetNumber}`);

    // 웹 API 호출: http://IP:80/api/ptz.cgi?PTZNumber={presetNumber}&GotoAbsolutePosition=Pan,Tilt,Zoom
    const apiUrl = `http://${ip}:80/api/ptz.cgi?PTZNumber=${presetNumber}&GotoAbsolutePosition=${pan},${tilt},${zoom}`;

    // Digest 인증을 사용한 요청
    const response = await makeDigestRequest(apiUrl, 'root', 'cctv1350!!', {
      timeout: 10000
    });

    const responseText = response.data;
    log.info(`[웹 API] 응답: ${responseText}`);

    // ptz_info.ini에 해당 프리셋으로 저장
    try {
      const fs = await import('fs');
      const path = await import('path');

      const binDir = path.resolve(process.cwd(), 'bin');
      const ptzInfoPath = path.join(binDir, 'ptz_info.ini');
      let iniContent = '';

      // bin 디렉토리가 없으면 생성
      if (!fs.existsSync(binDir)) {
        fs.mkdirSync(binDir, { recursive: true });
      }

      // 기존 INI 파일이 있으면 읽기
      if (fs.existsSync(ptzInfoPath)) {
        try {
          iniContent = fs.readFileSync(ptzInfoPath, 'utf-8');
        } catch (readError) {
          log.warn(`[INI 파일 읽기 오류] 파일 읽기 실패, 새로 생성:`, readError);
          iniContent = '';
        }
      }

      // 해당 프리셋 정보 추가/업데이트
      const sectionName = `PRESET_${presetNumber}`;
      const timestamp = new Date().toISOString();
      const client = req.ip || 'unknown';

      const presetData = `[${sectionName}]
pan=${pan}
tilt=${tilt}
zoom=${zoom}
focus=0
timestamp=${timestamp}
client=${client}

`;

      // 기존 1번 프리셋 섹션이 있으면 제거
      const sectionRegex = new RegExp(`\\[${sectionName}\\][\\s\\S]*?(?=\\n\\[|$)`, 'g');
      iniContent = iniContent.replace(sectionRegex, '');

      // 새 1번 프리셋 정보 추가
      iniContent += presetData;

      // INI 파일 저장
      fs.writeFileSync(ptzInfoPath, iniContent);
      log.info(`[웹 API] 1번 프리셋 정보 저장 완료: ${ptzInfoPath}`);

    } catch (fileError) {
      log.error(`[웹 API] INI 파일 저장 오류:`, fileError);
    }

    res.json({
      success: true,
      message: 'PTZ 위치 설정 성공',
      data: {
        ip,
        port: 80,
        ptzValues: {
          pan,
          tilt,
          zoom
        },
        rawResponse: responseText
      }
    });

  } catch (error) {
    log.error('[웹 API] PTZ 위치 설정 오류:', error);
    res.status(500).json({
      success: false,
      message: 'PTZ 위치 설정 실패',
      error: error.message
    });
  }
});

// =========================
// PNT 프리셋 및 투어 API
// =========================





/**
 * @swagger
 * /api/ptz/home:
 *   post:
 *     tags: [PTZ Control]
 *     summary: 홈프리셋 이동 (1번 프리셋)
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - ip
 *             properties:
 *               ip:
 *                 type: string
 *                 description: 카메라 IP 주소
 *     responses:
 *       200:
 *         description: 홈프리셋 이동 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.post('/ptz/home', async (req, res) => {
  try {
    const { ip } = req.body;

    if (!ip) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: ip'
      });
    }

    log.info(`[웹 API] 홈프리셋 이동: ${ip}:80`);

    // ptz_info.ini에서 1번 프리셋 값 읽기
    try {
      const fs = await import('fs');
      const path = await import('path');

      const binDir = path.resolve(process.cwd(), 'bin');
      const ptzInfoPath = path.join(binDir, 'ptz_info.ini');

      if (!fs.existsSync(ptzInfoPath)) {
        return res.status(404).json({
          success: false,
          message: '프리셋 파일이 없습니다'
        });
      }

      const iniContent = fs.readFileSync(ptzInfoPath, 'utf-8');
      const sectionName = 'PRESET_1';

      // 1번 프리셋 섹션 찾기
      const sectionRegex = new RegExp(`\\[${sectionName}\\][\\s\\S]*?(?=\\n\\[|$)`, 'g');
      const match = sectionRegex.exec(iniContent);

      if (!match) {
        return res.status(404).json({
          success: false,
          message: '1번 프리셋을 찾을 수 없습니다'
        });
      }

      const sectionContent = match[0];

      // Pan, Tilt, Zoom 값 추출
      const panMatch = sectionContent.match(/pan=([^\n\r]+)/);
      const tiltMatch = sectionContent.match(/tilt=([^\n\r]+)/);
      const zoomMatch = sectionContent.match(/zoom=([^\n\r]+)/);

      if (!panMatch || !tiltMatch || !zoomMatch) {
        return res.status(400).json({
          success: false,
          message: '1번 프리셋 데이터 형식이 올바르지 않습니다'
        });
      }

      const pan = parseFloat(panMatch[1]);
      const tilt = parseFloat(tiltMatch[1]);
      const zoom = parseFloat(zoomMatch[1]);

      log.info(`[웹 API] 1번 프리셋 데이터: Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}`);

      // PTZ 위치 설정 (setPosition API 호출)
      const setPositionUrl = `http://${ip}:80/api/ptz.cgi?PTZNumber=1&GotoAbsolutePosition=${pan},${tilt},${zoom}`;
      const response = await makeDigestRequest(setPositionUrl, 'root', 'cctv1350!!', {
        timeout: 10000
      });

      const responseText = response.data;
      log.info(`[웹 API] 홈프리셋 이동 응답: ${responseText}`);

      res.json({
        success: true,
        message: '홈프리셋 이동 성공',
        data: {
          ip,
          port: 80,
          ptzValues: { pan, tilt, zoom },
          rawResponse: responseText
        }
      });

    } catch (fileError) {
      log.error('[웹 API] 홈프리셋 이동 오류:', fileError);
      res.status(500).json({
        success: false,
        message: '홈프리셋 이동 실패',
        error: fileError.message
      });
    }

  } catch (error) {
    log.error('[웹 API] 홈프리셋 이동 오류:', error);
    res.status(500).json({
      success: false,
      message: '홈프리셋 이동 실패',
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
    const { ip } = req.body;
    const port = 33000; // PNT 서버 포트 고정

    if (!ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: ip, port'
      });
    }

    log.info(`PNT Tour Start: target: ${ip}:${port}`);

    const packet = createPNTPacket(PNT_PID.TOUR, [1]);
    log.info(`PNT Tour Start packet: ${packet.toString('hex')}`);

    const response = await sendTCPPacket(ip, port, packet);

    if (response.success) {
      res.json({
        success: true,
        message: '투어 시작 완료',
        data: {
          ip,
          port,
          packet: packet.toString('hex'),
          serverResponse: response.message
        }
      });
    } else {
      res.status(400).json({
        success: false,
        message: `투어 시작 실패: ${response.message}`,
        data: {
          ip,
          port,
          packet: packet.toString('hex'),
          serverResponse: response.message
        }
      });
    }

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
    const { ip } = req.body;
    const port = 33000; // PNT 서버 포트 고정

    if (!ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: ip, port'
      });
    }

    log.info(`PNT Tour Stop: target: ${ip}:${port}`);

    const packet = createPNTPacket(PNT_PID.TOUR, [0]);
    log.info(`PNT Tour Stop packet: ${packet.toString('hex')}`);

    const response = await sendTCPPacket(ip, port, packet);

    if (response.success) {
      res.json({
        success: true,
        message: '투어 정지 완료',
        data: {
          ip,
          port,
          packet: packet.toString('hex'),
          serverResponse: response.message
        }
      });
    } else {
      res.status(400).json({
        success: false,
        message: `투어 정지 실패: ${response.message}`,
        data: {
          ip,
          port,
          packet: packet.toString('hex'),
          serverResponse: response.message
        }
      });
    }

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
 *                 maximum: 99
 *                 description: 프리셋 번호 (1-99)
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
    const { presetNumber, speedRpm, delaySec, ip } = req.body;
    const port = 33000; // PNT 서버 포트 고정

    if (!presetNumber || !speedRpm || !delaySec || !ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: presetNumber, speedRpm, delaySec, ip, port'
      });
    }

    if (presetNumber < 1 || presetNumber > 99) {
      return res.status(400).json({
        success: false,
        message: '프리셋 번호는 1-99 사이여야 합니다'
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

    const response = await sendTCPPacket(ip, port, packet);

    if (response.success) {
      res.json({
        success: true,
        message: `투어 스텝 설정 완료 (Preset ${presetNumber})`,
        data: {
          presetNumber,
          speedRpm,
          delaySec: delay,
          ip,
          port,
          packet: packet.toString('hex'),
          serverResponse: response.message
        }
      });
    } else {
      res.status(400).json({
        success: false,
        message: `투어 스텝 설정 실패: ${response.message}`,
        data: {
          presetNumber,
          speedRpm,
          delaySec: delay,
          ip,
          port,
          packet: packet.toString('hex'),
          serverResponse: response.message
        }
      });
    }

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
    const { speedRpm, delaySec, ip } = req.body;
    const port = 33000; // PNT 서버 포트 고정

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

/**
 * @swagger
 * /api/ptz/status:
 *   get:
 *     tags: [PTZ Control]
 *     summary: PNT 서버 연결 상태 확인
 *     parameters:
 *       - in: query
 *         name: ip
 *         required: true
 *         schema:
 *           type: string
 *         description: 카메라 IP 주소
 *       - in: query
 *         name: port
 *         required: true
 *         schema:
 *           type: number
 *         description: 카메라 포트
 *     responses:
 *       200:
 *         description: 연결 상태 확인 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.get('/ptz/status', async (req, res) => {
  const startTime = Date.now();
  try {
    const { ip, port } = req.query;

    if (!ip || !port) {
      log.warn(`[PNT 상태 확인] 필수 파라미터 누락: ip=${ip}, port=${port}`);
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: ip, port'
      });
    }

    log.info(`[PNT 상태 확인] 서버 연결 테스트 시작: ${ip}:${port}`);

    // 간단한 연결 테스트 패킷 (프리셋 호출 0번 - 존재하지 않는 프리셋)
    const packet = createPNTPacket(PNT_PID.PRESET_RECALL, [0]);
    log.info(`[PNT 상태 확인] 테스트 패킷: ${packet.toString('hex')}`);

    const response = await sendTCPPacket(ip, port, packet);
    const totalTime = Date.now() - startTime;

    log.info(`[PNT 상태 확인] 응답 수신: ${JSON.stringify(response)}, 소요 시간: ${totalTime}ms`);

    res.json({
      success: true,
      message: 'PNT 서버 연결 상태 확인 완료',
      data: {
        ip,
        port,
        connected: response.success,
        serverResponse: response.message,
        packet: packet.toString('hex'),
        responseTime: totalTime
      }
    });

  } catch (error) {
    const totalTime = Date.now() - startTime;
    log.error(`[PNT 상태 확인] 연결 실패: ${error.message}, 소요 시간: ${totalTime}ms`);
    log.error(`[PNT 상태 확인] 오류 상세:`, error.stack);

    res.status(500).json({
      success: false,
      message: 'PNT 서버 연결 실패',
      data: {
        ip: req.query.ip,
        port: 33000,
        connected: false,
        error: error.message,
        responseTime: totalTime
      }
    });
  }
});

/**
 * @swagger
 * /api/ptz/preset/list:
 *   get:
 *     tags: [PTZ Control]
 *     summary: PNT 프리셋 목록 조회
 *     parameters:
 *       - in: query
 *         name: ip
 *         required: true
 *         schema:
 *           type: string
 *         description: 카메라 IP 주소
 *       - in: query
 *         name: port
 *         required: true
 *         schema:
 *           type: number
 *         description: 카메라 포트
 *     responses:
 *       200:
 *         description: 프리셋 목록 조회 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.get('/ptz/preset/list', async (req, res) => {
  try {
    const { ip } = req.query;
    const port = 33000; // PNT 서버 포트 고정

    if (!ip) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: ip'
      });
    }

    log.info(`PNT Preset List: target: ${ip}:${port}`);

    // PNT 서버에서 프리셋 목록을 조회하는 직접적인 방법이 없으므로
    // INI 파일을 직접 읽어서 프리셋 정보를 반환
    const fs = await import('fs');
    const path = await import('path');

    try {
      const binDir = path.join(process.cwd(), 'bin');
      const ptzInfoPath = path.join(binDir, 'ptz_info.ini');

      // bin 디렉토리가 없으면 생성
      if (!fs.existsSync(binDir)) {
        fs.mkdirSync(binDir, { recursive: true });
        log.info(`bin 디렉토리가 생성되었습니다: ${binDir}`);
      }

      if (!fs.existsSync(ptzInfoPath)) {
        return res.json({
          success: true,
          message: '프리셋 파일이 없습니다',
          data: {
            presets: [],
            count: 0
          }
        });
      }

      const iniContent = fs.readFileSync(ptzInfoPath, 'utf-8');
      const presets = [];

      // INI 파일에서 프리셋 정보 추출
      const presetRegex = /\[PRESET_(\d+)\][\s\S]*?pan=([^\n\r]+)[\s\S]*?tilt=([^\n\r]+)[\s\S]*?zoom=([^\n\r]+)[\s\S]*?focus=([^\n\r]+)[\s\S]*?timestamp=([^\n\r]+)[\s\S]*?client=([^\n\r]+)/g;
      let match;

      while ((match = presetRegex.exec(iniContent)) !== null) {
        const presetNum = parseInt(match[1]);
        const pan = parseFloat(match[2]) || 0;
        const tilt = parseFloat(match[3]) || 0;
        const zoom = parseFloat(match[4]) || 0;
        const focus = parseFloat(match[5]) || 0;
        const timestamp = match[6] || '';
        const client = match[7] || '';

        presets.push({
          presetNumber: presetNum,
          pan,
          tilt,
          zoom,
          focus,
          timestamp,
          client
        });
      }

      // 프리셋 번호순으로 정렬
      presets.sort((a, b) => a.presetNumber - b.presetNumber);

      res.json({
        success: true,
        message: `프리셋 목록 조회 완료 (${presets.length}개)`,
        data: {
          presets,
          count: presets.length
        }
      });

    } catch (fileError) {
      log.error('INI 파일 읽기 오류:', fileError);
      res.status(500).json({
        success: false,
        message: '프리셋 파일 읽기 실패',
        error: fileError.message
      });
    }

  } catch (error) {
    log.error('PNT Preset List Error:', error);
    res.status(500).json({
      success: false,
      message: '프리셋 목록 조회 실패',
      error: error.message
    });
  }
});

/**
 * @swagger
 * /api/ptz/preset/delete:
 *   delete:
 *     tags: [PTZ Control]
 *     summary: PNT 프리셋 삭제
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
 *                 maximum: 99
 *                 description: 프리셋 번호 (1-99)
 *               ip:
 *                 type: string
 *                 description: 카메라 IP 주소
 *               port:
 *                 type: number
 *                 description: 카메라 포트
 *     responses:
 *       200:
 *         description: 프리셋 삭제 성공
 *       400:
 *         description: 잘못된 요청 파라미터
 *       500:
 *         description: 서버 내부 오류
 */
router.delete('/ptz/preset/delete', async (req, res) => {
  try {
    const { presetNumber, ip } = req.body;
    const port = 33000; // PNT 서버 포트 고정

    if (!presetNumber || !ip || !port) {
      return res.status(400).json({
        success: false,
        message: '필수 파라미터가 누락되었습니다: presetNumber, ip, port'
      });
    }

    if (presetNumber < 1 || presetNumber > 99) {
      return res.status(400).json({
        success: false,
        message: '프리셋 번호는 1-99 사이여야 합니다'
      });
    }

    log.info(`PNT Preset Delete: ${presetNumber}, target: ${ip}:${port}`);

    // INI 파일에서 프리셋 삭제
    const fs = await import('fs');
    const path = await import('path');

    try {
      const binDir = path.join(process.cwd(), 'bin');
      const ptzInfoPath = path.join(binDir, 'ptz_info.ini');

      // bin 디렉토리가 없으면 생성
      if (!fs.existsSync(binDir)) {
        fs.mkdirSync(binDir, { recursive: true });
        log.info(`bin 디렉토리가 생성되었습니다: ${binDir}`);
      }

      if (!fs.existsSync(ptzInfoPath)) {
        return res.status(404).json({
          success: false,
          message: '프리셋 파일이 없습니다'
        });
      }

      let iniContent = fs.readFileSync(ptzInfoPath, 'utf-8');
      const sectionName = `PRESET_${presetNumber}`;

      // 프리셋 섹션 찾기
      const sectionRegex = new RegExp(`\\[${sectionName}\\][\\s\\S]*?(?=\\n\\[|$)`, 'g');
      const match = sectionRegex.exec(iniContent);

      if (match) {
        // 프리셋 섹션 제거
        iniContent = iniContent.replace(sectionRegex, '');

        // INI 파일 다시 저장
        fs.writeFileSync(ptzInfoPath, iniContent);

        res.json({
          success: true,
          message: `프리셋 ${presetNumber} 삭제 완료`,
          data: {
            presetNumber,
            ip,
            port
          }
        });
      } else {
        res.status(404).json({
          success: false,
          message: `프리셋 ${presetNumber}을 찾을 수 없습니다`
        });
      }

    } catch (fileError) {
      log.error('INI 파일 처리 오류:', fileError);
      res.status(500).json({
        success: false,
        message: '프리셋 삭제 실패',
        error: fileError.message
      });
    }

  } catch (error) {
    log.error('PNT Preset Delete Error:', error);
    res.status(500).json({
      success: false,
      message: '프리셋 삭제 실패',
      error: error.message
    });
  }
});

export default router;

