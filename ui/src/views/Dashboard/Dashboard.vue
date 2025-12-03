<template lang="pug">
.dashboard-2by2
  .cell.cell-topleft
    .topleft-inner-row
      .topleft-inner-left
        .time-layer
          .current-time {{ currentTime }}
        .site-info-layer
          .layer-title 실증현장 정보
          .site-info-content
            .site-name(v-if="location_info") {{ location_info }}
        .dam-data-layer
          .layer-title 실시간 댐 데이터
          .dam-data-content
            .dam-data-item
              .dam-data-label 댐 수위
              .dam-data-value {{ damData.rwl != null ? damData.rwl : '-' }}
            .dam-data-item
              .dam-data-label 우량
              .dam-data-value {{ damData.dambasrf != null ? damData.dambasrf : '-' }}
            .dam-data-item
              .dam-data-label 방류량
              .dam-data-value {{ damData.dqty != null ? damData.dqty : '-' }}
        .leak-status-layer
          .layer-title 실시간누수감지상태
          .status-buttons
            .status-button.safe(
              :class="{ active: selectedStatusButton === 'safe' }"
            )
              .status-icon ✅
              .status-text 안전
            .status-button.attention(
              :class="{ active: selectedStatusButton === 'attention' }"
            )
              .status-icon 🛡️
              .status-text 관심
            .status-button.caution(
              :class="{ active: selectedStatusButton === 'caution' }"
            )
              .status-icon ⚠️
              .status-text 주의
            .status-button.check(
              :class="{ active: selectedStatusButton === 'check' }"
            )
              .status-icon 🔍
              .status-text 점검
            .status-button.prepare(
              :class="{ active: selectedStatusButton === 'prepare' }"
            )
              .status-icon 🔔
              .status-text 대비
      .topleft-inner-right
        .map-image-container(v-if="mapImagePreview")
          v-img(
            :src="mapImagePreview"
            height="100%"
            width="100%"
            cover
            class="map-preview-image"
          )
        .no-map-image(v-else)
          .no-map-text 지도 이미지가 없습니다
  .cell.cell-topright
    .box-title
      span 열화상 영상
      v-btn(
        color="secondary"
        size="small"
        @click="showPanorama"
      ) 파노라마
    .video-container
      vue-aspect-ratio(ar="4:3")
        VideoCard(
          v-if="thermalCamera"
          :key="videoKeyThermal"
          :ref="thermalCamera.name"
          :camera="thermalCamera"
          title
          title-position="bottom"
          :stream="thermalCamera.live"
          @cameraStatus="cameraStatus"
        )
        .no-camera(v-else) No thermal camera available

  // 파노라마 슬라이더 팝업 다이얼로그
  v-dialog(
    v-model="panoramaDialog"
    max-width="1400"
    persistent
    content-class="panorama-dialog"
  )
    v-card.panorama-dialog-card
      v-card-title.headline
        span 파노라마 이미지
        v-spacer
        v-btn.close-btn(
          color="secondary"
          @click="panoramaDialog = false"
        ) X
      
      v-card-text
        .panorama-container
          .panorama-image-container
            v-img(
              v-if="currentPanoramaImage"
              :src="currentPanoramaImage"
              height="500"
              width="100%"
              contain
              class="panorama-image"
            )
            .no-image(v-else)
              .no-image-text 이미지가 없습니다
          
          .panorama-controls
            v-btn(
              :disabled="currentPanoramaIndex <= 0"
              @click="previousPanorama"
              color="primary"
              outlined
            )
              v-icon mdi-chevron-left
              | 이전
            .panorama-info
              span {{ currentPanoramaIndex + 1 }} / {{ panoramaDataList.length }}
              .panorama-date(v-if="currentPanoramaData")
                | {{ formatPanoramaDate(currentPanoramaData.create_date) }}
            v-btn(
              :disabled="currentPanoramaIndex >= panoramaDataList.length - 1"
              @click="nextPanorama"
              color="primary"
              outlined
            )
              | 다음
              v-icon mdi-chevron-right

  // PTZ 제어 팝업 다이얼로그
  v-dialog(
    v-model="ptzDialog"
    max-width="1200"
    persistent
    content-class="ptz-dialog"
  )
    v-card.ptz-dialog-card(
      ref="ptzDialogCard"
      @mousedown="startDrag"
    )
      v-card-title.headline.draggable-header(
        @mousedown="startDrag"
      )
        span PTZ 카메라 제어
        v-spacer
        v-btn.close-btn(
          color="white"
          @click="ptzDialog = false"
        ) X
      
      v-card-text
        .ptz-dialog-container
          // 왼쪽 영역 - 기존 PTZ 제어
          .ptz-left-panel
            .ptz-control-container
              // 연결 정보
              .connection-info
                v-row
                  v-col(cols="8")
                    v-text-field(
                      v-model="ptzConfig.ip"
                      label="카메라 IP"
                      outlined
                      dense
                      :error-messages="ipError"
                      @input="validateIP"
                    )
                  v-col(cols="4")
                    v-text-field(
                      v-model="ptzConfig.speed"
                      label="속도 (1-63)"
                      outlined
                      dense
                      type="number"
                      min="1"
                      max="63"
                    )
                
                // 연결 상태 표시
                .connection-status(v-if="connectionStatus")
                  v-alert(
                    :type="connectionStatus.type"
                    :text="connectionStatus.message"
                    dense
                    outlined
                  )
              
              // PTZ 제어 버튼
              .ptz-buttons
                .ptz-row
                  v-btn(
                    fab
                    large
                    color="secondary"
                    @mousedown="ptzMove('up')"
                    @mouseup="ptzStop"
                    @mouseleave="ptzStop"
                  )
                    v-icon(:icon="ptzIcons.up")
                    .ptz-label 상
                .ptz-row
                  v-btn(
                    fab
                    large
                    color="secondary"
                    @mousedown="ptzMove('left')"
                    @mouseup="ptzStop"
                    @mouseleave="ptzStop"
                  )
                    v-icon(:icon="ptzIcons.left")
                    .ptz-label 좌
                  v-btn(
                    fab
                    large
                    color="secondary"
                    @mousedown="ptzMove('right')"
                    @mouseup="ptzStop"
                    @mouseleave="ptzStop"
                  )
                    v-icon(:icon="ptzIcons.right")
                    .ptz-label 우
                .ptz-row
                  v-btn(
                    fab
                    large
                    color="secondary"
                    @mousedown="ptzMove('down')"
                    @mouseup="ptzStop"
                    @mouseleave="ptzStop"
                  )
                    v-icon(:icon="ptzIcons.down")
                    .ptz-label 하
              
              // 줌 및 포커스 제어
              .zoom-focus-controls
                v-row
                  v-col(cols="6")
                    .control-group
                      .control-label 줌 제어
                      .control-buttons
                        v-btn(
                          color="secondary"
                          @mousedown="ptzZoom('in')"
                          @mouseup="ptzStop"
                          @mouseleave="ptzStop"
                        )
                          v-icon(:icon="ptzIcons.zoomIn" size="small")
                          span.ml-2 줌 인
                        v-btn(
                          color="secondary"
                          @mousedown="ptzZoom('out')"
                          @mouseup="ptzStop"
                          @mouseleave="ptzStop"
                        )
                          v-icon(:icon="ptzIcons.zoomOut" size="small")
                          span.ml-2 줌 아웃
                  v-col(cols="6")
                    .control-group
                      .control-label 포커스 제어
                      .control-buttons
                        v-btn(
                          color="secondary"
                          @mousedown="ptzFocus('in')"
                          @mouseup="ptzStop"
                          @mouseleave="ptzStop"
                        )
                          v-icon(:icon="ptzIcons.focusIn" size="small")
                          span.ml-2 포커스 인
                        v-btn(
                          color="secondary"
                          @mousedown="ptzFocus('out')"
                          @mouseup="ptzStop"
                          @mouseleave="ptzStop"
                        )
                          v-icon(:icon="ptzIcons.focusOut" size="small")
                          span.ml-2 포커스 아웃
              
              // 와이퍼 제어
              .wiper-controls
                .control-group
                  .control-label 와이퍼 제어
                  .control-buttons
                    v-btn(
                      color="success"
                      @click="ptzWiper('on')"
                    )
                      v-icon(:icon="ptzIcons.wiperOn" size="small")
                      span.ml-2 와이퍼 ON
                    v-btn(
                      color="error"
                      @click="ptzWiper('off')"
                    )
                      v-icon(:icon="ptzIcons.wiperOff" size="small")
                      span.ml-2 와이퍼 OFF

          // 오른쪽 영역 - 프리셋 및 투어 제어
          .ptz-right-panel
            .preset-section
              .section-title 프리셋
              .preset-controls
                .preset-row
                  .preset-label Preset1
                  .preset-inputs
                    v-text-field(
                      v-model="presetValues.preset1.pan"
                      label="Pan"
                      outlined
                      dense
                      hide-details
                    )
                    v-text-field(
                      v-model="presetValues.preset1.tilt"
                      label="Tilt"
                      outlined
                      dense
                      hide-details
                    )
                    v-text-field(
                      v-model="presetValues.preset1.zoom"
                      label="Zoom"
                      outlined
                      dense
                      hide-details
                    )
                  .preset-buttons
                    v-btn(
                      color="secondary"
                      small
                      @click="loadPreset1"
                    ) 불러오기
                    v-btn(
                      color="success"
                      small
                      @click="savePreset1"
                    ) 저장하기
                
                .preset-row
                  .preset-label Preset2
                  .preset-inputs
                    v-text-field(
                      v-model="presetValues.preset2.pan"
                      label="Pan"
                      outlined
                      dense
                      hide-details
                    )
                    v-text-field(
                      v-model="presetValues.preset2.tilt"
                      label="Tilt"
                      outlined
                      dense
                      hide-details
                    )
                    v-text-field(
                      v-model="presetValues.preset2.zoom"
                      label="Zoom"
                      outlined
                      dense
                      hide-details
                    )
                  .preset-buttons
                    v-btn(
                      color="secondary"
                      small
                      @click="loadPreset2"
                    ) 불러오기
                    v-btn(
                      color="success"
                      small
                      @click="savePreset2"
                    ) 저장하기
                
                .preset-row
                  .preset-label Preset3
                  .preset-inputs
                    v-text-field(
                      v-model="presetValues.preset3.pan"
                      label="Pan"
                      outlined
                      dense
                      hide-details
                    )
                    v-text-field(
                      v-model="presetValues.preset3.tilt"
                      label="Tilt"
                      outlined
                      dense
                      hide-details
                    )
                    v-text-field(
                      v-model="presetValues.preset3.zoom"
                      label="Zoom"
                      outlined
                      dense
                      hide-details
                    )
                  .preset-buttons
                    v-btn(
                      color="secondary"
                      small
                      @click="loadPreset3"
                    ) 불러오기
                    v-btn(
                      color="success"
                      small
                      @click="savePreset3"
                    ) 저장하기

            // 홈 프리셋으로 이동 버튼
            .home-preset-section
              .section-title 홈 프리셋
              .home-preset-controls
                v-btn(
                  color="success"
                  large
                  @click="goToHomePreset"
                  :disabled="!connected"
                )
                  v-icon(left)
                  | 홈 프리셋으로 이동

            .tour-section
              .section-title 장치 투어(1→2→3) & 시간
              .tour-controls
                .tour-speed
                  v-text-field(
                    v-model="tourSpeed"
                    label="투어 속도(rpm)"
                    outlined
                    dense
                    type="number"
                    hide-details
                  )
                .step-write
                  v-text-field(
                    v-model="stepWrite"
                    label="스텝 쓰기(1~3)"
                    outlined
                    dense
                    type="number"
                    min="1"
                    max="3"
                    hide-details
                  )
                  v-btn(
                    color="success"
                    small
                    @click="writeTourSteps"
                    :disabled="!connected"
                  ) 스텝 쓰기


            .log-section
              .section-title 로그
              .log-area(ref="logArea")
                v-textarea(
                  v-model="logContent"
                  readonly
                  outlined
                  no-resize
                  hide-details
                  rows="5"
                )

  .cell.cell-bottomleft
    .bottomleft-inner-col
      .bottomleft-inner-top
        .box-title 분석영역리스트
        .table-container
          table.zone-table
            thead
              tr
                th ROI
                th 최대온도
                th 최소온도
                th 평균온도
                th 그래프
                th 다운로드
            tbody
              tr(
                v-for="(zone, idx) in zones"
                :key="`zone-${idx}-${zone.zone_desc}`"
                :class="{selected: selectedZoneIdx === idx, clicking: clickingZoneIdx === idx}"
                @click="showChart(zone, idx)"
              )
                td {{ zone.zone_desc }}
                td {{ getMaxTemp(zone) }}
                td {{ getMinTemp(zone) }}
                td {{ zone.avgTemp && zone.avgTemp !== '--' ? (typeof zone.avgTemp === 'string' ? zone.avgTemp : zone.avgTemp.toFixed(1)) : '--' }}
                td
                  span.icon-chart 📈
                td
                  span.icon-excel(@click.stop.prevent="downloadExcel(zone)") 📊
      .bottomleft-inner-bottom
          .box-title.chart-title 시계열 온도 데이터
          .chart-container
            v-chart(:options="chartOption" autoresize ref="trendChart" class="trend-chart")
  .cell.cell-bottomright
    .box-title
      span 실화상 영상
      v-btn(
        color="secondary"
        size="small"
        @click="showPTZControl"
      ) 팬틸트
    .video-container
      vue-aspect-ratio(ar="4:3")
        VideoCard(
          v-if="visibleCamera"
          :key="videoKeyVisible"
          :ref="visibleCamera.name"
          :camera="visibleCamera"
          title
          title-position="bottom"
          :stream="visibleCamera.live"
          @cameraStatus="cameraStatus"
        )
        .no-camera(v-else) No visible camera available

  // 경보 알림 팝업 레이어 (화면 가운데)
  .alert-popup-container(v-if="showAlertPopup && unclosedAlerts.length > 0")
    .alert-popup-header
      .alert-popup-title 경보 알림
      v-btn.close-popup-btn(
        icon
        small
        @click="closeAlertPopup"
      )
        v-icon(:icon="ptzIcons.close")
    .alert-popup-content
      .alert-list
        .alert-item(v-for="alert in unclosedAlerts" :key="alert.id")
          .alert-level 경보단계: {{ alert.levelText }}
          .alert-zone 경보영역: {{ alert.zoneName }}
          .alert-time 경보시간: {{ alert.time }}
    .alert-popup-footer
      v-btn(
        color="secondary"
        block
        @click="closeAlertPopup"
      ) 닫기
