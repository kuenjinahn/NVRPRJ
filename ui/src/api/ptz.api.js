import api from './index';

const resource = '/ptz';

// PTZ 이동 제어
export const ptzMove = (direction, speed, ip, port) =>
  api.post(`${resource}/move`, { direction, speed, ip, port });

// PTZ 정지
export const ptzStop = (ip, port) =>
  api.post(`${resource}/stop`, { ip, port });

// PTZ 줌 제어
export const ptzZoom = (direction, ip, port) =>
  api.post(`${resource}/zoom`, { direction, ip, port });

// PTZ 포커스 제어
export const ptzFocus = (direction, ip, port) =>
  api.post(`${resource}/focus`, { direction, ip, port });

// PTZ 와이퍼 제어
export const ptzWiper = (action, ip, port) =>
  api.post(`${resource}/wiper`, { action, ip, port });

// =========================
// PNT 프리셋 및 투어 API
// =========================

// PNT 프리셋 저장
export const pntPresetSave = (presetNumber, ip, port) =>
  api.post(`${resource}/preset/save`, { presetNumber, ip, port });

// PNT 프리셋 호출
export const pntPresetRecall = (presetNumber, ip, port) =>
  api.post(`${resource}/preset/recall`, { presetNumber, ip, port });

// PNT 투어 시작
export const pntTourStart = (ip, port) =>
  api.post(`${resource}/tour/start`, { ip, port });

// PNT 투어 정지
export const pntTourStop = (ip, port) =>
  api.post(`${resource}/tour/stop`, { ip, port });

// PNT 투어 스텝 설정
export const pntTourStep = (presetNumber, speedRpm, delaySec, ip, port) =>
  api.post(`${resource}/tour/step`, { presetNumber, speedRpm, delaySec, ip, port });

// PNT 투어 전체 설정 (1-3 스텝)
export const pntTourSetup = (speedRpm, delaySec, ip, port) =>
  api.post(`${resource}/tour/setup`, { speedRpm, delaySec, ip, port });