</template>
  
<script>
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { BarChart, LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import VideoCard from '@/components/camera-card.vue';
import { getCameras, getCameraSettings } from '@/api/cameras.api';
import { getRoiDataList, getRoiTemperatureTimeSeries } from '@/api/statistic.api';
import VChart from 'vue-echarts';
import VueAspectRatio from 'vue-aspect-ratio';
import socket from '@/mixins/socket';
import * as XLSX from 'xlsx';
import * as echarts from 'echarts';
import { getAlerts, updatePopupClose, getAlertSettings} from '@/api/alerts.api';
import { getEventSetting } from '@/api/eventSetting.api.js';
import { ptzMove, ptzStop, ptzZoom, ptzFocus, ptzWiper, pntTourStart, pntTourStop, pntTourSetup } from '@/api/ptz.api';
import { getPanoramaData } from '@/api/panorama.api';

// 새로운 웹 API 함수들
const getPTZPosition = async (ip, ptzNumber = 1) => {
  const response = await fetch(`/api/ptz/getPosition?ip=${ip}&ptzNumber=${ptzNumber}`);
  return await response.json();
};

const setPTZPosition = async (ip, pan, tilt, zoom, presetNumber = 1) => {
  const response = await fetch('/api/ptz/setPosition', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ip, pan, tilt, zoom, presetNumber })
  });
  return await response.json();
};

// 프리셋 목록 조회 API 함수
const getPresetList = async (ip) => {
  const response = await fetch(`/api/ptz/preset/list?ip=${ip}`);
  return await response.json();
};





// PTZ 아이콘 import
import { 
  mdiChevronUp, 
  mdiChevronDown, 
  mdiChevronLeft, 
  mdiChevronRight,
  mdiMagnifyPlus,
  mdiMagnifyMinus,
  mdiFocus,
  mdiFocusOutline,
  mdiWater,
  mdiWaterOff,
  mdiClose,
  mdiHome
} from '@mdi/js';
use([
  CanvasRenderer,
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent
]);

export default {
name: 'Dashboard',
  components: {
    VideoCard,
    'v-chart': VChart,
    'vue-aspect-ratio': VueAspectRatio
  },
  mixins: [socket],
data() {
  return {
    cameraList: [],
    thermalCamera: null,
    visibleCamera: null,
    videoKeyThermal: '',
    videoKeyVisible: '',
    camStates: [],
    currentTime: '',
    weather: {
      temperature: '--',
      description: '날씨 정보 로딩 중...',
      location: '서울'
    },
    timeInterval: null,
    alertHistoryInterval: null, // 실시간 누수감지상태 정보 갱신용 인터벌
    damDataInterval: null, // 실시간 댐 데이터 갱신용 인터벌
    showChartInterval: null, // 차트 자동 갱신용 인터벌 (1분마다)
    visibleCameraReloadInterval: null, // 실화상 영상 리로드용 인터벌 (1시간마다)
    zones: [],
    selectedZoneIdx: null,
    selectedZone: null,
    loading: true,
    socketConnected: false,
    alertHistory: [],
    gaugeChart: null,
    location_info: '',
    address: '',
    mapImagePreview: null,
    selectedStatusButton: 'safe', // 초기값을 안전으로 설정
    damData: {
      rwl: null,
      dambasrf: null,
      dqty: null
    },
    latestAlertInfo: null,
    showAlertPopup: false,
    unclosedAlerts: [],
    popupNotificationEnabled: true, // 팝업 알림 설정 (기본값: true)
    // PTZ 제어 관련 데이터
    ptzDialog: false,
    ptzConfig: {
      ip: '175.201.204.165',
      port: '80',
      speed: 32
    },
    // IP 유효성 검사 관련 데이터
    ipError: '',
    connectionStatus: null,
    // PTZ 아이콘
    ptzIcons: {
      up: mdiChevronUp,
      down: mdiChevronDown,
      left: mdiChevronLeft,
      right: mdiChevronRight,
      zoomIn: mdiMagnifyPlus,
      zoomOut: mdiMagnifyMinus,
      focusIn: mdiFocus,
      focusOut: mdiFocusOutline,
      wiperOn: mdiWater,
      wiperOff: mdiWaterOff,
      close: mdiClose,
      home: mdiHome
    },
    // 프리셋 값들
    presetValues: {
      preset1: { pan: '', tilt: '', zoom: '' },
      preset2: { pan: '', tilt: '', zoom: '' },
      preset3: { pan: '', tilt: '', zoom: '' }
    },
    // 투어 관련 데이터
    tourSpeed: 600,
    stepWrite: '',
    cycleProgress: 0,
    logContent: '',
    tourRunning: false,
    tourStatus: '대기 중',
    connected: false,
    // 드래그 관련 데이터
    isDragging: false,
    dragStartX: 0,
    dragStartY: 0,
    dialogOffsetX: 0,
    dialogOffsetY: 0,
    // 파노라마 관련 데이터
    panoramaDialog: false,
    panoramaDataList: [],
    currentPanoramaIndex: 0,
    currentPanoramaImage: null,
    currentPanoramaData: null,
    // 클릭 효과를 위한 데이터
    clickingZoneIdx: null
  };
},
computed: {

  chartOption() {
    console.log('=== chartOption Debug ===');
    console.log('selectedZone:', this.selectedZone);
    
    if (!this.selectedZone) {
      console.log('No selectedZone, returning empty options');
      return {};
    }
    
    const temps = this.selectedZone.temps || [];
    console.log('Raw temps data:', temps);
    
    if (!temps.length) {
      console.log('No temperature data available');
      return {};
    }

    const times = temps.map(t => {
      const date = new Date(t.time);
      // UTC 시간을 그대로 표시 (DB 시간과 동일)
      return date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false,
        timeZone: 'UTC'
      });
    });
    const minTemps = temps.map(t => Number(t.min));
    const maxTemps = temps.map(t => Number(t.max));
    const avgTemps = temps.map(t => Number(t.avg));
    console.log('Processed data:', {
      times: times.length,
      minTemps: minTemps.length,
      maxTemps: maxTemps.length,
      avgTemps: avgTemps.length,
      sampleTime: times[0],
      sampleMin: minTemps[0],
      sampleMax: maxTemps[0],
      sampleAvg: avgTemps[0]
    });

    // Y축 범위 계산 (음수값 허용)
    const allTemps = [...minTemps, ...maxTemps, ...avgTemps].filter(temp => !isNaN(temp) && temp !== null && temp !== undefined);
    const minTemp = allTemps.length > 0 ? Math.min(...allTemps) : 0;
    const maxTemp = allTemps.length > 0 ? Math.max(...allTemps) : 100;
    const tempRange = maxTemp - minTemp;
    const padding = tempRange > 0 ? tempRange * 0.1 : 5; // 10% 여유 공간 또는 최소 5도
    const yAxisMin = minTemp - padding; // 음수값 허용
    const yAxisMax = maxTemp + padding;

    const options = {
      tooltip: { 
        trigger: 'axis',
        formatter: function (params) {
          const time = params[0].axisValue;
          let result = `${time}<br/>`;
          params.forEach(param => {
            result += `${param.seriesName}: ${param.value}°C<br/>`;
          });
          return result;
        }
      },
      legend: {
        data: ['최소온도', '최대온도', '평균온도'],
        textStyle: {
          color: '#fff'
        }
      },
      xAxis: {
        type: 'category',
        data: times,
        name: '시간',
        boundaryGap: false,
        axisLabel: {
          color: '#fff',
          rotate: 45,
          formatter: '{value}'
        }
      },
      yAxis: {
        type: 'value',
        name: '온도(°C)',
        min: yAxisMin,
        max: yAxisMax,
        axisLabel: {
          color: '#fff',
          formatter: function (value) {
            return Math.round(value) + '°C';
          }
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.1)'
          }
        }
      },
      series: [
        {
          name: '최소온도',
          data: minTemps,
          type: 'line',
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#52c41a'
          },
          itemStyle: {
            color: '#52c41a'
          }
        },
        {
          name: '최대온도',
          data: maxTemps,
          type: 'line',
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#ff4d4f'
          },
          itemStyle: {
            color: '#ff4d4f'
          }
        },
        {
          name: '평균온도',
          data: avgTemps,
          type: 'line',
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#1890ff'
          },
          itemStyle: {
            color: '#1890ff'
          }
        }
      ],
      grid: { 
        left: 35, 
        right: 15, 
        top: 30, 
        bottom: 30,
        containLabel: true
      }
    };

    console.log('Generated chart options:', options);
    return options;
  }
},
mounted() {
  if (this.$sidebar) this.$sidebar.close();
  this.updateTime();
  this.timeInterval = setInterval(this.updateTime, 1000);
  
  // 소켓 연결 이벤트 리스너 등록
  this.$socket.client.on('connect', this.handleSocketConnect);
  this.$socket.client.on('disconnect', this.handleSocketDisconnect);
  
  // 소켓 연결 시작
  if (!this.$socket.client.connected) {
    this.$socket.client.connect();
  }
  this.initializeData();
  this.loadPopupNotificationSetting(); // 팝업 알림 설정 로드
  this.loadAlertHistory();
  // 실시간 누수감지상태 정보를 10초마다 갱신
  this.alertHistoryInterval = setInterval(() => {
    this.loadAlertHistory();
  }, 10000); // 10초 (10000ms)
  this.loadSiteName();
  this.loadMapImage();
  // 실시간 댐 데이터를 1분마다 갱신
  this.damDataInterval = setInterval(() => {
    this.loadSiteName();
  }, 60000); // 1분 (60000ms)
  
  // 현재 선택된 항목에 대한 차트를 1분마다 자동 갱신 (클릭 효과 포함)
  this.showChartInterval = setInterval(() => {
    if (this.selectedZoneIdx !== null && this.selectedZoneIdx !== undefined && this.zones.length > 0) {
      const selectedZone = this.zones[this.selectedZoneIdx];
      if (selectedZone) {
        // 클릭 효과를 위한 시각적 피드백
        this.clickingZoneIdx = this.selectedZoneIdx;
        this.showChart(selectedZone, this.selectedZoneIdx);
        // 클릭 효과 제거 (300ms 후)
        setTimeout(() => {
          this.clickingZoneIdx = null;
        }, 300);
      }
    }
  }, 60000); // 1분 (60000ms)
  
  // 실화상 영상을 1시간마다 리로드
  this.visibleCameraReloadInterval = setInterval(() => {
    if (this.visibleCamera) {
      // videoKeyVisible을 업데이트하여 VideoCard 컴포넌트 리마운트
      this.videoKeyVisible = this.visibleCamera.name + '_' + Date.now();
      console.log('실화상 영상 리로드:', this.videoKeyVisible);
    }
  }, 3600000); // 1시간 (3600000ms)
},
beforeDestroy() {
  if (this.timeInterval) {
    clearInterval(this.timeInterval);
  }
  if (this.alertHistoryInterval) {
    clearInterval(this.alertHistoryInterval);
  }
  if (this.damDataInterval) {
    clearInterval(this.damDataInterval);
  }
  if (this.showChartInterval) {
    clearInterval(this.showChartInterval);
  }
  if (this.visibleCameraReloadInterval) {
    clearInterval(this.visibleCameraReloadInterval);
  }
  // 소켓 이벤트 리스너 제거
  this.$socket.client.off('connect', this.handleSocketConnect);
  this.$socket.client.off('disconnect', this.handleSocketDisconnect);
},
methods: {
  handleSocketConnect() {
    console.log('Socket connected');
    this.socketConnected = true;
    this.initializeData();
  },
  handleSocketDisconnect() {
    console.log('Socket disconnected');
    this.socketConnected = false;
  },
  async initializeData() {
    try {
      await Promise.all([
        this.fetchWeather(),
        this.loadZones(),
        this.loadCameras()
      ]);
    this.loading = false;
    } catch (error) {
      console.error('Error initializing data:', error);
      this.loading = false;
    }
  },
  updateTime() {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const day = now.getDate();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    
    this.currentTime = `${year}년 ${month}월 ${day}일 ${hours}:${minutes}:${seconds}`;
  },
  // zone.minTemp와 zone.maxTemp 중 작은 값을 최소온도로 반환
  getMinTemp(zone) {
    // getRoiDataList API는 문자열('--' 또는 숫자 문자열)을 반환할 수 있음
    const minTemp = zone.minTemp;
    const maxTemp = zone.maxTemp;
    
    if (minTemp === '--' || minTemp == null) {
      if (maxTemp === '--' || maxTemp == null) {
        return '--';
      }
      return maxTemp;
    }
    if (maxTemp === '--' || maxTemp == null) {
      return minTemp;
    }
    // 둘 다 숫자인 경우 작은 값 반환
    const minNum = typeof minTemp === 'string' ? parseFloat(minTemp) : minTemp;
    const maxNum = typeof maxTemp === 'string' ? parseFloat(maxTemp) : maxTemp;
    if (isNaN(minNum) || isNaN(maxNum)) {
      return '--';
    }
    return Math.min(minNum, maxNum).toFixed(1);
  },
  // zone.minTemp와 zone.maxTemp 중 큰 값을 최대온도로 반환
  getMaxTemp(zone) {
    // getRoiDataList API는 문자열('--' 또는 숫자 문자열)을 반환할 수 있음
    const minTemp = zone.minTemp;
    const maxTemp = zone.maxTemp;
    
    if (minTemp === '--' || minTemp == null) {
      if (maxTemp === '--' || maxTemp == null) {
        return '--';
      }
      return maxTemp;
    }
    if (maxTemp === '--' || maxTemp == null) {
      return minTemp;
    }
    // 둘 다 숫자인 경우 큰 값 반환
    const minNum = typeof minTemp === 'string' ? parseFloat(minTemp) : minTemp;
    const maxNum = typeof maxTemp === 'string' ? parseFloat(maxTemp) : maxTemp;
    if (isNaN(minNum) || isNaN(maxNum)) {
      return '--';
    }
    return Math.max(minNum, maxNum).toFixed(1);
  },
  async fetchWeather() {
    try {
      // 1. 현장위치(address) 불러오기
      const data = await getEventSetting();
      let address = '';
      if (data && data.system_json) {
        const system = JSON.parse(data.system_json);
        address = system.address || '';
      }

      // 2. 주소가 있으면 날씨 API 호출
      let weatherData = {
        temperature: '--',
        description: '날씨 정보 없음',
        location: address || '위치 미설정'
      };

      if (address) {
        const apiKey = '550d972c6e25316a8a59ad0f07c6c237';
        const baseUrl = 'https://api.openweathermap.org/data/2.5/';
        const response = await fetch(
          `${baseUrl}weather?q=${encodeURIComponent(address)}&units=metric&appid=${apiKey}&lang=kr`
        );
        const owmInfo = await response.json();
        if (owmInfo && owmInfo.main && owmInfo.weather && owmInfo.weather[0]) {
          weatherData = {
            temperature: Math.round(owmInfo.main.temp),
            description: owmInfo.weather[0].description,
            location: weatherData.location
          };
        }
      }

      this.weather = weatherData;
    } catch (error) {
      console.error('날씨 정보를 가져오는데 실패했습니다:', error);
      this.weather = {
        temperature: '--',
        description: '날씨 정보 없음',
        location: '위치 미설정'
      };
    }
  },
  async loadZones() {
    try {
      const res = await getRoiDataList();
      this.zones = res.data.result || [];
      if (this.zones.length > 0) {
        this.selectedZoneIdx = 0;
        this.selectedZone = this.zones[0];
        // 첫 번째 항목의 차트 데이터도 로드
        await this.showChart(this.zones[0]);
      }
    } catch (e) {
      console.error('영역 통계 정보를 불러오지 못했습니다:', e);
    }
  },
  selectZone(idx) {
    this.selectedZoneIdx = idx;
    this.selectedZone = this.zones[idx];
  },
  // PTZ 제어 관련 메서드
  async showPTZControl() {
    try {
      console.log('PTZ 팝업 열기 시작...');
      
      // EventSetting에서 열화상 카메라 설정 조회
      const eventSetting = await getEventSetting();
      console.log('EventSetting 조회 결과:', eventSetting);
      
      if (eventSetting && eventSetting.object_json) {
        try {
          const objectConfig = JSON.parse(eventSetting.object_json);
          console.log('object_json 파싱 결과:', objectConfig);
          
          if (objectConfig.thermalCamera) {
            console.log('thermalCamera 설정 발견:', objectConfig.thermalCamera);
            
            // IP 설정
            if (objectConfig.thermalCamera.ip) {
              this.ptzConfig.ip = objectConfig.thermalCamera.ip;
              console.log('IP 설정 완료:', this.ptzConfig.ip);
            } else {
              console.log('IP 설정이 없어 기본값 사용:', this.ptzConfig.ip);
            }
            
            // Port 설정 (팬틸트 제어용으로 32000, 웹 API는 별도 처리)
            this.ptzConfig.port = '32000';
            console.log('Port 설정 완료 (팬틸트 제어용):', this.ptzConfig.port);
            
            // Speed 설정 (있는 경우)
            if (objectConfig.thermalCamera.speed) {
              this.ptzConfig.speed = objectConfig.thermalCamera.speed;
              console.log('Speed 설정 완료:', this.ptzConfig.speed);
            }
            
            console.log('최종 PTZ 설정:', this.ptzConfig);
          } else {
            console.log('thermalCamera 설정이 object_json에 없음, 기본값 사용');
          }
        } catch (parseError) {
          console.error('object_json 파싱 실패:', parseError);
          console.log('기본 PTZ 설정 사용');
        }
      } else {
        console.log('object_json이 없음, 기본값 사용');
      }
      
      // 연결 상태 초기화
      this.connectionStatus = null;
      this.ipError = '';
      
    } catch (error) {
      console.error('EventSetting 조회 실패:', error);
      console.log('기본 PTZ 설정 사용');
    }
    
    // 연결 상태 설정 (홈프리셋 버튼 활성화를 위해)
    this.connected = true;
    this.connectionStatus = { 
      type: 'success', 
      message: `연결 준비 완료: ${this.ptzConfig.ip}:80 (웹 API)` 
    };
    
    // 프리셋 팝업 열기
    this.ptzDialog = true;
    console.log('PTZ 팝업 열기 완료');
    
    // 3개 프리셋 값을 자동으로 로드
    await this.loadAllPresets();
  },

  // IP 유효성 검사
  validateIP() {
    const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    
    if (!this.ptzConfig.ip) {
      this.ipError = 'IP 주소를 입력해주세요';
      this.connectionStatus = { type: 'warning', message: 'IP 주소를 입력해주세요' };
    } else if (!ipRegex.test(this.ptzConfig.ip)) {
      this.ipError = '올바른 IP 주소 형식이 아닙니다';
      this.connectionStatus = { type: 'warning', message: '올바른 IP 주소 형식이 아닙니다' };
    } else {
      this.ipError = '';
      this.updateConnectionStatus();
    }
  },


  // 연결 상태 업데이트
  updateConnectionStatus() {
    console.log('🔗 연결 상태 업데이트');
    console.log('🔍 IP Error:', this.ipError);
    console.log('🔍 PTZ Config:', this.ptzConfig);
    
    if (!this.ipError) {
      this.connectionStatus = { 
        type: 'success', 
        message: `연결 준비 완료: ${this.ptzConfig.ip}:80 (웹 API)` 
      };
      this.connected = true;
      console.log('✅ 연결 상태: 준비 완료');
    } else {
      this.connectionStatus = { 
        type: 'error', 
        message: 'IP 주소를 올바르게 입력해주세요' 
      };
      this.connected = false;
      console.log('❌ 연결 상태: 오류');
    }
  },

  async ptzMove(direction) {
    // IP 유효성 검사
    if (this.ipError) {
      this.$toast.error('IP 주소를 올바르게 입력해주세요');
      return;
    }
    
    // 속도 값 유효성 검사 및 변환
    let speed = parseInt(this.ptzConfig.speed);
    if (isNaN(speed) || speed < 1 || speed > 63) {
      console.warn(`유효하지 않은 속도 값: ${this.ptzConfig.speed}, 기본값 32 사용`);
      speed = 32;
    }
    
    try {
      await ptzMove(direction, speed, this.ptzConfig.ip, this.ptzConfig.port);
      console.log(`PTZ Move: ${direction} with speed ${speed}`);
    } catch (error) {
      console.error('PTZ Move Error:', error);
      this.$toast.error('PTZ 제어 명령 전송 실패');
    }
  },

  async ptzStop() {
    // IP 유효성 검사
    if (this.ipError) {
      this.$toast.error('IP 주소를 올바르게 입력해주세요');
      return;
    }
    
    try {
      await ptzStop(this.ptzConfig.ip, this.ptzConfig.port);
      console.log('PTZ Stop command sent');
    } catch (error) {
      console.error('PTZ Stop Error:', error);
    }
  },

  async ptzZoom(direction) {
    // IP 유효성 검사
    if (this.ipError) {
      this.$toast.error('IP 주소를 올바르게 입력해주세요');
      return;
    }
    
    try {
      await ptzZoom(direction, this.ptzConfig.ip, this.ptzConfig.port);
      console.log(`PTZ Zoom: ${direction}`);
    } catch (error) {
      console.error('PTZ Zoom Error:', error);
      this.$toast.error('줌 제어 명령 전송 실패');
    }
  },

  async ptzFocus(direction) {
    // IP 유효성 검사
    if (this.ipError) {
      this.$toast.error('IP 주소를 올바르게 입력해주세요');
      this.connectionStatus = { type: 'error', message: 'IP 주소를 올바르게 입력해주세요' };
      return;
    }
    
    try {
      await ptzFocus(direction, this.ptzConfig.ip, this.ptzConfig.port);
      console.log(`PTZ Focus: ${direction}`);
    } catch (error) {
      console.error('PTZ Focus Error:', error);
      this.$toast.error('포커스 제어 명령 전송 실패');
    }
  },

  async ptzWiper(action) {
    // IP 유효성 검사
    if (this.ipError) {
      this.$toast.error('IP 주소를 올바르게 입력해주세요');
      this.connectionStatus = { type: 'error', message: 'IP 주소를 올바르게 입력해주세요' };
      return;
    }
    
    try {
      await ptzWiper(action, this.ptzConfig.ip, this.ptzConfig.port);
      console.log(`PTZ Wiper: ${action}`);
      this.$toast.success(`와이퍼 ${action === 'on' ? 'ON' : 'OFF'} 명령 전송 완료`);
    } catch (error) {
      console.error('PTZ Wiper Error:', error);
      this.$toast.error('와이퍼 제어 명령 전송 실패');
    }
  },

  // 파노라마 버튼 클릭
  async showPanorama() {
    try {
      this.$toast.info('파노라마 데이터를 불러오는 중...');
      await this.loadPanoramaData();
      this.panoramaDialog = true;
    } catch (error) {
      console.error('파노라마 데이터 로드 실패:', error);
      this.$toast.error('파노라마 데이터를 불러올 수 없습니다.');
    }
  },

  // 파노라마 데이터 로드
  async loadPanoramaData() {
    try {
      const response = await getPanoramaData(5);
      this.panoramaDataList = response.data || [];
      
      if (this.panoramaDataList.length > 0) {
        this.currentPanoramaIndex = 0;
        this.setCurrentPanoramaImage();
      } else {
        this.$toast.warning('파노라마 데이터가 없습니다.');
      }
    } catch (error) {
      console.error('파노라마 데이터 로드 오류:', error);
      throw error;
    }
  },

  // 현재 파노라마 이미지 설정
  setCurrentPanoramaImage() {
    if (this.panoramaDataList.length > 0 && this.currentPanoramaIndex < this.panoramaDataList.length) {
      const panoramaData = this.panoramaDataList[this.currentPanoramaIndex];
      this.currentPanoramaData = panoramaData;
      
      try {
        // panoramaData JSON 파싱
        const parsedData = JSON.parse(panoramaData.panoramaData);
        if (parsedData.image) {
          this.currentPanoramaImage = `data:image/jpeg;base64,${parsedData.image}`;
        } else {
          this.currentPanoramaImage = null;
        }
      } catch (error) {
        console.error('파노라마 데이터 파싱 오류:', error);
        this.currentPanoramaImage = null;
      }
    } else {
      this.currentPanoramaImage = null;
      this.currentPanoramaData = null;
    }
  },

  // 이전 파노라마 이미지
  previousPanorama() {
    if (this.currentPanoramaIndex > 0) {
      this.currentPanoramaIndex--;
      this.setCurrentPanoramaImage();
    }
  },

  // 다음 파노라마 이미지
  nextPanorama() {
    if (this.currentPanoramaIndex < this.panoramaDataList.length - 1) {
      this.currentPanoramaIndex++;
      this.setCurrentPanoramaImage();
    }
  },

  // 현재 위치 불러오기 (웹 API)
  async getCurrentPosition() {
    try {
      console.log('📍 현재 위치 불러오기 시작');
      
      // IP 유효성 검사
      if (this.ipError) {
        this.$toast.error('IP 주소를 올바르게 입력해주세요');
        this.addLog('현재 위치 불러오기 실패: IP 오류');
        return;
      }

      this.addLog('현재 위치 불러오기 요청 중...');
      
      const response = await getPTZPosition(this.ptzConfig.ip, 1);
      
      console.log('🔍 Current Position Response:', response);
      
      if (response.success && response.data && response.data.ptzValues) {
        const { pan, tilt, zoom } = response.data.ptzValues;

        console.log(`🔍 Current Position: Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}`);

        this.$toast.success(`현재 위치 불러오기 완료 (Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%)`);
        this.addLog(`현재 위치 불러오기 완료 - Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%`);
      } else {
        this.$toast.error(`현재 위치 불러오기 실패: ${response.message || '알 수 없는 오류'}`);
        this.addLog(`현재 위치 불러오기 실패: ${response.message || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('Current Position Error:', error);
      this.$toast.error('현재 위치 불러오기 실패');
      this.addLog(`현재 위치 불러오기 실패: ${error.message}`);
    }
  },

  // 현재 위치 저장하기 (웹 API)
  async setCurrentPosition() {
    try {
      console.log('💾 현재 위치 저장하기 시작');
      
      // IP 유효성 검사
      if (this.ipError) {
        this.$toast.error('IP 주소를 올바르게 입력해주세요');
        this.addLog('현재 위치 저장하기 실패: IP 오류');
        return;
      }

      // 먼저 현재 위치를 불러옴
      this.addLog('현재 위치 조회 중...');
      const getResponse = await getPTZPosition(this.ptzConfig.ip, 1);
      
      if (!getResponse.success || !getResponse.data || !getResponse.data.ptzValues) {
        this.$toast.error('현재 위치를 조회할 수 없습니다');
        this.addLog('현재 위치 저장하기 실패: 위치 조회 실패');
        return;
      }

      const { pan, tilt, zoom } = getResponse.data.ptzValues;
      this.addLog(`현재 위치: Pan=${pan}°, Tilt=${tilt}°, Zoom=${zoom}%`);

      // 1번 프리셋으로 저장
      this.addLog('1번 프리셋으로 저장 중...');
      const response = await setPTZPosition(this.ptzConfig.ip, pan, tilt, zoom, 1);
      
      console.log('🔍 Set Position Response:', response);
      
      if (response.success) {
        this.$toast.success(`현재 위치 저장 완료 (Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%)`);
        this.addLog(`현재 위치 저장 완료 - Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%`);
      } else {
        this.$toast.error(`현재 위치 저장 실패: ${response.message || '알 수 없는 오류'}`);
        this.addLog(`현재 위치 저장 실패: ${response.message || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('Set Position Error:', error);
      this.$toast.error('현재 위치 저장 실패');
      this.addLog(`현재 위치 저장 실패: ${error.message}`);
    }
  },

  // 1번 프리셋 불러오기
  async loadPreset1() {
    try {
      console.log('📍 1번 프리셋 불러오기 시작');
      
      // IP 유효성 검사
      if (this.ipError) {
        this.$toast.error('IP 주소를 올바르게 입력해주세요');
        this.addLog('1번 프리셋 불러오기 실패: IP 오류');
        return;
      }

      this.addLog('1번 프리셋 조회 중...');
      
      const response = await getPTZPosition(this.ptzConfig.ip, 1);
      
      console.log('🔍 Preset 1 Response:', response);
      
      if (response.success && response.data && response.data.ptzValues) {
        const { pan, tilt, zoom } = response.data.ptzValues;

        console.log(`🔍 Preset 1 Values: Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}`);

        // 1번 프리셋 입력 필드에 값 적용
        this.presetValues.preset1.pan = pan;
        this.presetValues.preset1.tilt = tilt;
        this.presetValues.preset1.zoom = zoom;

        this.$toast.success(`1번 프리셋 불러오기 완료 (Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%)`);
        this.addLog(`1번 프리셋 불러오기 완료 - Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%`);
      } else {
        this.$toast.error(`1번 프리셋 불러오기 실패: ${response.message || '알 수 없는 오류'}`);
        this.addLog(`1번 프리셋 불러오기 실패: ${response.message || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('Preset 1 Error:', error);
      this.$toast.error('1번 프리셋 불러오기 실패');
      this.addLog(`1번 프리셋 불러오기 실패: ${error.message}`);
    }
  },

  // 2번 프리셋 불러오기
  async loadPreset2() {
    try {
      console.log('📍 2번 프리셋 불러오기 시작');
      
      // IP 유효성 검사
      if (this.ipError) {
        this.$toast.error('IP 주소를 올바르게 입력해주세요');
        this.addLog('2번 프리셋 불러오기 실패: IP 오류');
        return;
      }

      this.addLog('2번 프리셋 조회 중...');
      
      const response = await getPTZPosition(this.ptzConfig.ip, 2);
      
      console.log('🔍 Preset 2 Response:', response);
      
      if (response.success && response.data && response.data.ptzValues) {
        const { pan, tilt, zoom } = response.data.ptzValues;

        console.log(`🔍 Preset 2 Values: Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}`);

        // 2번 프리셋 입력 필드에 값 적용
        this.presetValues.preset2.pan = pan;
        this.presetValues.preset2.tilt = tilt;
        this.presetValues.preset2.zoom = zoom;

        this.$toast.success(`2번 프리셋 불러오기 완료 (Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%)`);
        this.addLog(`2번 프리셋 불러오기 완료 - Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%`);
      } else {
        this.$toast.error(`2번 프리셋 불러오기 실패: ${response.message || '알 수 없는 오류'}`);
        this.addLog(`2번 프리셋 불러오기 실패: ${response.message || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('Preset 2 Error:', error);
      this.$toast.error('2번 프리셋 불러오기 실패');
      this.addLog(`2번 프리셋 불러오기 실패: ${error.message}`);
    }
  },

  // 3번 프리셋 불러오기
  async loadPreset3() {
    try {
      console.log('📍 3번 프리셋 불러오기 시작');
      
      // IP 유효성 검사
      if (this.ipError) {
        this.$toast.error('IP 주소를 올바르게 입력해주세요');
        this.addLog('3번 프리셋 불러오기 실패: IP 오류');
        return;
      }

      this.addLog('3번 프리셋 조회 중...');
      
      const response = await getPTZPosition(this.ptzConfig.ip, 3);
      
      console.log('🔍 Preset 3 Response:', response);
      
      if (response.success && response.data && response.data.ptzValues) {
        const { pan, tilt, zoom } = response.data.ptzValues;

        console.log(`🔍 Preset 3 Values: Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}`);

        // 3번 프리셋 입력 필드에 값 적용
        this.presetValues.preset3.pan = pan;
        this.presetValues.preset3.tilt = tilt;
        this.presetValues.preset3.zoom = zoom;

        this.$toast.success(`3번 프리셋 불러오기 완료 (Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%)`);
        this.addLog(`3번 프리셋 불러오기 완료 - Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%`);
      } else {
        this.$toast.error(`3번 프리셋 불러오기 실패: ${response.message || '알 수 없는 오류'}`);
        this.addLog(`3번 프리셋 불러오기 실패: ${response.message || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('Preset 3 Error:', error);
      this.$toast.error('3번 프리셋 불러오기 실패');
      this.addLog(`3번 프리셋 불러오기 실패: ${error.message}`);
    }
  },

  // 모든 프리셋 값 자동 로드 (팝업 열 때 호출)
  async loadAllPresets() {
    try {
      console.log('📍 모든 프리셋 값 자동 로드 시작');
      
      // IP 유효성 검사
      if (this.ipError) {
        console.log('IP 오류로 인해 프리셋 로드 건너뜀');
        return;
      }

      this.addLog('서버에서 프리셋 목록 조회 중...');
      
      // 서버에서 프리셋 목록 조회
      const response = await getPresetList(this.ptzConfig.ip);
      
      console.log('🔍 Preset List Response:', response);
      
      if (response.success && response.data && response.data.presets) {
        const presets = response.data.presets;
        console.log(`🔍 Found ${presets.length} presets:`, presets);
        
        // 각 프리셋에 대해 값 설정
        for (const preset of presets) {
          const presetNum = preset.presetNumber;
          const pan = preset.pan || 0;
          const tilt = preset.tilt || 0;
          const zoom = preset.zoom || 1;
          
          console.log(`🔍 Preset ${presetNum} Values: Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}`);
          
          // 해당 프리셋 입력 필드에 값 적용
          if (presetNum === 1) {
            this.presetValues.preset1.pan = pan;
            this.presetValues.preset1.tilt = tilt;
            this.presetValues.preset1.zoom = zoom;
          } else if (presetNum === 2) {
            this.presetValues.preset2.pan = pan;
            this.presetValues.preset2.tilt = tilt;
            this.presetValues.preset2.zoom = zoom;
          } else if (presetNum === 3) {
            this.presetValues.preset3.pan = pan;
            this.presetValues.preset3.tilt = tilt;
            this.presetValues.preset3.zoom = zoom;
          }
        }
        
        this.$toast.success(`프리셋 값 자동 로드 완료 (${presets.length}개)`);
        this.addLog(`프리셋 값 자동 로드 완료 - ${presets.length}개 프리셋`);
      } else {
        console.log('프리셋 목록이 없거나 오류 발생, 개별 로드 시도');
        this.addLog('프리셋 목록 조회 실패, 개별 로드 시도');
        
        // 개별 프리셋 로드 시도
        await Promise.all([
          this.loadPreset1(),
          this.loadPreset2(),
          this.loadPreset3()
        ]);
      }
    } catch (error) {
      console.error('Load All Presets Error:', error);
      this.$toast.warning('프리셋 자동 로드 실패, 수동으로 불러오기를 시도해주세요');
      this.addLog(`프리셋 자동 로드 실패: ${error.message}`);
    }
  },

  // 1번 프리셋 저장하기
  async savePreset1() {
    try {
      console.log('💾 1번 프리셋 저장하기 시작');
      
      // IP 유효성 검사
      if (this.ipError) {
        this.$toast.error('IP 주소를 올바르게 입력해주세요');
        this.addLog('1번 프리셋 저장하기 실패: IP 오류');
        return;
      }

      // 입력된 값들을 가져옴
      const presetData = this.presetValues.preset1;
      
      if (!presetData.pan || !presetData.tilt || !presetData.zoom) {
        this.$toast.error('1번 프리셋의 Pan, Tilt, Zoom 값을 모두 입력해주세요');
        this.addLog('1번 프리셋 저장하기 실패: 값이 누락됨');
        return;
      }

      const { pan, tilt, zoom } = presetData;
      this.addLog(`1번 프리셋 저장 중: Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}`);

      const response = await setPTZPosition(this.ptzConfig.ip, pan, tilt, zoom, 1);
      
      console.log('🔍 Preset 1 Save Response:', response);
      
      if (response.success) {
        this.$toast.success(`1번 프리셋 저장 완료 (Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%)`);
        this.addLog(`1번 프리셋 저장 완료 - Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%`);
      } else {
        this.$toast.error(`1번 프리셋 저장 실패: ${response.message || '알 수 없는 오류'}`);
        this.addLog(`1번 프리셋 저장 실패: ${response.message || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('Preset 1 Save Error:', error);
      this.$toast.error('1번 프리셋 저장 실패');
      this.addLog(`1번 프리셋 저장 실패: ${error.message}`);
    }
  },

  // 2번 프리셋 저장하기
  async savePreset2() {
    try {
      console.log('💾 2번 프리셋 저장하기 시작');
      
      // IP 유효성 검사
      if (this.ipError) {
        this.$toast.error('IP 주소를 올바르게 입력해주세요');
        this.addLog('2번 프리셋 저장하기 실패: IP 오류');
        return;
      }

      // 입력된 값들을 가져옴
      const presetData = this.presetValues.preset2;
      
      if (!presetData.pan || !presetData.tilt || !presetData.zoom) {
        this.$toast.error('2번 프리셋의 Pan, Tilt, Zoom 값을 모두 입력해주세요');
        this.addLog('2번 프리셋 저장하기 실패: 값이 누락됨');
        return;
      }

      const { pan, tilt, zoom } = presetData;
      this.addLog(`2번 프리셋 저장 중: Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}`);

      const response = await setPTZPosition(this.ptzConfig.ip, pan, tilt, zoom, 2);
      
      console.log('🔍 Preset 2 Save Response:', response);
      
      if (response.success) {
        this.$toast.success(`2번 프리셋 저장 완료 (Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%)`);
        this.addLog(`2번 프리셋 저장 완료 - Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%`);
      } else {
        this.$toast.error(`2번 프리셋 저장 실패: ${response.message || '알 수 없는 오류'}`);
        this.addLog(`2번 프리셋 저장 실패: ${response.message || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('Preset 2 Save Error:', error);
      this.$toast.error('2번 프리셋 저장 실패');
      this.addLog(`2번 프리셋 저장 실패: ${error.message}`);
    }
  },

  // 3번 프리셋 저장하기
  async savePreset3() {
    try {
      console.log('💾 3번 프리셋 저장하기 시작');
      
      // IP 유효성 검사
      if (this.ipError) {
        this.$toast.error('IP 주소를 올바르게 입력해주세요');
        this.addLog('3번 프리셋 저장하기 실패: IP 오류');
        return;
      }

      // 입력된 값들을 가져옴
      const presetData = this.presetValues.preset3;
      
      if (!presetData.pan || !presetData.tilt || !presetData.zoom) {
        this.$toast.error('3번 프리셋의 Pan, Tilt, Zoom 값을 모두 입력해주세요');
        this.addLog('3번 프리셋 저장하기 실패: 값이 누락됨');
        return;
      }

      const { pan, tilt, zoom } = presetData;
      this.addLog(`3번 프리셋 저장 중: Pan=${pan}, Tilt=${tilt}, Zoom=${zoom}`);

      const response = await setPTZPosition(this.ptzConfig.ip, pan, tilt, zoom, 3);
      
      console.log('🔍 Preset 3 Save Response:', response);
      
      if (response.success) {
        this.$toast.success(`3번 프리셋 저장 완료 (Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%)`);
        this.addLog(`3번 프리셋 저장 완료 - Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%`);
      } else {
        this.$toast.error(`3번 프리셋 저장 실패: ${response.message || '알 수 없는 오류'}`);
        this.addLog(`3번 프리셋 저장 실패: ${response.message || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('Preset 3 Save Error:', error);
      this.$toast.error('3번 프리셋 저장 실패');
      this.addLog(`3번 프리셋 저장 실패: ${error.message}`);
    }
  },

  // 홈 프리셋으로 이동 (웹 API)
  async goToHomePreset() {
    try {
      console.log('🏠 홈 프리셋 이동 시작');
      
      // IP 유효성 검사
      if (this.ipError) {
        this.$toast.error('IP 주소를 올바르게 입력해주세요');
        this.addLog('홈 프리셋 이동 실패: IP 오류');
        return;
      }

      this.addLog('홈 프리셋 이동 요청 중...');
      
      // 홈 프리셋 이동 API 호출 (INI 파일에서 1번 프리셋 값을 읽어서 setPosition 호출)
      const response = await fetch('/api/ptz/home', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ip: this.ptzConfig.ip })
      });
      
      const data = await response.json();
      
      if (data.success) {
        const { pan, tilt, zoom } = data.data.ptzValues;
        this.$toast.success(`홈 프리셋으로 이동 완료 (Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%)`);
        this.addLog(`홈 프리셋으로 이동 완료 - Pan: ${pan}°, Tilt: ${tilt}°, Zoom: ${zoom}%`);
      } else {
        this.$toast.error(`홈 프리셋 이동 실패: ${data.message || '알 수 없는 오류'}`);
        this.addLog(`홈 프리셋 이동 실패: ${data.message || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('Home Preset Error:', error);
      this.$toast.error('홈 프리셋으로 이동 실패');
      this.addLog(`홈 프리셋으로 이동 실패: ${error.message}`);
    }
  },

  // 로그 추가
  addLog(message) {
    const timestamp = new Date().toLocaleTimeString('ko-KR');
    this.logContent += `[${timestamp}] ${message}\n`;
    
    // 다음 틱에서 자동 스크롤
    this.$nextTick(() => {
      this.scrollToBottom();
    });
  },

  // 로그 영역을 맨 아래로 스크롤
  scrollToBottom() {
    this.$nextTick(() => {
      const logArea = this.$refs.logArea;
      if (logArea) {
        const textarea = logArea.querySelector('textarea');
        if (textarea) {
          // 스크롤을 맨 아래로
          textarea.scrollTop = textarea.scrollHeight;
          
          // 추가적인 스크롤 보장
          setTimeout(() => {
            textarea.scrollTop = textarea.scrollHeight;
          }, 10);
        }
      }
    });
  },

  // 투어 스텝 쓰기
  async writeTourSteps() {
    try {
      console.log('⚙️ 투어 스텝 쓰기 시작');
      console.log('🔍 IP Error:', this.ipError);
      console.log('🔍 Port Error:', this.portError);
      console.log('🔍 Tour Speed:', this.tourSpeed);
      console.log('🔍 PTZ Config:', this.ptzConfig);
      
      // IP와 Port 유효성 검사
      if (this.ipError || this.portError) {
        this.$toast.error('IP 주소와 포트를 올바르게 입력해주세요');
        this.addLog('투어 스텝 설정 실패: IP/Port 오류');
        return;
      }

      if (!this.tourSpeed || this.tourSpeed <= 0) {
        this.$toast.error('투어 속도를 올바르게 입력해주세요');
        this.addLog('투어 스텝 설정 실패: 속도 오류');
        return;
      }

      this.addLog('투어 스텝 설정 요청 중...');
      console.log('📡 API 호출: pntTourSetup(' + this.tourSpeed + ', 60, ' + this.ptzConfig.ip + ', ' + this.ptzConfig.port + ')');
      
      await pntTourSetup(this.tourSpeed, 60, this.ptzConfig.ip, this.ptzConfig.port);
      this.$toast.success('투어 스텝 설정 완료 (Preset 1-3)');
      this.addLog(`투어 스텝 설정: 속도=${this.tourSpeed}rpm, 지연=60초`);
    } catch (error) {
      console.error('Tour Setup Error:', error);
      this.$toast.error('투어 스텝 설정 실패');
      this.addLog(`투어 스텝 설정 실패: ${error.message}`);
    }
  },

  // 투어 시작
  async startTour() {
    try {
      await pntTourStart(this.ptzConfig.ip, this.ptzConfig.port);
      this.tourRunning = true;
      this.tourStatus = '투어 실행 중';
      this.$toast.success('투어 시작');
      this.addLog('투어 시작');
    } catch (error) {
      console.error('Tour Start Error:', error);
      this.$toast.error('투어 시작 실패');
      this.addLog(`투어 시작 실패: ${error.message}`);
    }
  },

  // 투어 정지
  async stopTour() {
    try {
      await pntTourStop(this.ptzConfig.ip, this.ptzConfig.port);
      this.tourRunning = false;
      this.tourStatus = '대기 중';
      this.$toast.success('투어 정지');
      this.addLog('투어 정지');
    } catch (error) {
      console.error('Tour Stop Error:', error);
      this.$toast.error('투어 정지 실패');
      this.addLog(`투어 정지 실패: ${error.message}`);
    }
  },

  // 드래그 시작
  startDrag(event) {
    if (event.target.closest('.close-btn')) return; // 닫기 버튼 클릭 시 드래그 방지
    
    this.isDragging = true;
    this.dragStartX = event.clientX;
    this.dragStartY = event.clientY;
    
    const dialogElement = this.$refs.ptzDialogCard?.$el;
    if (dialogElement) {
      const rect = dialogElement.getBoundingClientRect();
      this.dialogOffsetX = rect.left;
      this.dialogOffsetY = rect.top;
    }
    
    document.addEventListener('mousemove', this.onDrag);
    document.addEventListener('mouseup', this.stopDrag);
    event.preventDefault();
  },

  // 드래그 중
  onDrag(event) {
    if (!this.isDragging) return;
    
    const deltaX = event.clientX - this.dragStartX;
    const deltaY = event.clientY - this.dragStartY;
    
    const newX = this.dialogOffsetX + deltaX;
    const newY = this.dialogOffsetY + deltaY;
    
    const dialogElement = this.$refs.ptzDialogCard?.$el;
    if (dialogElement) {
      dialogElement.style.position = 'fixed';
      dialogElement.style.left = `${newX}px`;
      dialogElement.style.top = `${newY}px`;
      dialogElement.style.margin = '0';
      dialogElement.style.transform = 'none';
      dialogElement.style.width = '1200px'; // 원래 크기 유지
      dialogElement.style.maxWidth = '1200px'; // 원래 크기 유지
    }
  },

  // 드래그 종료
  stopDrag() {
    this.isDragging = false;
    document.removeEventListener('mousemove', this.onDrag);
    document.removeEventListener('mouseup', this.stopDrag);
  },

  async loadCameras() {
    try {
      const response = await getCameras();
      for (const camera of response.data.result) {
        const settings = await getCameraSettings(camera.name);
        camera.settings = settings.data.settings;
        camera.live = camera.settings.camview?.live || false;
        camera.refreshTimer = camera.settings.camview?.refreshTimer || 60;
        camera.url = camera.videoConfig.source.replace(/\u00A0/g, ' ').split('-i ')[1];
      }
      this.cameraList = response.data.result;
      
      // videoType에 따라 카메라 분류
      this.thermalCamera = null;
      this.visibleCamera = null;
      
      for (const camera of this.cameraList) {
        const videoType = camera.videoConfig?.videoType || 1;
        if (videoType === 1) {
          // 열화상 카메라
          if (!this.thermalCamera) {
            this.thermalCamera = camera;
          }
        } else if (videoType === 2) {
          // 실화상 카메라
          if (!this.visibleCamera) {
            this.visibleCamera = camera;
          }
        }
      }
      
      // videoType이 없는 경우 기존 로직으로 fallback
      if (!this.thermalCamera && !this.visibleCamera && this.cameraList.length > 0) {
        this.thermalCamera = this.cameraList[0] || null;
        this.visibleCamera = this.cameraList[1] || null;
      }
      
      this.videoKeyThermal = this.thermalCamera ? this.thermalCamera.name + '_' + Date.now() : '';
      this.videoKeyVisible = this.visibleCamera ? this.visibleCamera.name + '_' + Date.now() : '';
    } catch (err) {
      console.error('Error loading cameras:', err);
      this.thermalCamera = null;
      this.visibleCamera = null;
    }
  },
  cameraStatus(data) {
    if (!this.camStates.some((cam) => cam.name === data.name)) {
      this.camStates.push(data);
    }
  },
  async downloadExcel(zone) {
    try {
      // ROI 번호 추출 (zone_type 또는 zone_desc에서)
      let roiNumber = null;
      // zone_type이 0이어도 유효한 값이므로 명시적으로 체크
      if (zone.zone_type !== null && zone.zone_type !== undefined && zone.zone_type !== '') {
        if (typeof zone.zone_type === 'string' && zone.zone_type.startsWith('Z')) {
          roiNumber = parseInt(zone.zone_type.replace('Z', ''));
        } else if (typeof zone.zone_type === 'string') {
          roiNumber = parseInt(zone.zone_type);
        } else if (typeof zone.zone_type === 'number') {
          roiNumber = zone.zone_type;
        }
      }
      
      // zone_type에서 추출 실패한 경우 zone_desc에서 시도
      if (roiNumber === null && zone.zone_desc) {
        const match = zone.zone_desc.match(/\d+/);
        if (match) {
          roiNumber = parseInt(match[0]);
        }
      }
      
      
      // 해당 ROI의 30일치 시계열 온도 데이터 가져오기
      this.$toast.info('데이터를 불러오는 중...');
      const response = await getRoiTemperatureTimeSeries({ 
        roiNumber: roiNumber,
        days: 30  // 30일치 데이터 조회
      });
      
      if (!response.data || !response.data.success || !response.data.result) {
        this.$toast.error('시계열 데이터를 가져올 수 없습니다.');
        return;
      }
      
      const timeSeriesData = response.data.result.timeSeriesData || [];
      
      if (timeSeriesData.length === 0) {
        this.$toast.warning('다운로드할 데이터가 없습니다.');
        return;
      }
      
      // Create worksheet data
      const worksheetData = [];
      
      // Add headers
      worksheetData.push(['시간', '최소온도 (°C)', '최대온도 (°C)', '평균온도 (°C)']);
      
      // Add data rows - UTC 시간으로 표시
      timeSeriesData.forEach(temp => {
        const date = new Date(temp.time);
        const timeStr = date.toLocaleString('ko-KR', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          timeZone: 'UTC'
        });
        
        worksheetData.push([
          timeStr,
          typeof temp.min === 'string' ? temp.min : (temp.min ? parseFloat(temp.min).toFixed(1) : '--'),
          typeof temp.max === 'string' ? temp.max : (temp.max ? parseFloat(temp.max).toFixed(1) : '--'),
          typeof temp.avg === 'string' ? temp.avg : (temp.avg ? parseFloat(temp.avg).toFixed(1) : '--')
        ]);
      });

      // Create workbook and worksheet
      const wb = XLSX.utils.book_new();
      const ws = XLSX.utils.aoa_to_sheet(worksheetData);

      // Set column widths
      const colWidths = [
        { wch: 20 }, // Time column
        { wch: 12 }, // Min temp column
        { wch: 12 }, // Max temp column
        { wch: 12 }  // Avg temp column
      ];
      ws['!cols'] = colWidths;

      // Add worksheet to workbook
      XLSX.utils.book_append_sheet(wb, ws, 'Temperature Data');

      // Generate Excel file
      const excelBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
      const blob = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      
      // Create download link
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `${zone.zone_desc}_temperature_data.xlsx`;
      link.click();
      URL.revokeObjectURL(link.href);
      
      this.$toast.success('Excel 파일 다운로드가 완료되었습니다.');
    } catch (error) {
      console.error('Error downloading Excel:', error);
      this.$toast.error('Excel 다운로드 중 오류가 발생했습니다.');
    }
  },
  async showChart(zone, idx = null) {
    // 수동 클릭인 경우 클릭 효과 추가
    if (idx !== null && idx !== undefined) {
      this.clickingZoneIdx = idx;
      setTimeout(() => {
        this.clickingZoneIdx = null;
      }, 300);
    }
    
    console.log('=== showChart called ===');
    console.log('zone:', zone);
    console.log('idx:', idx);
    console.log('current selectedZoneIdx:', this.selectedZoneIdx);
    
    // 선택된 인덱스 업데이트
    let index = idx;
    if (index === null || index === undefined) {
      index = this.zones.findIndex(z => z.zone_desc === zone.zone_desc);
    }
    
    if (index !== -1) {
      this.selectedZoneIdx = index;
      console.log('Updated selectedZoneIdx to:', index);
    } else {
      console.warn('Could not find zone index');
    }
    
    // ROI 번호 추출 (zone_type 또는 zone_desc에서)
    let roiNumber = null;
    console.log('Zone object for ROI extraction:', zone);
    
    // zone_type이 0이어도 유효한 값이므로 명시적으로 체크
    if (zone.zone_type !== null && zone.zone_type !== undefined && zone.zone_type !== '') {
      // zone_type이 "Z1", "Z2" 형식인 경우
      if (typeof zone.zone_type === 'string' && zone.zone_type.startsWith('Z')) {
        roiNumber = parseInt(zone.zone_type.replace('Z', ''));
        console.log('Extracted ROI number from zone_type (Z format):', roiNumber);
      } else if (typeof zone.zone_type === 'string') {
        // 숫자 문자열인 경우 (예: "1", "2", "0")
        roiNumber = parseInt(zone.zone_type);
        console.log('Extracted ROI number from zone_type (number format):', roiNumber);
      } else if (typeof zone.zone_type === 'number') {
        // 숫자인 경우 (0 포함)
        roiNumber = zone.zone_type;
        console.log('Extracted ROI number from zone_type (number):', roiNumber);
      }
    }
    
    // zone_type에서 추출 실패한 경우 zone_desc에서 시도
    if (roiNumber === null && zone.zone_desc) {
      // zone_desc에서 숫자 추출 (예: "ROI 1" -> 1)
      const match = zone.zone_desc.match(/\d+/);
      if (match) {
        roiNumber = parseInt(match[0]);
        console.log('Extracted ROI number from zone_desc:', roiNumber);
      }
    }
    
    // ROI 온도 시계열 데이터 가져오기
    // roiNumber가 0일 수도 있으므로 !== null && !== undefined로 체크
    if (roiNumber !== null && roiNumber !== undefined && !isNaN(roiNumber)) {
      try {
        console.log('Calling API for ROI:', roiNumber);
        const response = await getRoiTemperatureTimeSeries({ 
          roiNumber: roiNumber,
          days: 30  // 차트는 30일치 데이터 조회
        });
        
        if (response.data && response.data.success && response.data.result) {
          // 가져온 데이터를 selectedZone.temps 형식으로 변환
          this.selectedZone = {
            ...zone,
            temps: response.data.result.timeSeriesData || []
          };
          console.log('Loaded temperature time series data:', this.selectedZone.temps);
        } else {
          console.warn('No temperature data found for ROI:', roiNumber);
          this.selectedZone = {
            ...zone,
            temps: zone.temps || []
          };
        }
      } catch (error) {
        console.error('Error loading temperature time series data:', error);
        this.selectedZone = {
          ...zone,
          temps: zone.temps || []
        };
      }
    } else {
      console.warn('Could not extract ROI number from zone:', zone, 'roiNumber:', roiNumber);
      this.selectedZone = {
        ...zone,
        temps: zone.temps || []
      };
    }
    
    console.log('Updated selectedZone:', this.selectedZone);
  },
  onChartReady(chartInstance) {
    console.log('Chart is ready!', chartInstance);
  },
  initGaugeChart() {
      const chartDom = this.$refs.gaugeChart;
      this.gaugeChart = echarts.init(chartDom);
      
      const option = {
        backgroundColor: 'transparent',
        series: [{
          type: 'gauge',
          startAngle: 180,
          endAngle: 0,
          center: ['50%', '75%'],
          radius: '90%',
          min: 0,
          max: 4,
          splitNumber: 4,
          axisLine: {
            lineStyle: {
              width: 20,
              color: [
                [0.25, '#4B7BE5'],  // 관심 - 파랑
                [0.5, '#FFB800'],   // 주의 - 노랑
                [0.75, '#FF8A00'],  // 경계 - 주황
                [1, '#FF4B4B']      // 심각 - 빨강
              ]
            }
          },
          pointer: {
            icon: 'path://M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z',
            length: '60%',
            width: 8,
            offsetCenter: [0, '5%'],
            itemStyle: {
              color: '#999'
            }
          },
          axisTick: {
            length: 12,
            lineStyle: {
              color: 'auto',
              width: 2
            }
          },
          splitLine: {
            length: 20,
            lineStyle: {
              color: 'auto',
              width: 2
            }
          },
          axisLabel: {
            color: '#999',
            fontSize: 12,
            distance: -60,
            formatter: (value) => {
              if (value === 1) return '주의';
              if (value === 2) return '경고';
              if (value === 3) return '위험';
              if (value === 4) return '심각';
              if (value === 5) return '비상';
              return '';
            }
          },
          title: {
            offsetCenter: [0, '20%'],
            fontSize: 14,
            color: '#fff'
          },
          detail: {
            fontSize: 24,
            offsetCenter: [0, '40%'],
            valueAnimation: true,
            formatter: (value) => {
              return Math.round(value) + '단계';
            },
            color: '#fff'
          },
          data: [{
            value: this.alertCount,
            name: '경보 단계'
          }]
        }]
      };

      this.gaugeChart.setOption(option);
      window.addEventListener('resize', this.handleChartResize);
    },
    async loadAlertHistory() {
      try {
        // 최근 10분간의 데이터만 조회 (popup_close 값 무관)
        const now = new Date();
        const tenMinutesAgo = new Date(now.getTime() - 10 * 60 * 1000);
        
        // 로컬 시간대 형식으로 변환 (YYYY-MM-DDTHH:mm:ss 형식)
        // 서버가 로컬 시간대를 기대하므로 UTC가 아닌 로컬 시간 사용
        const formatLocalDateTime = (date) => {
          const year = date.getFullYear();
          const month = String(date.getMonth() + 1).padStart(2, '0');
          const day = String(date.getDate()).padStart(2, '0');
          const hours = String(date.getHours()).padStart(2, '0');
          const minutes = String(date.getMinutes()).padStart(2, '0');
          const seconds = String(date.getSeconds()).padStart(2, '0');
          return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
        };
        
        const startDate = formatLocalDateTime(tenMinutesAgo);
        const endDate = formatLocalDateTime(now);
        
        console.log(`[누수감지상태] 조회 시간 범위: ${startDate} ~ ${endDate} (로컬 시간)`);
        
        // API 호출 시 최근 10분간의 데이터만 요청, 최대 20개까지 조회
        const parameters = `?startDate=${encodeURIComponent(startDate)}&endDate=${encodeURIComponent(endDate)}&includeClosed=true&limit=20`;
        const response = await getAlerts(parameters);
        
        // 경보 데이터가 없거나 빈 배열인 경우 안전 상태로 설정
        if (!response.data.result || response.data.result.length === 0) {
          this.alertHistory = [];
          // zones는 loadZones에서 ROI API로 관리하므로 여기서는 설정하지 않음
          this.alertCount = 0;
          this.selectedStatusButton = 'safe';
          this.latestAlertInfo = null;
          this.unclosedAlerts = [];
          this.showAlertPopup = false;
          
          if (this.gaugeChart) {
            this.gaugeChart.setOption({
              series: [{
                data: [{
                  value: 0
                }],
                detail: {
                  formatter: () => '안전',
                  color: '#fff',
                  fontSize: 24,
                  offsetCenter: [0, '40%']
                }
              }]
            });
          }
          return;
        }
        
        // API에서 이미 최근 10분간의 데이터만 조회했으므로 추가 필터링 불필요
        // 하지만 서버가 정확히 10분을 필터링하지 않을 수 있으므로 클라이언트 측에서도 확인
        const recentAlerts = response.data.result.filter(alert => {
          const alertTime = new Date(alert.alert_accur_time);
          return alertTime >= tenMinutesAgo;
        });
        
        console.log(`[누수감지상태] API 조회 결과: ${response.data.result.length}개, 10분 이내 경보: ${recentAlerts.length}개`);
        
        // 10분 이내 경보를 alertHistory에 저장 (popup_close와 상관없이)
        this.alertHistory = recentAlerts.map(alert => {
          let minTemp = '-';
          let maxTemp = '-';
          let avgTemp = '-';
          try {
            const info = alert.alert_info_json ? JSON.parse(alert.alert_info_json) : {};
            minTemp = (typeof info.min_roi_value === 'number') ? info.min_roi_value.toFixed(1) : '-';
            maxTemp = (typeof info.max_roi_value === 'number') ? info.max_roi_value.toFixed(1) : '-';
            if (typeof info.min_roi_value === 'number' && typeof info.max_roi_value === 'number') {
              avgTemp = ((info.min_roi_value + info.max_roi_value) / 2).toFixed(1);
            }
          } catch (e) {
            // no-op
          }
          return {
            id: alert.id,
            time: this.formatDate(alert.alert_accur_time),
            type: alert.alert_type,
            level: alert.alert_level,
            maxTemp,
            minTemp,
            avgTemp,
            popup_close: alert.popup_close || 0,
            fk_detect_zone_id: alert.fk_detect_zone_id
          }
        });

        // alert API는 경보 정보만 처리하고, zones는 loadZones에서 ROI API로 관리

        // 팝업은 popup_close가 0인 경우만 표시 (10분 이내 경보 중에서), 최대 20개까지
        const unclosedAlertsData = recentAlerts
          .filter(alert => (alert.popup_close || 0) === 0)
          .slice(0, 20) // 최대 20개까지 제한
          .map(alert => {
            // alert_type에서 ROI 번호 추출 (S001 -> ROI 0, S002 -> ROI 1, ...)
            let roiNumber = '미지정';
            if (alert.alert_type) {
              // alert_type에서 숫자 추출 (예: "S001" -> "001" -> 1 -> ROI 0)
              const match = alert.alert_type.match(/\d+/);
              if (match) {
                const number = parseInt(match[0]);
                roiNumber = `ROI ${number - 1}`;
              }
            }
            
            return {
              id: alert.id,
              levelText: this.getLevelText(alert.alert_level),
              zoneName: roiNumber,
              time: this.formatDate(alert.alert_accur_time)
            };
          });
        
        this.unclosedAlerts = unclosedAlertsData;
        // 팝업 알림 설정이 활성화된 경우에만 팝업 표시
        this.showAlertPopup = unclosedAlertsData.length > 0 && this.popupNotificationEnabled;

        // 최신 경보단계로 gaugeChart 값 반영 (한글 문구로)
        // 경고 데이터 중 가장 위험한 값으로 감지상태 표시
        if (this.alertHistory.length > 0) {
          // alert_level이 가장 높은 경보 찾기 (가장 위험한 값)
          let highestAlert = this.alertHistory[0];
          let highestLevel = Number(highestAlert.level) || 0;
          
          console.log(`[누수감지상태] 경보 이력 ${this.alertHistory.length}개 조회, 첫 번째 경보 레벨: ${highestLevel}`);
          
          for (let i = 1; i < this.alertHistory.length; i++) {
            const currentLevel = Number(this.alertHistory[i].level) || 0;
            if (currentLevel > highestLevel) {
              console.log(`[누수감지상태] 더 높은 레벨 발견: ${currentLevel} > ${highestLevel} (이전 최고 레벨)`);
              highestLevel = currentLevel;
              highestAlert = this.alertHistory[i];
            }
          }
          
          console.log(`[누수감지상태] 최종 최고 레벨: ${highestLevel}, 경보 ID: ${highestAlert.id}`);
          
          // highestLevel을 사용하여 일관성 유지
          const alertLevel = highestLevel;
          
          // alert_level이 없거나, 0이거나, 유효하지 않은 경우 안전 상태로 설정
          if (alertLevel === 0 || alertLevel === null || alertLevel === undefined || isNaN(alertLevel)) {
            this.alertCount = 0;
            this.selectedStatusButton = 'safe';
            this.latestAlertInfo = null;
            
            if (this.gaugeChart) {
              this.gaugeChart.setOption({
                series: [{
                  data: [{
                    value: 0
                  }],
                  detail: {
                    formatter: () => '안전',
                    color: '#fff',
                    fontSize: 24,
                    offsetCenter: [0, '40%']
                  }
                }]
              });
            }
          } else {
            // 유효한 경보 레벨이 있는 경우
            this.alertCount = alertLevel;
            const levelLabel = this.getLevelText(alertLevel.toString());
            console.log(`[누수감지상태] 경보 레벨 설정: ${alertLevel} (${levelLabel}), alertCount: ${this.alertCount}`);
            if (this.gaugeChart) {
              this.gaugeChart.setOption({
                series: [{
                  data: [{
                    value: this.alertCount
                  }],
                  detail: {
                    formatter: () => levelLabel,
                    color: '#fff',
                    fontSize: 24,
                    offsetCenter: [0, '40%']
                  }
                }]
              });
            }
            
            // alert_level에 따른 버튼 매핑
            // alert_level 0 -> 안전, 1 -> 관심, 2 -> 주의, 3 -> 점검, 4 -> 대비
            const alertLevelNum = alertLevel; // 이미 숫자로 변환됨
            const buttonMapping = {
              0: 'safe',      // 안전
              1: 'attention', // 관심
              2: 'caution',   // 주의
              3: 'check',     // 점검
              4: 'prepare'    // 대비
            };
            
            const defaultButton = buttonMapping[alertLevelNum] || 'safe'; // 기본값을 safe로 변경
            this.selectedStatusButton = defaultButton; // 버튼 타입 설정
            console.log(`[누수감지상태] 버튼 상태 설정: ${defaultButton} (레벨 ${alertLevelNum})`);
            
            // 최신 경보 정보 설정 (가장 높은 레벨의 경보 정보 사용)
            this.latestAlertInfo = {
              level: this.getLevelText(alertLevel.toString()),
              maxTemp: highestAlert.maxTemp,
              minTemp: highestAlert.minTemp,
              time: highestAlert.time
            };
            console.log(`[누수감지상태] 최신 경보 정보 설정: 레벨=${this.latestAlertInfo.level}, 최대온도=${highestAlert.maxTemp}, 최소온도=${highestAlert.minTemp}`);
          }
        } else {
          // 경보 데이터가 없는 경우 안전 상태로 설정
          this.alertCount = 0;
          this.selectedStatusButton = 'safe';
          this.latestAlertInfo = null;
          
          if (this.gaugeChart) {
            this.gaugeChart.setOption({
              series: [{
                data: [{
                  value: 0
                }],
                detail: {
                  formatter: () => '안전',
                  color: '#fff',
                  fontSize: 24,
                  offsetCenter: [0, '40%']
                }
              }]
            });
          }
        }
      } catch (error) {
        console.error('알림 이력 조회 실패:', error);
        this.$toast?.error('알림 이력을 불러오는 중 오류가 발생했습니다.');
      }
    },
    formatDate(time) {
      if (!time) return '';
      
      try {
        let dateStr = String(time).trim();
        
        // ISO 형식에서 T를 공백으로 변환
        if (dateStr.includes('T')) {
          dateStr = dateStr.replace('T', ' ');
        }
        
        // .000Z, .0000Z 같은 밀리초 및 Z 제거
        dateStr = dateStr.replace(/\.\d+[Zz]?$/i, '').replace(/[Zz]$/i, '');
        
        // MySQL DATETIME 형식: "YYYY-MM-DD HH:mm:ss" 또는 "YYYY-MM-DD HH:mm"
        // 시간대 변환 없이 직접 파싱하여 포맷팅
        const dateTimeMatch = dateStr.match(/(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?/);
        if (dateTimeMatch) {
          const year = dateTimeMatch[1];
          const month = dateTimeMatch[2];
          const day = dateTimeMatch[3];
          const hours = dateTimeMatch[4];
          const minutes = dateTimeMatch[5];
          const seconds = dateTimeMatch[6] || '00';
          
          // 시간대 변환 없이 그대로 포맷팅 (DB에 저장된 로컬 시간 그대로 사용)
          return `${year}. ${month}. ${day}. ${hours}:${minutes}:${seconds}`;
        }
        
        // 시간만 있는 경우: "14:30:00" 또는 "14:30"
        if (dateStr.includes(':') && !dateStr.includes('-')) {
          const [hours, minutes] = dateStr.split(':');
          return `${hours}:${minutes}`;
        }
        
        // 파싱 실패 시 원본 반환
        return dateStr;
      } catch (error) {
        console.error('[formatDate] Date formatting error:', error, time);
        return String(time); // 에러 발생 시 원본 반환
      }
    },
    formatPanoramaDate(dateStr) {
      if (!dateStr) return '-';
      
      try {
        // DB에서 조회한 문자열을 그대로 사용
        let dateStrTrimmed = String(dateStr).trim();
        
        // .0000Z, .000Z, .00Z, .0Z, Z 같은 표현 제거
        dateStrTrimmed = dateStrTrimmed.replace(/\.\d+[Zz]?$/i, '').replace(/[Zz]$/i, '');
        
        // MySQL DATETIME 형식: "YYYY-MM-DD HH:mm:ss"
        // 날짜와 시간 부분을 직접 추출 (Date 객체 생성으로 인한 시간대 문제 방지)
        const dateTimeMatch = dateStrTrimmed.match(/(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})/);
        if (dateTimeMatch) {
          const year = dateTimeMatch[1];
          const month = dateTimeMatch[2];
          const day = dateTimeMatch[3];
          const hours = dateTimeMatch[4];
          const minutes = dateTimeMatch[5];
          const seconds = dateTimeMatch[6];
          
          // 년월일과 시간을 포함한 형식으로 포맷팅 (YYYY-MM-DD HH:mm:ss)
          return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
        }
        
        // 시간 형식을 찾을 수 없으면 그대로 반환
        return dateStrTrimmed;
      } catch (error) {
        console.error('[formatPanoramaDate] 날짜 포맷팅 오류:', error, dateStr);
        return String(dateStr);
      }
    },
    getLevelText(level) {
      const adjustedLevel = Number(level) + 1;
      const levels = {
        '1': '주의',
        '2': '경고',
        '3': '위험',
        '4': '심각',
        '5': '비상'
      };
      return levels[adjustedLevel] || adjustedLevel;
    },
    async loadPopupNotificationSetting() {
      try {
        const response = await getAlertSettings();
        if (response && response.result && response.result.alert_setting_json) {
          try {
            const alertSettingJson = JSON.parse(response.result.alert_setting_json);
            if (alertSettingJson.notification && alertSettingJson.notification.popupEnabled !== undefined) {
              this.popupNotificationEnabled = alertSettingJson.notification.popupEnabled;
              console.log('[팝업알림설정] 팝업 알림 설정: ' + this.popupNotificationEnabled);
            } else {
              // 설정이 없으면 기본값 true 사용
              this.popupNotificationEnabled = true;
              console.log('[팝업알림설정] 팝업 알림 설정이 없어 기본값(true) 사용');
            }
          } catch (e) {
            console.error('팝업 알림 설정 파싱 오류:', e);
            this.popupNotificationEnabled = true; // 기본값
          }
        } else {
          // 설정이 없으면 기본값 true 사용
          this.popupNotificationEnabled = true;
          console.log('[팝업알림설정] 팝업 알림 설정이 없어 기본값(true) 사용');
        }
      } catch (error) {
        console.error('팝업 알림 설정 로딩 오류:', error);
        this.popupNotificationEnabled = true; // 기본값
      }
    },
    async closeAlertPopup() {
      try {
        // 팝업에 표시된 경보들의 ID 목록
        const popupAlertIds = this.unclosedAlerts.map(alert => alert.id);
        
        // 1. 팝업에 표시된 경보들의 popup_close를 1로 업데이트
        const popupUpdatePromises = this.unclosedAlerts.map(alert => 
          updatePopupClose(alert.id)
        );
        
        // 2. 팝업 리스트 외의 DB상에 popup_close가 0인 경보들을 찾아서 모두 1로 업데이트
        const otherAlertsToUpdate = this.alertHistory.filter(alert => 
          !popupAlertIds.includes(alert.id) && (alert.popup_close || 0) === 0
        );
        
        const otherUpdatePromises = otherAlertsToUpdate.map(alert => 
          updatePopupClose(alert.id)
        );
        
        // 모든 업데이트를 병렬로 실행
        await Promise.all([...popupUpdatePromises, ...otherUpdatePromises]);
        
        // 팝업 닫기
        this.showAlertPopup = false;
        this.unclosedAlerts = [];
        
        // 경보 이력 다시 로드하여 팝업 상태 업데이트
        await this.loadAlertHistory();
      } catch (error) {
        console.error('팝업 닫기 실패:', error);
        this.$toast?.error('팝업을 닫는 중 오류가 발생했습니다.');
      }
    },
    async loadSiteName() {
      try {
        const data = await getEventSetting();
        if (data && data.system_json) {
          const system = JSON.parse(data.system_json);
          this.location_info = system.location_info || '';
          this.address = system.address || '';
          this.weather.location = system.address || '';
          
          // 실시간 댐 데이터 로드
          this.damData = {
            rwl: system.rwl || null,
            dambasrf: system.dambasrf || null,
            dqty: system.dqty || null
          };
        }
      } catch (e) {
        this.location_info = '';
        this.address = '';
        this.damData = {
          rwl: null,
          dambasrf: null,
          dqty: null
        };
      }
    },

    async loadMapImage() {
      try {
        console.log('loadMapImage ...start')
        const data = await getEventSetting();
        if (data && data.system_json) {
          const system = JSON.parse(data.system_json);

          this.mapImagePreview = system.map || null;
          
        }
      } catch (e) {
        this.mapImagePreview = null;
      }
    },
    // selectStatusButton(buttonType) {
    //   this.selectedStatusButton = buttonType;
    //   
    //   // 버튼 타입을 경보 레벨로 매핑
    //   const levelMapping = {
    //     'safe': 1,
    //     'attention': 2,
    //     'caution': 3,
    //     'check': 4,
    //     'prepare': 5
    //   };
    //   
    //   const targetLevel = levelMapping[buttonType];
    //   
    //   // 해당 레벨의 가장 최신 경보 찾기
    //   const latestAlert = this.alertHistory.find(alert => Number(alert.level) === targetLevel);
    //   
    //   if (latestAlert) {
    //     this.latestAlertInfo = {
    //       level: this.getLevelText(latestAlert.level),
    //       maxTemp: latestAlert.maxTemp,
    //       minTemp: latestAlert.minTemp,
    //       time: latestAlert.time
    //     };
    //   } else {
    //     // 해당 레벨의 경보가 없으면 전체에서 가장 최신 경보 표시
    //     if (this.alertHistory.length > 0) {
    //       const latest = this.alertHistory[0];
    //       this.latestAlertInfo = {
    //         level: this.getLevelText(latest.level),
    //         maxTemp: latest.maxTemp,
    //         minTemp: latest.minTemp,
    //         time: latest.time
    //       };
    //     } else {
    //       this.latestAlertInfo = null;
    //     }
    //   }
    // },
    getStatusButtonText(buttonType) {
      switch (buttonType) {
        case 'safe':
          return '안전';
        case 'attention':
          return '관심';
        case 'caution':
          return '주의';
        case 'check':
          return '점검';
        case 'prepare':
          return '대비';
        default:
          return '';
      }
    }
  },
};
</script>

<style lang="scss" scoped>
.dashboard-2by2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 16px;
  height: calc(100vh - 32px);
  background: #222736;
  padding: 16px;
  overflow: hidden;
}

.cell {
  background: #2a3042;
  border: 1px solid #2a3042;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  padding: 0;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.cell-topleft {
  grid-column: 1;
  grid-row: 1;
  display: flex;
  flex-direction: column;
}

.cell-topright {
  grid-column: 2;
  grid-row: 1;
  display: flex;
  flex-direction: column;
}

.cell-bottomleft {
  grid-column: 1;
  grid-row: 2;
  display: flex;
  flex-direction: column;
}

.cell-bottomright {
  grid-column: 2;
  grid-row: 2;
  display: flex;
  flex-direction: column;
}

.topleft-inner-row {
  display: flex;
  flex: 1;
  height: 100%;
  gap: 0;
}

.topleft-inner-left {
  flex: 4;
  border-right: 2px solid #555;
  border-radius: 8px 0 0 8px;
  background: transparent;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.topleft-inner-right {
  flex: 6;
  border-radius: 0 8px 8px 0;
  background: transparent;
  min-width: 0;
  min-height: 0;
}

.bottomleft-inner-col {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.bottomleft-inner-top {
  flex: 1;
  border-bottom: 2px solid #555;
  border-radius: 8px 8px 0 0;
  background: transparent;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  
  .box-title {
    background: #666;
    color: #fff;
    font-weight: bold;
    padding: 4px 12px;
    border-bottom: 1px solid #555;
    border-radius: 8px 8px 0 0;
    flex-shrink: 0;
    font-size: 14px;
    line-height: 1.2;
    display: block; // flex가 아닌 block으로 설정
  }
}

.bottomleft-inner-bottom {
  flex: 1;
  border-radius: 0 0 8px 8px;
  background: #2a3042;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.box-title {
  background: #666;
  color: #fff;
  font-weight: bold;
  padding: 4px 12px;
  border-bottom: 1px solid #555;
  border-radius: 8px 8px 0 0;
  flex-shrink: 0;
  font-size: 14px;
  line-height: 1.2;
  
  // 시계열 온도 데이터 제목은 더 작게
  &.chart-title {
    padding: 2px 8px;
    font-size: 12px;
  }
}

.video-container {
  flex: 1;
  position: relative;
  background: #000;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-container .vue-aspect-ratio {
  width: auto;
  height: 80vw;
  max-width: 100%;
  max-height: 100%;
  aspect-ratio: 4 / 3;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.video-container .video-card {
  width: 100%;
  height: 100%;
}

// PTZ 제어 관련 스타일
.box-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: bold;
  color: #fff;
  margin-bottom: 10px;
  
  .v-btn {
    background: #6c757d;  // secondary 색상
    color: white;
    font-size: 12px;
    padding: 4px 12px;
    height: 28px;
    margin-left: auto;  // 버튼을 오른쪽 끝으로 밀어냄
    
    &:hover {
      background: #5a6268;  // secondary hover 색상
    }
  }
}

// PTZ 다이얼로그 스타일
.ptz-dialog {
  .v-dialog__content {
    position: relative;
  }
}

.ptz-dialog-card {
  .draggable-header {
    cursor: move;
    background: #333;
    color: white;
    border-bottom: 1px solid #555;
    user-select: none;
    
    &:active {
      cursor: grabbing;
    }
  }
}

.ptz-dialog-container {
  display: flex;
  gap: 20px;
  min-height: 500px;

}

.ptz-left-panel {
  flex: 1;
  border-right: 1px solid #555;
  padding-right: 20px;
}

.ptz-right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.preset-section, .home-preset-section, .tour-section, .log-section {
  .section-title {
    font-size: 16px;
    font-weight: bold;
    color: white;
    margin-bottom: 15px;
    padding-bottom: 8px;
    border-bottom: 2px solid #ddd;
  }
}

.preset-controls {
  .preset-row {
    display: flex;
    align-items: center;
    margin-bottom: 15px;
    gap: 10px;
    
    .preset-label {
      min-width: 80px;
      font-weight: bold;
      color: white;
    }
    
    .preset-inputs {
      display: flex;
      gap: 8px;
      flex: 1;
      
      .v-text-field {
        flex: 1;
      }
    }
    
    .preset-buttons {
      display: flex;
      gap: 8px;
    }
  }
}

.home-preset-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px 0;
  
  .v-btn {
    width: 200px;
    height: 50px;
    font-size: 16px;
    font-weight: bold;
    border-radius: 12px;
    
    .v-icon {
      margin-right: 0px;
      font-size: 20px;
    }
  }
}

.tour-controls {
  .tour-speed, .step-write {
    margin-bottom: 15px;
  }
  
  .step-write {
    display: flex;
    align-items: center;
    gap: 10px;
    
    .v-btn {
      margin-top: 20px;
    }
  }
  
  .cycle-progress {
    .progress-title {
      font-weight: bold;
      color: white;
      margin-bottom: 8px;
    }
    
    .progress-bar {
      margin-bottom: 8px;
    }
    
    .progress-status {
      text-align: center;
      color: white;
      font-size: 14px;
      margin-bottom: 10px;
    }
    
    .tour-buttons {
      display: flex;
      gap: 10px;
      justify-content: center;
    }
  }
}

.log-section {
  .log-area {
    max-height: 200px;
    overflow: hidden;
    border: 1px solid #555;
    border-radius: 4px;
    
    .v-textarea {
      font-family: 'Courier New', monospace;
      font-size: 12px;
      height: 200px !important;
      max-height: 200px !important;
      overflow-y: auto !important;
      
      // 스크롤바 스타일링
      &::-webkit-scrollbar {
        width: 8px;
      }
      
      &::-webkit-scrollbar-track {
        background: #333;
        border-radius: 4px;
      }
      
      &::-webkit-scrollbar-thumb {
        background: #666;
        border-radius: 4px;
        
        &:hover {
          background: #888;
        }
      }
      
      // textarea 내부 스타일
      textarea {
        height: 200px !important;
        max-height: 200px !important;
        overflow-y: auto !important;
        resize: none !important;
      }
    }
  }
}

.video-header {
  margin-bottom: 10px;
  
  .video-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 16px;
    font-weight: bold;
    color: #fff;
    
    .v-btn {
      background: #6c757d;  // secondary 색상
      color: white;
      font-size: 12px;
      padding: 4px 12px;
      height: 28px;
      
      &:hover {
        background: #5a6268;  // secondary hover 색상
      }
    }
  }
}

.ptz-control-container {
  // 닫기 버튼 스타일
  .close-btn {
    background-color: #221c1c !important;
    border: 0px solid white !important;
    min-width: 32px !important;
    min-height: 32px !important;
    border-radius: 4px !important;
    font-weight: bold !important;
    font-size: 16px !important;
    
    &:hover {
      background-color: #cccccc !important;
    }
  }
  
  .connection-info {
    margin-bottom: 20px;
    padding: 15px;
    background: #545454;
    border-radius: 8px;
  }
  
  .ptz-buttons {
    text-align: center;
    margin-bottom: 20px;
    
    .ptz-row {
      display: flex;
      justify-content: center;
      margin: 15px 0;
      
      .v-btn {
        margin: 0 8px;
        
        &.v-btn--fab {
          width: 80px;
          height: 80px;
          position: relative;
          
          .ptz-label {
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            font-size: 12px;
            font-weight: bold;
            color: #d6d6d6;
            white-space: nowrap;
          }
        }
      }
      
      // 중간 행 (좌우 버튼)의 간격을 더 크게
      &:nth-child(2) {
        .v-btn {
          margin: 0 40px;  // 좌우 버튼 간격 더 증가
        }
      }
    }
  }
  
  .zoom-focus-controls {
    margin-bottom: 20px;
    
    .control-group {
      .control-label {
        font-weight: bold;
        margin-bottom: 10px;
        color: #333;
      }
      
      .control-buttons {
        display: flex;
        gap: 10px;
        
        .v-btn {
          flex: 1;
        }
      }
    }
  }
  
  .wiper-controls {
    .control-group {
      .control-label {
        font-weight: bold;
        margin-bottom: 10px;
        color: #333;
      }
      
      .control-buttons {
        display: flex;
        gap: 10px;
        
        .v-btn {
          flex: 1;
        }
      }
    }
  }
}

.time-layer {
  background: #3659e2;
  color: white;
  padding: 15px;
  text-align: center;
  border-radius: 8px 0 0 0;
  height: 15%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  
  
  .current-time {
    font-size: 20px;
    color: white;
  }
}

.site-info-layer {
  background: #2a3042;
  color: white;
  padding: 0px;
  border-top: 1px solid #2a3042;
  height: 25%;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  margin: 5px 0;
  .layer-title {
    background: #666;
    color: white;
    font-weight: bold;
    padding: 8px 10px;
    margin-bottom: 10px;
    text-align: left;
  }
  
  .site-info-content {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    
    .site-name {
      font-size: 16px;
      font-weight: bold;
      text-align: center;
      line-height: 1.3;
      word-break: break-all;
    }
  }
}

.dam-data-layer {
  background: #2a3042;
  color: white;
  padding: 0px;
  border-top: 1px solid #2a3042;
  height: 25%;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  margin: 5px 0;
  
  .layer-title {
    background: #666;
    color: white;
    font-weight: bold;
    padding: 8px 10px;
    margin-bottom: 10px;
    text-align: left;
  }
  
  .dam-data-content {
    flex: 1;
    display: flex;
    flex-direction: row;
    justify-content: space-around;
    align-items: center;
    padding: 0 10px;
    gap: 10px;
    
    .dam-data-item {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 8px 4px;
      
      .dam-data-label {
        font-size: 14px;
        color: #ccc;
        font-weight: normal;
        margin-bottom: 8px;
        text-align: center;
      }
      
      .dam-data-value {
        font-size: 18px;
        color: #fff;
        font-weight: bold;
        text-align: center;
      }
    }
  }
}

.leak-status-layer {
  background: #2a3042;
  color: white;
  padding: 0px;
  border-top: 1px solid #2a3042;
  border-radius: 0 0 0 8px;
  height: 30%;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  margin: 5px 0 !important;
  
  .layer-title {
    background: #666;
    color: white;
    font-weight: bold;
    padding: 8px 10px;
    margin-bottom: 10px;
    font-size: 14px;
    text-align: left;
  }
  
  .status-buttons {
    flex: 1;
    display: flex;
    gap: 8px;
    margin-top: -20px;
    padding: 0px 10px;
    align-items: center;
    justify-content: center;
    
    .status-button {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 8px 4px;
      border-radius: 6px;
      transition: all 0.3s ease;
      
      &.safe {
        background: transparent;
        border-color: transparent;
        
        &.active {
          background: #4caf50;
          border: 2px solid #fff;
          box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        }
      }
      
      &.attention {
        background: transparent;
        border-color: transparent;
        
        &.active {
          background: #2196f3;
          border: 2px solid #fff;
          box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        }
      }
      
      &.caution {
        background: transparent;
        border-color: transparent;
        
        &.active {
          background: #ff9800;
          border: 2px solid #fff;
          box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        }
      }
      
      &.check {
        background: transparent;
        border-color: transparent;
        
        &.active {
          background: #f44336;
          border: 2px solid #fff;
          box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        }
      }
      
      &.prepare {
        background: transparent;
        border-color: transparent;
        
        &.active {
          background: #e34d4d;
          border: 2px solid #fff;
          box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        }
      }
      
      .status-icon {
        font-size: 18px;
        margin-bottom: 4px;
      }
      
      .status-text {
        font-size: 12px;
        font-weight: bold;
        text-align: center;
      }
    }
  }
  .status-info {
    background: #333;
    border-radius: 0 0 8px 8px;
    padding: 10px;
    margin-top: 10px;
    .info-title {
      font-size: 14px;
      font-weight: bold;
      color: #fff;
      margin-bottom: 8px;
      text-align: left;
    }
    .info-content {
      display: flex;
      flex-direction: column;
      gap: 4px;
      .info-item {
        display: flex;
        justify-content: space-between;
        .label {
          color: #bbb;
          font-size: 12px;
        }
        .value {
          color: #fff;
          font-size: 14px;
          font-weight: bold;
        }
      }
    }
  }
}

.zone-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;

  th, td {
    padding: 8px;
    text-align: center;
    border-bottom: 1px solid #555;
  }

  th {
    background: #444;
    color: #fff;
    font-weight: bold;
    position: sticky;
    top: 0;
    z-index: 10;
  }

  tr {
    cursor: pointer;
    transition: background-color 0.3s, transform 0.2s, box-shadow 0.2s;
    user-select: none;

    &:hover {
      background-color: #444d67;
    }

    &.selected {
      background-color: #444d67;
    }
    
    &.clicking {
      background-color: #5a6578;
      transform: scale(0.98);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }

    td:first-child {
      background-color: #535e6c;
      font-weight: bold;
    }
  }

  .icon-chart, .icon-excel {
    cursor: pointer;
    font-size: 1.2em;
    transition: transform 0.2s;

    &:hover {
      transform: scale(1.2);
    }
  }
}

.chart-container {
  flex: 1;
  min-height: 0;
  padding: 5px;
  background: #2a3042;
  border-radius: 0 0 8px 8px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: stretch;
  margin-top: 0;
  height: 100%;
  overflow: hidden;

  .trend-chart {
    width: 100%;
    height: 100%;
    min-height: 150px;
    background: #2a3042;
  }

  .no-data {
    color: #888;
    font-size: 1.2em;
  }
}

.no-data {
  color: #bbb;
  text-align: center;
  padding: 30px 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
  font-size: 14px;
}

.no-camera {
  color: #666;
  font-size: 14px;
  text-align: center;
  padding: 20px;
}

.current-time {
  font-size: 24px;
  color: #ccc;
  line-height: 1.2;
  text-align: left;
  display: block;
}

.gauge-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}

.gauge-meter {
  width: 100%;
  height: 180px;
  min-width: 180px;
  min-height: 180px;
}

.bottom-box {
  flex: 1;
  padding: 20px;
  background: #333;
  border-radius: 0 0 8px 8px;
}

.table-title {
  background: #666;
  color: #fff;
  font-weight: bold;
  padding: 8px 16px;
  border-bottom: 2px solid #555;
  border-radius: 8px 8px 0 0;
  flex-shrink: 0;
}

.alert-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;

  .table-header {
    display: flex;
    background: #222;
    font-weight: bold;
    .header-cell {
      flex: 1;
      text-align: center;
      color: #fff;
      padding: 8px 0;
    }
  }
  .table-body {
    max-height: 200px;
    overflow-y: auto;
    .table-row {
      display: flex;
      align-items: center;
      border-bottom: 1px solid #333;
      transition: background 0.2s;
      &:hover {
        background: #333;
      }
      .table-cell {
        flex: 1;
        text-align: center;
        color: #eee;
        padding: 6px 0;
        .level-icon {
          margin-right: 4px;
        }
      }
      &.level-4 { background: rgba(255,75,75,0.15);}
      &.level-3 { background: rgba(255,138,0,0.10);}
      &.level-2 { background: rgba(255,184,0,0.10);}
      &.level-1 { background: rgba(75,123,229,0.10);}
    }
  }
}

@media (max-width: 900px) {
  .dashboard-2by2 {
    display: flex;
    flex-direction: column;
    padding: 4px;
    gap: 8px;
    height: auto;
  }
  
  .cell {
    min-width: 0;
    width: 100%;
    height: 50vh;
  }
}

// 기존 스타일은 새로운 3개 레이어 구조로 대체됨

.map-image-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
  background: #333;
  border-radius: 0 8px 8px 0;
  margin-left: 3px;
  .map-preview-image {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #222;
    border-radius: 0 8px 8px 0;

  }
}

.no-map-image {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #333;
  border-radius: 0 8px 8px 0;

  .no-map-text {
    color: #888;
    font-size: 16px;
    text-align: center;
  }
}

// 파노라마 다이얼로그 스타일
.panorama-dialog {
  .panorama-dialog-card {
    background: #1e1e1e;
    color: white;
    
    .headline {
      background: #2a3042;
      color: white;
      padding: 16px 24px;
      border-bottom: 1px solid #444;
      
      .close-btn {
        min-width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #f44336;
        color: white;
        
        &:hover {
          background: #d32f2f;
        }
      }
    }
    
    .panorama-container {
      padding: 20px;
      
      .panorama-image-container {
        margin-bottom: 20px;
        text-align: center;
        background: #2a2a2a;
        border-radius: 8px;
        padding: 10px;
        
        .panorama-image {
          border-radius: 8px;
          max-height: 500px;
          object-fit: contain;
        }
        
        .no-image {
          height: 300px;
          display: flex;
          align-items: center;
          justify-content: center;
          
          .no-image-text {
            color: #888;
            font-size: 18px;
          }
        }
      }
      
      .panorama-controls {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 20px;
        padding: 20px;
        background: #2a3042;
        border-radius: 8px;
        
        .v-btn {
          min-width: 100px;
          height: 40px;
          
          &.v-btn--disabled {
            opacity: 0.5;
          }
        }
        
        .panorama-info {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 5px;
          color: white;
          font-weight: bold;
          
          .panorama-date {
            font-size: 14px;
            color: #ccc;
            font-weight: normal;
          }
        }
      }
    }
  }
}

// 경보 알림 팝업 레이어 스타일 (화면 가운데)
.alert-popup-container {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 500px;
  max-width: calc(100vw - 40px);
  max-height: calc(100vh - 40px);
  background: #2a3042;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  z-index: 1000;
  border: 2px solid #ff4d4f;
  
  .alert-popup-header {
    padding: 16px 20px;
    border-bottom: 2px solid #444;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #1e2130;
    border-radius: 8px 8px 0 0;
    
    .alert-popup-title {
      font-size: 18px;
      font-weight: bold;
      color: #ff4d4f;
    }
    
    .close-popup-btn {
      min-width: 32px;
      width: 32px;
      height: 32px;
      color: #fff;
      
      &:hover {
        background: rgba(255, 255, 255, 0.1);
      }
    }
  }
  
  .alert-popup-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    max-height: calc(100vh - 200px);
    
    .alert-list {
      .alert-item {
        padding: 12px;
        margin-bottom: 10px;
        background: #1e2130;
        border-radius: 4px;
        border-left: 4px solid #ff4d4f;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .alert-level {
          font-size: 15px;
          font-weight: bold;
          color: #ff4d4f;
          margin-bottom: 6px;
        }
        
        .alert-zone {
          font-size: 13px;
          color: #ccc;
          margin-bottom: 4px;
        }
        
        .alert-time {
          font-size: 12px;
          color: #999;
        }
      }
    }
  }
  
  .alert-popup-footer {
    padding: 16px 20px;
    border-top: 2px solid #444;
    background: #1e2130;
    border-radius: 0 0 8px 8px;
    
    .v-btn {
      height: 40px;
      font-size: 14px;
      font-weight: bold;
    }
  }
}
</style>
