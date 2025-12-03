<template lang="pug">
.alert-status-container
  .left-sidebar
    .time-layer
      .location-info {{ location_info }}
      .current-time {{ currentTime }}
    .alert-history-layer
      .layer-title
        | 경보 이력
        v-btn(
          icon
          :color="autoRefreshAlertHistory ? 'primary' : 'grey'"
          @click="toggleAlertHistoryRefresh"
          class="ml-2"
          small
        )
          v-icon {{ icons.mdiRefresh }}
      .roi-filter-section
        v-select(
          v-model="scenarioFilter"
          :items="scenarioOptions"
          label="시나리오 필터"
          prepend-inner-icon="mdi-filter"
          dense
          outlined
          hide-details
          @change="applyScenarioFilter()"
        )
      .alert-history-content
        .alert-history-table
          .table-row(
            v-for="(alert, index) in displayAlertHistory" 
            :key="alert.id"
            :class="getAlertRowClass(alert, index)"
            @click="selectAlert(index)"
          )
            .roi-number
              .roi-label ROI {{ getRoiDisplayName(alert) }}
            .data-table
              .table-item
                .item-label 최고온도
                .item-value {{ alert.maxTemp }}°C
              .table-item
                .item-label 최소온도
                .item-value {{ alert.minTemp }}°C
              .table-item
                .item-label 평균온도
                .item-value {{ alert.avgTemp }}°C
              .table-item
                .item-label 경보단계
                .item-value {{ getLevelText(alert.level) }}
              .table-item
                .item-label 시나리오
                .item-value {{ getScenarioDisplayName(alert) }}
              .table-item
                .item-label 측정시간
                .item-value {{ alert.time }}

  .center-content
    .top-image-box
      .box-title 열화상 이미지 분석 결과({{ lastEventTime }})
      .image-container
        img.thermal-image(
          v-if="thermalImageSrc"
          :src="thermalImageSrc"
          alt="열화상 이미지"
          @load="onThermalImageLoad"
          @click="onPanoramaImageClick"
        )
        .thermal-image-placeholder(v-else)
          .placeholder-text 열화상 이미지
          .placeholder-subtext
    .bottom-image-box
      .box-title 실화상 이미지
      .image-container
        img.visual-image(
          v-if="visualImageSrc"
          :src="visualImageSrc"
          alt="실화상 이미지"
        )
        .visual-image-placeholder(v-else)
          .placeholder-text 실화상 이미지
          .placeholder-subtext
  .right-sidebar
    .gauge-box
      .box-title 현재 경보단계
      .gauge-container
        .gauge-meter(ref="gaugeChart")
      .scenario-info(v-if="currentScenario")
        .scenario-label 시나리오
        .scenario-value {{ currentScenario }}
    
    .chart-box
      .box-title 최근 7일 경보 발령 수
      .chart-container
        div(ref="alertChart" style="width:100%;height:180px;min-width:180px;min-height:180px;")
    
    .history-box
      .box-title 경보 발생(누수) 날짜 및 시간 이력
      .alert-table
        .table-header
          .header-cell 경보레벨
          .header-cell 발생일자
        .table-body
          .table-row(v-for="alert in displayAlertHistory" :key="alert.id")
            .table-cell {{ getLevelText(alert.level) }}
            .table-cell {{ alert.time }}

  // ROI 데이터 팝업 다이얼로그
  v-dialog(
    v-model="showRoiDataDialog"
    max-width="1000px"
    persistent
  )
    v-card.roi-dialog-card
      v-card-title.roi-dialog-title
        .title-content
          .main-title ROI {{ selectedRoiNumber }} 시계열 데이터
          .sub-title 열화상 이미지 분석 결과
        v-spacer
        v-btn.close-btn(icon @click="closeRoiDataDialog")
          v-icon mdi-close
      v-card-text.roi-dialog-content
        .roi-data-container
          .temperature-summary(v-if="roiTimeSeriesData.length > 0")
            .summary-item
              .item-label 최대온도
              .item-value {{ getRoiMaxTemp(roiTemperatureStats) }}°C
            .summary-item
              .item-label 최소온도
              .item-value {{ getRoiMinTemp(roiTemperatureStats) }}°C
            .summary-item
              .item-label 평균온도
              .item-value {{ roiTemperatureStats.avgTemp }}°C
          .chart-container(v-if="roiTimeSeriesData.length > 0")
            div(ref="roiTimeSeriesChart" style="width:100%;height:400px;")
          .no-data(v-else)
            .no-data-text 데이터가 없습니다.
      v-card-actions.roi-dialog-actions
        v-spacer
        v-btn.close-action-btn(color="primary" @click="closeRoiDataDialog") 닫기
</template>
  
<script>
import { 
  mdiRefresh
} from '@mdi/js';
import { getCameras, getCameraSettings } from '@/api/cameras.api';
import { getAlerts, getRecentAlertCounts } from '@/api/alerts.api';
import { getEventSetting } from '@/api/eventSetting.api';
import { getRoiTimeSeriesData } from '@/api/statistic.api';
import VideoCard from '@/components/camera-card.vue';
import socket from '@/mixins/socket';
import * as echarts from 'echarts';

export default {
  name: 'NotificationStatus',

  components: {
    VideoCard
  },

  mixins: [socket],

  data: () => ({
    icons: {
      mdiRefresh
    },
    loading: false,
    cameras: [],
    selectedCameraIndex: null,
    videoKey: 0,
    currentAlertLevel: '대기',
    alertChart: null,
    gaugeChart: null,
    alertCount: 4,
    alertHistory: [],
    env: process.env.NODE_ENV,
    alertRefreshTimer: null,
    autoRefreshAlertHistory: false,
    currentTime: '',
    timeInterval: null,
    location_info: '수자원공사 섬진강댐',
    thermalImageSrc: null,
    visualImageSrc: null,
    selectedAlertIndex: 0,
    zoneBoxes: [],
    selectedAlertZoneType: null,
    alertBoxes: [],
    selectedAlertBoxId: null,
    thermalImageSize: { width: 0, height: 0 },
    currentScenario: null,
    siteDetails: {
      maxTemp: '46.24',
      minTemp: '19.73',
      avgTemp: '41.31',
      alertLevel: '4',
      measurementTime: '2025-07-09 15:40:00'
    },
    // ROI 데이터 팝업 관련
    showRoiDataDialog: false,
    selectedRoiNumber: null,
    roiTimeSeriesData: [],
    roiTimeSeriesChart: null,
    roiTemperatureStats: {
      maxTemp: 0,
      minTemp: 0,
      avgTemp: 0
    },
    // 시나리오 필터 관련
    scenarioFilter: null,
    scenarioOptions: [
      { text: '전체', value: null },
      { text: '시나리오1', value: 1 },
      { text: '시나리오2', value: 2 }
    ],
    filteredAlertHistory: []
  }),

  computed: {
    selectedCamera() {
      return this.selectedCameraIndex !== null && this.cameras.length > 0 
        ? this.cameras[this.selectedCameraIndex] 
        : null;
    },
    
    // 필터가 적용되었는지 여부에 따라 표시할 경보 리스트 반환
    displayAlertHistory() {
      // 필터가 적용된 경우 (scenarioFilter가 null이 아닌 경우)
      if (this.scenarioFilter !== null && this.scenarioFilter !== undefined) {
        // 필터링된 결과만 반환 (빈 배열이어도 반환)
        return this.filteredAlertHistory;
      }
      // 필터가 적용되지 않은 경우 원본 리스트 반환
      return this.alertHistory;
    },
    
    lastEventTime() {
      if (this.alertHistory.length === 0) {
        return this.currentTime;
      }
      
      // 선택된 경보가 있으면 해당 경보의 시간, 없으면 마지막 이벤트의 시간 반환
      if (this.selectedAlertIndex >= 0 && this.selectedAlertIndex < this.alertHistory.length) {
        const selectedAlert = this.alertHistory[this.selectedAlertIndex];
        return selectedAlert.time || this.currentTime;
      } else {
        const lastEvent = this.alertHistory[this.alertHistory.length - 1];
        return lastEvent.time || this.currentTime;
      }
    }
  },
  
  filters: {
    toFixed(value, decimals) {
      if (isNaN(value)) return '0.00';
      return Number(value).toFixed(decimals);
    }
  },

  watch: {
    cameras: {
      immediate: true,
      handler(newCameras) {
        console.log('Cameras changed:', {
          length: newCameras.length,
          cameras: newCameras
        });
      }
    }
  },

  async created() {
    console.log('Component created');
    if (this.$sidebar) this.$sidebar.close();
    this.updateTime();
    this.timeInterval = setInterval(this.updateTime, 1000);
    await this.initializeData();
    await this.loadAlertHistory();
  },

  mounted() {
    console.log('Component mounted, cameras:', this.cameras);
    this.$socket.client.on('connect', this.handleSocketConnect);
    this.$nextTick(() => {
      this.initAlertChart();
      this.initGaugeChart();
      this.loadAlertChart();
    });
    
    // 윈도우 resize 이벤트 리스너 추가
    window.addEventListener('resize', this.handleWindowResize);
    // 경보 이력 자동 갱신 시작 (10초마다)
    this.startAlertRefresh();
  },

  beforeDestroy() {
    if (this.timeInterval) {
      clearInterval(this.timeInterval);
    }
    if (this.selectedCamera?.name) {
      this.$refs[this.selectedCamera.name]?.[0]?.destroy();
    }
    if (this.alertChart) {
      this.alertChart.dispose();
    }
    if (this.gaugeChart) {
      this.gaugeChart.dispose();
    }
    window.removeEventListener('resize', this.handleChartResize);
    window.removeEventListener('resize', this.handleWindowResize);
    this.$socket.client.off('connect', this.handleSocketConnect);
    this.stopAlertRefresh();
  },

  methods: {
    updateTime() {
      // 한국 시간으로 변환 (UTC+9)
      const now = new Date();
      const koreaTime = new Date(now.getTime() + (9 * 60 * 60 * 1000)); // UTC+9
      
      const year = koreaTime.getUTCFullYear();
      const month = koreaTime.getUTCMonth() + 1;
      const day = koreaTime.getUTCDate();
      const hours = koreaTime.getUTCHours();
      const minutes = String(koreaTime.getUTCMinutes()).padStart(2, '0');
      const seconds = String(koreaTime.getUTCSeconds()).padStart(2, '0');
      
      // 오전/오후 구분
      const period = hours < 12 ? '오전' : '오후';
      const displayHours = hours < 12 ? hours : (hours === 12 ? 12 : hours - 12);
      const displayHoursStr = String(displayHours).padStart(2, '0');
      
      this.currentTime = `${year}/${month}/${day} ${period} ${displayHoursStr}:${minutes}:${seconds}`;
    },
    // roiTemperatureStats.minTemp와 roiTemperatureStats.maxTemp 중 작은 값을 최소온도로 반환
    getRoiMinTemp(stats) {
      if (!stats) return '--';
      if (stats.minTemp == null && stats.maxTemp == null) {
        return '--';
      }
      if (stats.minTemp == null) return stats.maxTemp;
      if (stats.maxTemp == null) return stats.minTemp;
      return Math.min(stats.minTemp, stats.maxTemp);
    },
    // roiTemperatureStats.minTemp와 roiTemperatureStats.maxTemp 중 큰 값을 최대온도로 반환
    getRoiMaxTemp(stats) {
      if (!stats) return '--';
      if (stats.minTemp == null && stats.maxTemp == null) {
        return '--';
      }
      if (stats.minTemp == null) return stats.maxTemp;
      if (stats.maxTemp == null) return stats.minTemp;
      return Math.max(stats.minTemp, stats.maxTemp);
    },
    
    async initializeData() {
      try {
        await this.fetchCameras();
        await this.loadLocationInfo();
        if (this.cameras.length > 0) {
          this.selectCamera(0);
        }
      } catch (error) {
        console.error('Error initializing data:', error);
      }
    },

    async fetchCameras() {
      console.log('Starting fetchCameras');
      this.loading = true;
      
      try {
        const response = await getCameras();
        console.log('getCameras response:', response);

        if (!response?.data?.result) {
          console.warn('No camera data in response');
          this.cameras = [];
          return;
        }

        const rawCameras = response.data.result;
        console.log('Raw cameras:', rawCameras);

        if (!Array.isArray(rawCameras)) {
          console.warn('Camera data is not an array');
          this.cameras = [];
          return;
        }

        const processedCameras = [];
        for (const camera of rawCameras) {
          try {
            if (!camera?.name) {
              console.warn('Skipping camera without name:', camera);
              continue;
            }

            console.log('Processing camera:', camera.name);
            
            const settingsResponse = await getCameraSettings(camera.name);
            console.log('Camera settings response:', settingsResponse);
            
            const processedCamera = {
              ...camera,
              settings: settingsResponse?.data || {}
            };
            
            processedCameras.push(processedCamera);
            console.log('Added processed camera:', processedCamera);
          } catch (err) {
            console.error(`Error processing camera ${camera?.name || 'unknown'}:`, err);
          }
        }

        console.log('Setting cameras array:', processedCameras);
        this.cameras = processedCameras;
        
      } catch (error) {
        console.error('Error in fetchCameras:', error);
        this.$toast.error('카메라 목록을 불러오는데 실패했습니다.');
        this.cameras = [];
      } finally {
        this.loading = false;
        console.log('fetchCameras completed. Current cameras:', this.cameras);
      }
    },

    async loadLocationInfo() {
      try {
        console.log('Loading location info...');
        const data = await getEventSetting();
        console.log('Event setting response:', data);
        
        if (data && data.system_json) {
          const system = JSON.parse(data.system_json);
          this.location_info = system.location_info || '수자원공사 섬진강댐';
          console.log('Location info loaded:', this.location_info);
        } else {
          console.log('No system_json found, using default location info');
          this.location_info = '수자원공사 섬진강댐';
        }
      } catch (error) {
        console.error('Error loading location info:', error);
        this.location_info = '수자원공사 섬진강댐';
      }
    },

    selectCamera(index) {
      if (this.selectedCameraIndex === index) {
        return;
      }
      
      // 이전 선택된 카메라의 VideoCard 인스턴스 정리
      if (this.selectedCamera) {
        const prevRef = this.$refs[`main-${this.selectedCamera.name}`];
        if (prevRef && prevRef[0]) {
          prevRef[0].destroy();
        }
      }

      this.selectedCameraIndex = index;
      this.videoKey++; // 비디오 키 업데이트로 VideoCard 재생성

      // 새로 선택된 카메라의 VideoCard 초기화
      this.$nextTick(() => {
        const newRef = this.$refs[`main-${this.selectedCamera.name}`];
        if (newRef && newRef[0]) {
          newRef[0].initialize();
        }
      });
    },

    async refreshCameras() {
      await this.fetchCameras();
    },

    handleSocketConnect() {
      if (this.selectedCamera?.name && this.$refs[this.selectedCamera.name]?.[0]) {
        this.$refs[this.selectedCamera.name][0].refreshStream(true);
      }
    },

    formatRtspUrl(camera) {
      try {
        if (!camera?.videoConfig?.source) return 'URL 없음';
        const source = camera.videoConfig.source.replace(/\u00A0/g, ' ');
        const parts = source.split('-i ');
        return parts.length > 1 ? parts[1] : 'URL 없음';
      } catch (error) {
        console.error('Error formatting RTSP URL:', error);
        return 'URL 없음';
      }
    },

    initAlertChart() {
      const chartDom = this.$refs.alertChart;
      if (!chartDom) return;
      if (this.alertChart) {
        this.alertChart.dispose();
      }
      this.alertChart = echarts.init(chartDom);

      // 빈 데이터로만 초기화
      this.alertChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: '#ffffff' } }, axisLabel: { color: '#ffffff' } },
        yAxis: { type: 'value', axisLine: { lineStyle: { color: '#ffffff' } }, axisLabel: { color: '#ffffff' }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } } },
        series: [{
          name: '경보건수',
          type: 'bar',
          data: [],
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#83bff6' },
              { offset: 0.5, color: '#188df0' },
              { offset: 1, color: '#188df0' }
            ])
          }
        }]
      });
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

    handleChartResize() {
      if (this.alertChart) {
        this.alertChart.resize();
      }
      if (this.gaugeChart) {
        this.gaugeChart.resize();
      }
    },

    handleWindowResize() {
      // 윈도우 크기 변경 시 alert 박스 위치 재계산
      this.$nextTick(() => {
        this.updateAlertBoxes();
      });
    },

    async loadAlertHistory() {
      try {
        // 1페이지 20개만 요청 (모든 경보 이력 조회를 위해 includeClosed=true 추가)
        const response = await getAlerts('?page=1&pageSize=20&includeClosed=true');
        this.alertHistory = response.data.result.map(alert => {
          let minTemp = '-';
          let maxTemp = '-';
          let avgTemp = '-';
          let info = {};
          
          // alert_info_json 안전하게 파싱
          try {
            if (alert.alert_info_json && typeof alert.alert_info_json === 'string') {
              // JSON 문자열이 잘린 경우를 대비하여 안전하게 파싱
              const jsonStr = alert.alert_info_json.trim();
              if (jsonStr.endsWith('}') || jsonStr.endsWith(']')) {
                info = JSON.parse(jsonStr);
              } else {
                // JSON이 잘린 경우, 마지막 완전한 객체나 배열을 찾아서 파싱 시도
                const lastCompleteJson = this.findLastCompleteJson(jsonStr);
                if (lastCompleteJson) {
                  info = JSON.parse(lastCompleteJson);
                } else {
                  console.warn('JSON이 잘려있어 파싱할 수 없습니다:', jsonStr.substring(0, 100) + '...');
                  info = {};
                }
              }
            } else if (alert.alert_info_json && typeof alert.alert_info_json === 'object') {
              info = alert.alert_info_json;
            }
          } catch (e) {
            console.error('alert_info_json 파싱 오류:', e, '원본 데이터:', alert.alert_info_json);
            info = {};
          }
          
          try {
            // temperature_stats에서 온도 데이터 추출
            if (info.temperature_stats) {
              minTemp = (typeof info.temperature_stats.min === 'number') ? info.temperature_stats.min.toFixed(1) : '-';
              maxTemp = (typeof info.temperature_stats.max === 'number') ? info.temperature_stats.max.toFixed(1) : '-';
              avgTemp = (typeof info.temperature_stats.average === 'number') ? info.temperature_stats.average.toFixed(1) : '-';
            } else {
              // 기존 방식으로 fallback
              minTemp = (typeof info.min_roi_value === 'number') ? info.min_roi_value.toFixed(1) : '-';
              maxTemp = (typeof info.max_roi_value === 'number') ? info.max_roi_value.toFixed(1) : '-';
              avgTemp = '-';
            }
          } catch (e) {
            console.error('온도 데이터 파싱 오류:', e);
          }
          
          return {
            id: alert.id,
            time: this.formatDate(alert.alert_accur_time),
            originalTime: alert.alert_accur_time, // 원본 날짜 데이터 보존
            type: alert.alert_type,
            level: alert.alert_level,
            maxTemp,
            minTemp,
            avgTemp,
            roiNumber: info.zone_type,
            snapshotImages: alert.snapshotImages,
            alert_info_json: alert.alert_info_json
          }
        });

        // 현재 선택된 경보의 ID 저장 (자동 갱신 시 선택 유지용)
        let selectedAlertId = null;
        if (this.selectedAlertIndex >= 0 && this.selectedAlertIndex < this.displayAlertHistory.length) {
          selectedAlertId = this.displayAlertHistory[this.selectedAlertIndex]?.id;
        }

        // 시나리오 필터 적용
        this.applyScenarioFilter();

        // 자동 갱신 시 선택된 경보 유지
        if (selectedAlertId && this.displayAlertHistory.length > 0) {
          // 같은 ID를 가진 경보 찾기
          const foundIndex = this.displayAlertHistory.findIndex(alert => alert.id === selectedAlertId);
          if (foundIndex >= 0) {
            this.selectedAlertIndex = foundIndex;
          } else {
            // 선택된 경보가 없어진 경우 최신 경보 선택
            this.selectedAlertIndex = 0;
          }
        } else if (this.displayAlertHistory.length > 0) {
          // 처음 로드하거나 선택된 경보가 없는 경우 최신 경보 선택
          this.selectedAlertIndex = 0;
        }

        // 최신 경보의 snapshotImages 파싱하여 이미지 분류
        // 필터가 적용된 경우 filteredAlertHistory만 사용, 그렇지 않으면 alertHistory 사용
        if (this.displayAlertHistory.length > 0 && this.selectedAlertIndex >= 0 && this.selectedAlertIndex < this.displayAlertHistory.length) {
          this.parseSnapshotImages(this.displayAlertHistory[this.selectedAlertIndex].snapshotImages);
          this.updateAlertBoxes();
          this.updateCurrentScenario(this.displayAlertHistory[this.selectedAlertIndex]);
        }

        // 최신 경보단계로 gaugeChart 값 반영 (한글 문구로)
        if (this.displayAlertHistory.length > 0) {
          this.alertCount = Number(this.displayAlertHistory[0].level) || 0;
          const levelLabel = this.getLevelText(this.displayAlertHistory[0].level);
          if (this.gaugeChart) {
            this.gaugeChart.setOption({
              series: [{
                data: [{
                  value: this.alertCount,
                  name: levelLabel
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

    getTypeText(type) {
      const types = {
        'A001': '누수 감지',
        'A002': '움직임 감지',
        'A003': '얼굴 인식',
        'A004': '차량 감지'
      };
      return types[type] || type;
    },

    getLevelText(level) {
      const levels = {
        '1': '주의',
        '2': '경고',
        '3': '위험',
        '4': '심각',
        '5': '비상'
      };
      return levels[level] || level;
    },

    async loadAlertChart() {
      try {
        const response = await getRecentAlertCounts();
        const data = response.data.result;

        // 최근 7일 날짜 배열 생성 (오늘 포함) - 한국 시간 기준
        const today = new Date();
        const koreaToday = new Date(today.getTime() + (9 * 60 * 60 * 1000)); // UTC+9
        const categories = [];
        for (let i = 6; i >= 0; i--) {
          const d = new Date(koreaToday);
          d.setUTCDate(koreaToday.getUTCDate() - i);
          const year = d.getUTCFullYear();
          const month = String(d.getUTCMonth() + 1).padStart(2, '0');
          const day = String(d.getUTCDate()).padStart(2, '0');
          categories.push(`${year}-${month}-${day}`);
        }
        const dataMap = Object.fromEntries(data.map(d => [d.date, d.count]));
        const counts = categories.map(date => dataMap[date] || 0);

        if (this.alertChart) {
          this.alertChart.setOption({
            xAxis: { type: 'category', data: categories },
            yAxis: { type: 'value' },
            legend: { show: false },
            tooltip: { trigger: 'axis' },
            series: [{
              name: '경보건수',
              type: 'bar',
              data: counts,
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: '#83bff6' },
                  { offset: 0.5, color: '#188df0' },
                  { offset: 1, color: '#188df0' }
                ])
              }
            }]
          }, true); // notMerge: true
        }
      } catch (e) {
        console.error('최근 7일 경보 차트 데이터 조회 실패:', e);
      }
    },

    startAlertRefresh() {
      this.stopAlertRefresh();
      this.alertRefreshTimer = setInterval(() => {
        this.loadAlertHistory();
      }, 10000); // 10초마다 자동 갱신
    },

    stopAlertRefresh() {
      if (this.alertRefreshTimer) {
        clearInterval(this.alertRefreshTimer);
        this.alertRefreshTimer = null;
      }
    },

    getAlertRowClass(alert, index) {
      return {
        'alert-level-3': Number(alert.level) >= 3,
        'alert-level-4': Number(alert.level) >= 4,
        'alert-level-5': Number(alert.level) >= 5,
        'selected-alert': this.selectedAlertIndex === index
      };
    },

    selectAlert(index) {
      if (index >= 0 && index < this.displayAlertHistory.length) {
        this.selectedAlertIndex = index;
        const selectedAlert = this.displayAlertHistory[index];
        console.log('Selected alert:', selectedAlert);
        
        // temperature_stats 정보 출력
        try {
          const alertInfo = selectedAlert.alert_info_json ? JSON.parse(selectedAlert.alert_info_json) : {};
          if (alertInfo.temperature_stats) {
            console.log('Temperature stats:', {
              min: alertInfo.temperature_stats.min,
              max: alertInfo.temperature_stats.max,
              average: alertInfo.temperature_stats.average,
              difference: alertInfo.temperature_stats.difference
            });
          }
        } catch (e) {
          console.error('Error parsing temperature stats:', e);
        }
        
        this.parseSnapshotImages(selectedAlert.snapshotImages);
        this.updateAlertBoxes();
        
        // 시나리오 정보 업데이트
        this.updateCurrentScenario(selectedAlert);
        
        // 선택된 경보의 level로 게이지 업데이트
        const selectedLevel = Number(selectedAlert.level) || 0;
        const levelLabel = this.getLevelText(selectedAlert.level);
        this.alertCount = selectedLevel;
        if (this.gaugeChart) {
          this.gaugeChart.setOption({
            series: [{
              data: [{
                value: selectedLevel,
                name: levelLabel
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
      }
    },

    updateCurrentScenario(alert) {
      try {
        // alert_type에 따라 시나리오 결정
        const alertType = alert.type;
        
        if (alertType === 'S001' || alertType === 1 || alertType === '1') {
          this.currentScenario = '시나리오1';
          return;
        } else if (alertType === 'S002' || alertType === 2 || alertType === '2') {
          this.currentScenario = '시나리오2';
          return;
        }
        
        // alert_info_json에서 scenario 정보 확인
        let alertInfo = {};
        try {
          if (alert.alert_info_json && typeof alert.alert_info_json === 'string') {
            const jsonStr = alert.alert_info_json.trim();
            if (jsonStr.endsWith('}') || jsonStr.endsWith(']')) {
              alertInfo = JSON.parse(jsonStr);
            } else {
              const lastCompleteJson = this.findLastCompleteJson(jsonStr);
              if (lastCompleteJson) {
                alertInfo = JSON.parse(lastCompleteJson);
              }
            }
          } else if (alert.alert_info_json && typeof alert.alert_info_json === 'object') {
            alertInfo = alert.alert_info_json;
          }
        } catch (e) {
          console.error('updateCurrentScenario에서 alert_info_json 파싱 오류:', e);
        }
        
        // scenario 필드에서 확인
        if (alertInfo.scenario === 'scenario1') {
          this.currentScenario = '시나리오1';
        } else if (alertInfo.scenario === 'scenario2') {
          this.currentScenario = '시나리오2';
        } else {
          this.currentScenario = null;
        }
      } catch (error) {
        console.error('Error updating current scenario:', error);
        this.currentScenario = null;
      }
    },

    parseSnapshotImages(snapshotImagesJson) {
      try {
        if (!snapshotImagesJson) {
          console.log('No snapshot images data');
          this.thermalImageSrc = null;
          this.visualImageSrc = null;
          return;
        }

        let snapshotImages = [];
        
        // snapshotImagesJson 안전하게 파싱
        try {
          if (typeof snapshotImagesJson === 'string') {
            // JSON 문자열이 잘린 경우를 대비하여 안전하게 파싱
            const jsonStr = snapshotImagesJson.trim();
            if (jsonStr.endsWith('}') || jsonStr.endsWith(']')) {
              snapshotImages = JSON.parse(jsonStr);
            } else {
              // JSON이 잘린 경우, 마지막 완전한 객체나 배열을 찾아서 파싱 시도
              const lastCompleteJson = this.findLastCompleteJson(jsonStr);
              if (lastCompleteJson) {
                snapshotImages = JSON.parse(lastCompleteJson);
              } else {
                console.warn('JSON이 잘려있어 파싱할 수 없습니다:', jsonStr.substring(0, 100) + '...');
                this.thermalImageSrc = null;
                this.visualImageSrc = null;
                return;
              }
            }
          } else if (Array.isArray(snapshotImagesJson)) {
            snapshotImages = snapshotImagesJson;
          }
        } catch (e) {
          console.error('parseSnapshotImages에서 JSON 파싱 오류:', e, '원본 데이터:', snapshotImagesJson);
          this.thermalImageSrc = null;
          this.visualImageSrc = null;
          return;
        }
        
        console.log('Parsed snapshot images:', snapshotImages);

        if (!Array.isArray(snapshotImages) || snapshotImages.length === 0) {
          console.log('No snapshot images in array');
          this.thermalImageSrc = null;
          this.visualImageSrc = null;
          return;
        }

        // image_type과 video_type에 따라 이미지 분류
        let thermalImage = null;
        let visualImage = null;

        for (const snapshot of snapshotImages) {
          // 파노라마 이미지 확인 (image_type 또는 panorama_image 필드)
          if (snapshot.image_type === 'panorama' || snapshot.panorama_image === true) {
            thermalImage = snapshot;
            console.log('Found panorama image (thermal)');
          }
          // video_type으로 열화상 이미지 확인
          else if (snapshot.video_type === '1' || snapshot.video_type === 1) {
            thermalImage = snapshot;
            console.log('Found thermal image by video_type');
          }
          // 실화상 스트림 이미지 확인 (image_type 또는 video_type)
          else if (snapshot.image_type === 'visible_stream' || snapshot.video_type === '2' || snapshot.video_type === 2) {
            visualImage = snapshot;
            console.log('Found visual image');
          }
        }

        // 첫 번째 이미지가 파노라마이고 두 번째가 실화상인 경우 (순서 기반으로도 확인)
        if (snapshotImages.length >= 1 && !thermalImage) {
          const firstImage = snapshotImages[0];
          if (firstImage.image_type === 'panorama' || firstImage.panorama_image === true || firstImage.image_data) {
            thermalImage = firstImage;
            console.log('Using first image as panorama (thermal)');
          }
        }

        if (snapshotImages.length >= 2 && !visualImage) {
          const secondImage = snapshotImages[1];
          if (secondImage.image_type === 'visible_stream' || secondImage.video_type === '2' || secondImage.video_type === 2 || secondImage.image_data) {
            visualImage = secondImage;
            console.log('Using second image as visual');
          }
        }

        // base64 이미지 소스 설정
        if (thermalImage && thermalImage.image_data) {
          this.thermalImageSrc = `data:image/jpeg;base64,${thermalImage.image_data}`;
          console.log('Thermal image loaded');
        } else {
          this.thermalImageSrc = null;
          console.log('No thermal image found', thermalImage);
        }

        if (visualImage && visualImage.image_data) {
          this.visualImageSrc = `data:image/jpeg;base64,${visualImage.image_data}`;
          console.log('Visual image loaded');
        } else {
          this.visualImageSrc = null;
          console.log('No visual image found', visualImage);
        }

      } catch (error) {
        console.error('Error parsing snapshot images:', error);
        this.thermalImageSrc = null;
        this.visualImageSrc = null;
      }
    },

    toggleAlertHistoryRefresh() {
      this.autoRefreshAlertHistory = !this.autoRefreshAlertHistory;
      if (this.autoRefreshAlertHistory) {
        this.startAlertRefresh();
      } else {
        this.stopAlertRefresh();
      }
    },

    onThermalImageLoad(event) {
      console.log('onThermalImageLoad', event);
      // 이미지의 실제 크기 정보 가져오기
      const img = event.target;
      
      // 원본 이미지 크기 (naturalWidth/naturalHeight)
      const naturalWidth = img.naturalWidth || 1920;
      const naturalHeight = img.naturalHeight || 480;
      
      // 실제 렌더링된 크기 (offsetWidth/offsetHeight) - CSS로 조정된 크기
      const renderedWidth = img.offsetWidth || naturalWidth;
      const renderedHeight = img.offsetHeight || naturalHeight;
      
      // object-fit: contain으로 인해 비율이 유지되므로, 실제 표시 영역 계산
      // contain 모드에서는 작은 쪽에 맞춰서 표시됨
      const containerWidth = img.parentElement ? img.parentElement.offsetWidth : renderedWidth;
      const containerHeight = img.parentElement ? img.parentElement.offsetHeight : renderedHeight;
      
      // 실제 이미지 비율
      const imageAspect = naturalWidth / naturalHeight;
      const containerAspect = containerWidth / containerHeight;
      
      // contain 모드에서 실제 표시되는 크기 계산
      let displayWidth, displayHeight;
      if (imageAspect > containerAspect) {
        // 이미지가 더 넓음 - 너비에 맞춤
        displayWidth = containerWidth;
        displayHeight = containerWidth / imageAspect;
      } else {
        // 이미지가 더 높음 - 높이에 맞춤
        displayHeight = containerHeight;
        displayWidth = containerHeight * imageAspect;
      }
      
      // contain 모드에서 이미지가 중앙 정렬되므로 오프셋 계산
      const offsetX = (containerWidth - displayWidth) / 2;
      const offsetY = (containerHeight - displayHeight) / 2;
      
      this.thermalImageSize = {
        width: displayWidth,
        height: displayHeight,
        naturalWidth: naturalWidth,
        naturalHeight: naturalHeight,
        renderedWidth: renderedWidth,
        renderedHeight: renderedHeight,
        containerWidth: containerWidth,
        containerHeight: containerHeight,
        offsetX: offsetX,
        offsetY: offsetY
      };
      
      console.log('Thermal image size:', {
        natural: `${naturalWidth}x${naturalHeight}`,
        rendered: `${renderedWidth}x${renderedHeight}`,
        display: `${displayWidth}x${displayHeight}`,
        container: `${containerWidth}x${containerHeight}`,
        offset: `${offsetX}, ${offsetY}`
      });
      
      // 이미지 렌더링 완료 후 alert 박스 업데이트
      this.$nextTick(() => {
        setTimeout(() => {
          this.updateAlertBoxes();
        }, 100);
      });
    },

    updateAlertBoxes() {
      if (this.displayAlertHistory.length === 0 || this.selectedAlertIndex >= this.displayAlertHistory.length) {
        this.alertBoxes = [];
        return;
      }

      const selectedAlert = this.displayAlertHistory[this.selectedAlertIndex];
      try {
        let alertInfo = {};
        
        // alert_info_json 안전하게 파싱
        try {
          if (selectedAlert.alert_info_json && typeof selectedAlert.alert_info_json === 'string') {
            // JSON 문자열이 잘린 경우를 대비하여 안전하게 파싱
            const jsonStr = selectedAlert.alert_info_json.trim();
            if (jsonStr.endsWith('}') || jsonStr.endsWith(']')) {
              alertInfo = JSON.parse(jsonStr);
            } else {
              // JSON이 잘린 경우, 마지막 완전한 객체나 배열을 찾아서 파싱 시도
              const lastCompleteJson = this.findLastCompleteJson(jsonStr);
              if (lastCompleteJson) {
                alertInfo = JSON.parse(lastCompleteJson);
              } else {
                console.warn('JSON이 잘려있어 파싱할 수 없습니다:', jsonStr.substring(0, 100) + '...');
                alertInfo = {};
              }
            }
          } else if (selectedAlert.alert_info_json && typeof selectedAlert.alert_info_json === 'object') {
            alertInfo = selectedAlert.alert_info_json;
          }
        } catch (e) {
          console.error('updateAlertBoxes에서 alert_info_json 파싱 오류:', e, '원본 데이터:', selectedAlert.alert_info_json);
          alertInfo = {};
        }
        
        this.selectedAlertZoneType = alertInfo.zone_type;

        // scenario에 따른 처리 분기
        if (alertInfo.scenario === 'scenario2') {
          // 시나리오2: alert_region 또는 bar_region 영역 그림
          let alertRegion = alertInfo.alert_region || alertInfo.bar_region;
          
          if (alertRegion) {
            // alert_region 또는 bar_region의 좌표 사용
            const start_x = alertRegion.start_x !== undefined ? alertRegion.start_x : (alertRegion.min_x !== undefined ? alertRegion.min_x : 0);
            const end_x = alertRegion.end_x !== undefined ? alertRegion.end_x : (alertRegion.max_x !== undefined ? alertRegion.max_x : 0);
            const start_y = alertRegion.start_y !== undefined ? alertRegion.start_y : (alertRegion.min_y !== undefined ? alertRegion.min_y : 0);
            const end_y = alertRegion.end_y !== undefined ? alertRegion.end_y : (alertRegion.max_y !== undefined ? alertRegion.max_y : 480);
            
            this.alertBoxes = [{
              box_id: `scenario2_region_${alertInfo.zone_type || 0}`,
              left: start_x,
              top: start_y,
              right: end_x,
              bottom: end_y,
              temp_diff: alertInfo.temperature_stats?.difference || 0,
              alert_level: alertInfo.alert_level || 1,
              polygon: [
                [start_x, start_y],
                [end_x, start_y],
                [end_x, end_y],
                [start_x, end_y]
              ],
              scenario: 'scenario2',
              alert_region: alertRegion,
              temperature_stats: alertInfo.temperature_stats
            }];
            
            console.log('Scenario2 alert_region box created:', this.alertBoxes[0]);
            console.log('  좌표 정보:', {
              left: start_x,
              top: start_y,
              right: end_x,
              bottom: end_y,
              width: end_x - start_x,
              height: end_y - start_y
            });
          } else if (alertInfo.roi_polygon && alertInfo.roi_polygon.main_roi) {
            // fallback: ROI 전체 영역을 박스로 표시
            const mainRoi = alertInfo.roi_polygon.main_roi;
            const rect = mainRoi.rect || [0, 0, 640, 240];
            const [x, y, w, h] = rect;
            
            this.alertBoxes = [{
              box_id: `scenario2_roi_${alertInfo.zone_type || 0}`,
              left: x,
              top: y,
              right: x + w,
              bottom: y + h,
              temp_diff: alertInfo.temperature_stats?.difference || 0,
              alert_level: alertInfo.alert_level || 1,
              polygon: mainRoi.polygon || [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
              scenario: 'scenario2',
              temperature_stats: alertInfo.temperature_stats
            }];
            
            console.log('Scenario2: ROI 전체 영역을 박스로 표시 (alert_region 없음)');
          } else {
            this.alertBoxes = [];
            console.log('Scenario2: alert_region 또는 ROI 정보가 없습니다');
          }
        } else if (alertInfo.roi_polygon && alertInfo.roi_polygon.alert_boxes && Array.isArray(alertInfo.roi_polygon.alert_boxes)) {
          // 시나리오1: roi_polygon의 alert_boxes에서 20x20 박스 정보 추출
          this.alertBoxes = alertInfo.roi_polygon.alert_boxes.map(box => ({
            ...box,
            // 폴리곤 좌표를 박스 스타일로 변환 (오버레이 내 상대 좌표로 변환)
            left: box.polygon[0][0],       // 절대 좌표 그대로 사용
            top: box.polygon[0][1],        // 절대 좌표 그대로 사용
            right: box.polygon[2][0],      // 절대 좌표 그대로 사용
            bottom: box.polygon[2][1],     // 절대 좌표 그대로 사용
            temp_diff: box.temp_diff || 0,
            alert_level: box.alert_level || 0,
            scenario: 'scenario1'
          }));
          
          console.log('Alert boxes updated from roi_polygon (시나리오1, 20x20 박스):', this.alertBoxes);
          
          // 첫 번째 박스의 좌표 정보 로깅
          if (this.alertBoxes.length > 0) {
            const firstBox = this.alertBoxes[0];
            console.log('첫 번째 박스 좌표 정보:', {
              box_id: firstBox.box_id,
              polygon: firstBox.polygon,
              left: firstBox.left,
              top: firstBox.top,
              right: firstBox.right,
              bottom: firstBox.bottom,
              width: firstBox.right - firstBox.left,
              height: firstBox.bottom - firstBox.top
            });
          }
        } else if (alertInfo.rect && Array.isArray(alertInfo.rect) && alertInfo.rect.length === 4) {
          // 기존 rect 정보로 fallback (단일 박스)
          const [x, y, width, height] = alertInfo.rect;
          this.alertBoxes = [{
            box_id: 'main_roi',
            left: x,
            top: y,
            right: x + width,
            bottom: y + height,
            temp_diff: 0,
            alert_level: alertInfo.alert_level || 0,
            polygon: [[x, y], [x + width, y], [x + width, y + height], [x, y + height]],
            scenario: 'unknown'
          }];
          
          console.log('Alert boxes updated from rect (fallback):', this.alertBoxes);
        } else {
          this.alertBoxes = [];
          console.log('No alert boxes data found');
        }

        console.log('Selected alert zone type:', this.selectedAlertZoneType);
      } catch (error) {
        console.error('Error parsing alert boxes:', error);
        this.alertBoxes = [];
      }
    },

    getAlertBoxStyle(box) {
      // 원본 파노라마 이미지 크기 (naturalWidth/naturalHeight 사용)
      const originalWidth = this.thermalImageSize.naturalWidth || 1920;
      const originalHeight = this.thermalImageSize.naturalHeight || 480;
      
      // 실제 표시되는 이미지 크기 (contain 모드로 인한 실제 표시 크기)
      const displayWidth = this.thermalImageSize.width || originalWidth;
      const displayHeight = this.thermalImageSize.height || originalHeight;
      
      // contain 모드에서 이미지가 중앙 정렬되므로 오프셋
      const offsetX = this.thermalImageSize.offsetX || 0;
      const offsetY = this.thermalImageSize.offsetY || 0;
      
      // 비율 계산 (원본 대비 실제 표시 크기 비율)
      const scaleX = displayWidth / originalWidth;
      const scaleY = displayHeight / originalHeight;
      
      // 원본 좌표를 표시 크기에 맞게 변환하고 오프셋 추가
      const left = (box.left * scaleX) + offsetX;
      const top = (box.top * scaleY) + offsetY;
      const width = (box.right - box.left) * scaleX;
      const height = (box.bottom - box.top) * scaleY;
      
      console.log('Box coordinate conversion:', {
        original: { left: box.left, top: box.top, right: box.right, bottom: box.bottom },
        scaled: { left, top, width, height },
        scale: { scaleX, scaleY },
        offset: { offsetX, offsetY },
        imageSize: { originalWidth, originalHeight, displayWidth, displayHeight }
      });
      
      // 시나리오에 따른 스타일 분기
      if (box.scenario === 'scenario2') {
        // 시나리오2: 수직 막대 스타일 (bar_region)
        const backgroundColor = this.getScenario2Color(box.alert_level || 1);
        
        return {
          position: 'absolute',
          left: `${left}px`,
          top: `${top}px`,
          width: `${width}px`,
          height: `${height}px`,
          backgroundColor: backgroundColor,
          border: '2px solid rgba(255, 255, 255, 0.9)',
          opacity: 0.6,
          cursor: 'pointer',
          transition: 'all 0.3s ease'
        };
      } else {
        // 시나리오1: 20x20 박스 스타일
        const tempDiff = box.temp_diff || 0;
        const backgroundColor = this.getTemperatureColor(tempDiff);
        
        return {
          position: 'absolute',
          left: `${left}px`,
          top: `${top}px`,
          width: `${width}px`,
          height: `${height}px`,
          backgroundColor: backgroundColor,
          border: '1px solid rgba(255, 255, 255, 0.8)',
          opacity: 0.7,
          cursor: 'pointer',
          transition: 'all 0.3s ease'
        };
      }
    },

    getTemperatureColor(tempDiff) {
      // 온도차에 따른 색상 변화: 노란색 -> 주황색 -> 붉은색
      if (tempDiff <= 2) {
        return 'rgba(255, 255, 0, 0.3)'; // 연한 노란색
      } else if (tempDiff <= 5) {
        return 'rgba(255, 255, 0, 0.5)'; // 노란색
      } else if (tempDiff <= 8) {
        return 'rgba(255, 165, 0, 0.6)'; // 주황색
      } else if (tempDiff <= 10) {
        return 'rgba(255, 69, 0, 0.7)'; // 붉은 주황색
      } else {
        return 'rgba(255, 0, 0, 0.8)'; // 붉은색
      }
    },

    getScenario2Color() {
      // 시나리오2 수직 막대 배경을 주황색으로 고정
      return 'rgba(255, 255, 0, 1)'; // 주황색 (고정)
      
      // 기존 경보 레벨별 색상 (주석 처리)
      /*
      switch (alertLevel) {
        case 1:
          return 'rgba(255, 255, 0, 0.4)'; // 노란색 (주의)
        case 2:
          return 'rgba(255, 165, 0, 0.5)'; // 주황색 (경고)
        case 3:
          return 'rgba(255, 69, 0, 0.6)'; // 붉은 주황색 (위험)
        case 4:
          return 'rgba(255, 0, 0, 0.7)'; // 붉은색 (심각)
        default:
          return 'rgba(255, 255, 0, 0.4)'; // 기본값 (노란색)
      }
      */
    },

    // 파노라마 이미지 클릭 이벤트
    onPanoramaImageClick() {
      console.log('Panorama image clicked');
      
      // 현재 선택된 경보의 ROI 정보 가져오기
      if (this.selectedAlertIndex >= 0 && this.selectedAlertIndex < this.displayAlertHistory.length) {
        const selectedAlert = this.displayAlertHistory[this.selectedAlertIndex];
        try {
          let alertInfo = {};
          if (selectedAlert.alert_info_json && typeof selectedAlert.alert_info_json === 'string') {
            const jsonStr = selectedAlert.alert_info_json.trim();
            if (jsonStr.endsWith('}') || jsonStr.endsWith(']')) {
              alertInfo = JSON.parse(jsonStr);
            } else {
              const lastCompleteJson = this.findLastCompleteJson(jsonStr);
              if (lastCompleteJson) {
                alertInfo = JSON.parse(lastCompleteJson);
              }
            }
          } else if (selectedAlert.alert_info_json && typeof selectedAlert.alert_info_json === 'object') {
            alertInfo = selectedAlert.alert_info_json;
          }
          
          // ROI 정보 추출
          if (alertInfo.roi_polygon && alertInfo.roi_polygon.main_roi) {
            const roiNumber = alertInfo.roi_polygon.main_roi.zone_type;
            this.selectedRoiNumber = roiNumber;
            // 다이얼로그를 먼저 열고, 렌더링 완료 후 데이터 로드
            this.showRoiDataDialog = true;
            this.$nextTick(() => {
              // 다이얼로그가 완전히 렌더링된 후 데이터 로드
              setTimeout(() => {
                this.loadRoiTimeSeriesData(roiNumber);
              }, 100);
            });
          } else if (alertInfo.zone_type) {
            // fallback: zone_type 직접 사용
            const roiNumber = alertInfo.zone_type;
            this.selectedRoiNumber = roiNumber;
            this.showRoiDataDialog = true;
            this.$nextTick(() => {
              setTimeout(() => {
                this.loadRoiTimeSeriesData(roiNumber);
              }, 100);
            });
          } else {
            this.$toast.warning('ROI 정보를 찾을 수 없습니다.');
          }
        } catch (e) {
          console.error('Error parsing ROI data for panorama image click:', e);
          this.$toast.error('ROI 데이터를 불러오는 중 오류가 발생했습니다.');
        }
      } else {
        this.$toast.warning('선택된 경보가 없습니다.');
      }
    },

    // Alert 박스 클릭 이벤트
    onAlertBoxClick(box) {
      console.log('Alert box clicked:', box);
      this.selectedAlertBoxId = box.box_id;
      
      // 시나리오에 따른 처리 분기
      if (box.scenario === 'scenario2') {
        // 시나리오2: 수직 막대 정보 표시
        const tempStats = box.temperature_stats || {};
        this.$toast.info(`시나리오2 수직 막대: 온도차 ${tempStats.difference?.toFixed(1) || 0}°C, 평균온도 ${tempStats.average?.toFixed(1) || 0}°C, 경보레벨 ${box.alert_level}`);
        
        // 시나리오2는 ROI 시계열 데이터가 없으므로 다이얼로그 표시하지 않음
        console.log('Scenario2 box clicked - no ROI time series data available');
      } else {
        // 시나리오1: 20x20 박스 정보 표시
        this.$toast.info(`박스 ${box.box_id}: 온도차 ${box.temp_diff.toFixed(1)}°C, 경보레벨 ${box.alert_level}`);
        
        // ROI 시계열 데이터 로드 (박스가 속한 ROI의 zone_type 사용)
        if (this.selectedAlertIndex >= 0 && this.selectedAlertIndex < this.displayAlertHistory.length) {
          const selectedAlert = this.displayAlertHistory[this.selectedAlertIndex];
          try {
            const alertInfo = selectedAlert.alert_info_json ? JSON.parse(selectedAlert.alert_info_json) : {};
            if (alertInfo.roi_polygon && alertInfo.roi_polygon.main_roi) {
              const roiNumber = alertInfo.roi_polygon.main_roi.zone_type;
              this.selectedRoiNumber = roiNumber;
              // 다이얼로그를 먼저 열고, 렌더링 완료 후 데이터 로드
              this.showRoiDataDialog = true;
              this.$nextTick(() => {
                // 다이얼로그가 완전히 렌더링된 후 데이터 로드
                setTimeout(() => {
                  this.loadRoiTimeSeriesData(roiNumber);
                }, 100);
              });
            }
          } catch (e) {
            console.error('Error parsing ROI data for box click:', e);
          }
        }
      }
    },

    findLastCompleteJson(jsonStr) {
      try {
        // JSON 문자열이 잘린 경우, 마지막 완전한 객체나 배열을 찾아서 반환
        let braceCount = 0;
        let bracketCount = 0;
        let inString = false;
        let escapeNext = false;
        let lastCompleteIndex = -1;
        
        for (let i = 0; i < jsonStr.length; i++) {
          const char = jsonStr[i];
          
          if (escapeNext) {
            escapeNext = false;
            continue;
          }
          
          if (char === '\\') {
            escapeNext = true;
            continue;
          }
          
          if (char === '"' && !escapeNext) {
            inString = !inString;
            continue;
          }
          
          if (!inString) {
            if (char === '{') {
              braceCount++;
            } else if (char === '}') {
              braceCount--;
              if (braceCount === 0) {
                lastCompleteIndex = i;
              }
            } else if (char === '[') {
              bracketCount++;
            } else if (char === ']') {
              bracketCount--;
              if (bracketCount === 0) {
                lastCompleteIndex = i;
              }
            }
          }
        }
        
        if (lastCompleteIndex > 0) {
          return jsonStr.substring(0, lastCompleteIndex + 1);
        }
        
        return null;
      } catch (error) {
        console.error('findLastCompleteJson 오류:', error);
        return null;
      }
    },

    getScenarioDisplayName(alert) {
      try {
        // alert_type에 따라 시나리오 표시
        const alertType = alert.type;
        
        // alert_type이 'S001', 'S002' 또는 1, 2인 경우 처리
        if (alertType === 'S001' || alertType === 1 || alertType === '1') {
          return '시나리오1';
        } else if (alertType === 'S002' || alertType === 2 || alertType === '2') {
          return '시나리오2';
        }
        
        // alert_info_json에서 scenario 정보 확인
        let alertInfo = {};
        try {
          if (alert.alert_info_json && typeof alert.alert_info_json === 'string') {
            const jsonStr = alert.alert_info_json.trim();
            if (jsonStr.endsWith('}') || jsonStr.endsWith(']')) {
              alertInfo = JSON.parse(jsonStr);
            } else {
              const lastCompleteJson = this.findLastCompleteJson(jsonStr);
              if (lastCompleteJson) {
                alertInfo = JSON.parse(lastCompleteJson);
              }
            }
          } else if (alert.alert_info_json && typeof alert.alert_info_json === 'object') {
            alertInfo = alert.alert_info_json;
          }
        } catch (e) {
          console.error('getScenarioDisplayName에서 alert_info_json 파싱 오류:', e);
        }
        
        // scenario 필드에서 확인
        if (alertInfo.scenario === 'scenario1') {
          return '시나리오1';
        } else if (alertInfo.scenario === 'scenario2') {
          return '시나리오2';
        }
        
        // fallback: ROI 번호 표시
        let roiNumber = '-';
        if (alertInfo.roi_polygon && alertInfo.roi_polygon.main_roi) {
          roiNumber = alertInfo.roi_polygon.main_roi.zone_type || alert.roiNumber || '-';
        } else {
          roiNumber = alert.roiNumber || '-';
        }
        
        return roiNumber !== '-' ? `ROI ${roiNumber}` : '-';
      } catch (error) {
        console.error('Error parsing scenario display name:', error);
        return alert.roiNumber ? `ROI ${alert.roiNumber}` : '-';
      }
    },

    getRoiDisplayName(alert) {
      try {
        let alertInfo = {};
        
        // alert_info_json 안전하게 파싱
        try {
          if (alert.alert_info_json && typeof alert.alert_info_json === 'string') {
            // JSON 문자열이 잘린 경우를 대비하여 안전하게 파싱
            const jsonStr = alert.alert_info_json.trim();
            if (jsonStr.endsWith('}') || jsonStr.endsWith(']')) {
              alertInfo = JSON.parse(jsonStr);
            } else {
              // JSON이 잘린 경우, 마지막 완전한 객체나 배열을 찾아서 파싱 시도
              const lastCompleteJson = this.findLastCompleteJson(jsonStr);
              if (lastCompleteJson) {
                alertInfo = JSON.parse(lastCompleteJson);
              } else {
                console.warn('JSON이 잘려있어 파싱할 수 없습니다:', jsonStr.substring(0, 100) + '...');
                alertInfo = {};
              }
            }
          } else if (alert.alert_info_json && typeof alert.alert_info_json === 'object') {
            alertInfo = alert.alert_info_json;
          }
        } catch (e) {
          console.error('getRoiDisplayName에서 alert_info_json 파싱 오류:', e, '원본 데이터:', alert.alert_info_json);
          alertInfo = {};
        }
        
        // roi_polygon의 main_roi에서 zone_type 추출
        // zone_type이 0인 경우도 "ROI 0"으로 표시해야 함
        let roiNumber = null;
        if (alertInfo.roi_polygon && alertInfo.roi_polygon.main_roi) {
          const zoneType = alertInfo.roi_polygon.main_roi.zone_type;
          // zone_type이 0인 경우도 유효한 ROI 번호로 처리
          if (zoneType !== null && zoneType !== undefined && zoneType !== '') {
            roiNumber = typeof zoneType === 'number' ? zoneType : parseInt(zoneType);
            if (!isNaN(roiNumber)) {
              return roiNumber;
            }
          }
        }
        
        // alertInfo.zone_type에서 추출 시도
        if (roiNumber === null && alertInfo.zone_type !== null && alertInfo.zone_type !== undefined && alertInfo.zone_type !== '') {
          roiNumber = typeof alertInfo.zone_type === 'number' ? alertInfo.zone_type : parseInt(alertInfo.zone_type);
          if (!isNaN(roiNumber)) {
            return roiNumber;
          }
        }
        
        // 기존 방식으로 fallback
        if (alert.roiNumber !== null && alert.roiNumber !== undefined && alert.roiNumber !== '') {
          return alert.roiNumber;
        }
        
        return '-';
      } catch (error) {
        console.error('Error parsing ROI display name:', error);
        if (alert.roiNumber !== null && alert.roiNumber !== undefined && alert.roiNumber !== '') {
          return alert.roiNumber;
        }
        return '-';
      }
    },

    // ROI 시계열 데이터 로드
    async loadRoiTimeSeriesData(roiNumber) {
      try {
        console.log('Loading ROI time series data for:', roiNumber);
        
        // 선택된 경보의 시간 정보 가져오기
        if (this.selectedAlertIndex >= 0 && this.selectedAlertIndex < this.alertHistory.length) {
          const selectedAlert = this.alertHistory[this.selectedAlertIndex];
          
          // 날짜 유효성 검사 및 변환 (originalTime은 이미 UTC)
          let eventDate;
          if (selectedAlert.originalTime) {
            // originalTime은 이미 UTC 시간 문자열이므로 그대로 사용
            eventDate = new Date(selectedAlert.originalTime);
            // Invalid Date 체크
            if (isNaN(eventDate.getTime())) {
              console.warn('Invalid date format:', selectedAlert.originalTime);
              // 현재 시간으로 대체
              eventDate = new Date();
            }
          } else if (selectedAlert.time) {
            // fallback: 포맷된 시간 사용 (ISO 형식이면 UTC로 해석됨)
            eventDate = new Date(selectedAlert.time);
            if (isNaN(eventDate.getTime())) {
              console.warn('Invalid formatted date format:', selectedAlert.time);
              // 현재 시간으로 대체
              eventDate = new Date();
            }
          } else {
            console.warn('No time data available, using current time');
            eventDate = new Date();
          }
          
          console.log('🔍 시간 변환 정보:');
          console.log('  - Original event date (UTC):', eventDate.toISOString());
          
          // API 호출 전 파라미터 로깅
          const apiParams = {
            roiNumber: roiNumber,
            eventDate: eventDate.toISOString()  // UTC 시간 그대로 사용
          };
          console.log('📡 API 호출 파라미터 (UTC):', apiParams);
          
          // API 호출
          const response = await getRoiTimeSeriesData(apiParams);
          
          console.log('ROI Time Series API Response:', response);
          console.log('Response status:', response?.status);
          console.log('Response data:', response?.data);
          
          // 응답 상태 코드 확인
          if (response && response.status === 200) {
            if (response.data && response.data.result) {
              const result = response.data.result;
              
              // API 응답 데이터를 차트용 데이터로 변환 (최대, 평균, 최소 온도 포함)
              this.roiTimeSeriesData = result.timeSeriesData.map(item => ({
                time: item.time,
                maxTemp: parseFloat(item.max || item.avg || 0),
                avgTemp: parseFloat(item.avg || 0),
                minTemp: parseFloat(item.min || item.avg || 0),
                roiNumber: item.roiNumber
              }));
              
              // 통계 정보 업데이트
              this.roiTemperatureStats = {
                maxTemp: parseFloat(result.statistics.maxTemp),
                minTemp: parseFloat(result.statistics.minTemp),
                avgTemp: parseFloat(result.statistics.avgTemp)
              };
              
              console.log('Processed ROI time series data:', this.roiTimeSeriesData);
              console.log('Temperature stats:', this.roiTemperatureStats);
              
              // 차트 초기화 (다이얼로그가 완전히 렌더링된 후)
              this.$nextTick(() => {
                // DOM이 완전히 렌더링될 때까지 약간의 지연 추가
                setTimeout(() => {
                  this.initRoiTimeSeriesChart();
                }, 200);
              });
            } else {
              console.log('API 응답에 result 데이터가 없습니다:', response.data);
              this.roiTimeSeriesData = [];
              this.roiTemperatureStats = { maxTemp: 0, minTemp: 0, avgTemp: 0 };
              // 데이터가 없어도 차트 초기화 (빈 차트 표시)
              this.$nextTick(() => {
                setTimeout(() => {
                  this.initRoiTimeSeriesChart();
                }, 200);
              });
            }
          } else if (response && response.status === 304) {
            console.log('API 응답 304 (Not Modified) - 데이터가 변경되지 않았거나 없습니다');
            console.log('Response headers:', response.headers);
            this.roiTimeSeriesData = [];
            this.roiTemperatureStats = { maxTemp: 0, minTemp: 0, avgTemp: 0 };
            // 데이터가 없어도 차트 초기화 (빈 차트 표시)
            this.$nextTick(() => {
              setTimeout(() => {
                this.initRoiTimeSeriesChart();
              }, 200);
            });
          } else {
            console.log('API 응답 오류 또는 예상치 못한 상태 코드:', response?.status);
            this.roiTimeSeriesData = [];
            this.roiTemperatureStats = { maxTemp: 0, minTemp: 0, avgTemp: 0 };
            // 데이터가 없어도 차트 초기화 (빈 차트 표시)
            this.$nextTick(() => {
              setTimeout(() => {
                this.initRoiTimeSeriesChart();
              }, 200);
            });
          }
        } else {
          console.log('No selected alert available');
          this.roiTimeSeriesData = [];
          this.roiTemperatureStats = { maxTemp: 0, minTemp: 0, avgTemp: 0 };
          // 데이터가 없어도 차트 초기화 (빈 차트 표시)
          this.$nextTick(() => {
            setTimeout(() => {
              this.initRoiTimeSeriesChart();
            }, 200);
          });
        }
      } catch (error) {
        console.error('Error loading ROI time series data:', error);
        this.$toast.error('ROI 데이터를 불러오는데 실패했습니다.');
        this.roiTimeSeriesData = [];
        this.roiTemperatureStats = { maxTemp: 0, minTemp: 0, avgTemp: 0 };
        // 에러 발생 시에도 차트 초기화 (빈 차트 표시)
        this.$nextTick(() => {
          setTimeout(() => {
            this.initRoiTimeSeriesChart();
          }, 200);
        });
      }
    },

    // 임시 데이터 생성 (실제 API 연동 시 제거)
    // generateMockRoiData(roiNumber) {
    //   const now = new Date();
    //   const data = [];
    //   
    //   for (let i = 24; i >= 0; i--) {
    //     const time = new Date(now.getTime() - i * 60 * 60 * 1000); // 1시간 간격
    //     const temperature = 20 + Math.random() * 30 + (roiNumber * 2); // ROI 번호에 따른 온도 변화
    //     
    //     data.push({
    //       time: time.toISOString(),
    //       temperature: parseFloat(temperature.toFixed(2)),
    //       roiNumber: roiNumber
    //     });
    //   }
    //   
    //   this.roiTimeSeriesData = data;
    //   this.calculateTemperatureStats();
    //   console.log('Generated mock ROI data:', data);
    // },

    // 온도 통계 계산
    calculateTemperatureStats() {
      if (this.roiTimeSeriesData.length === 0) {
        this.roiTemperatureStats = { maxTemp: 0, minTemp: 0, avgTemp: 0 };
        return;
      }

      const maxTemps = this.roiTimeSeriesData.map(item => item.maxTemp);
      const avgTemps = this.roiTimeSeriesData.map(item => item.avgTemp);
      const minTemps = this.roiTimeSeriesData.map(item => item.minTemp);
      
      const maxTemp = Math.max(...maxTemps);
      const minTemp = Math.min(...minTemps);
      const avgTemp = avgTemps.reduce((sum, temp) => sum + temp, 0) / avgTemps.length;

      this.roiTemperatureStats = {
        maxTemp: parseFloat(maxTemp.toFixed(2)),
        minTemp: parseFloat(minTemp.toFixed(2)),
        avgTemp: parseFloat(avgTemp.toFixed(2))
      };

      console.log('Temperature stats:', this.roiTemperatureStats);
    },

    // ROI 시계열 차트 초기화
    initRoiTimeSeriesChart() {
      const chartDom = this.$refs.roiTimeSeriesChart;
      if (!chartDom) return;
      
      if (this.roiTimeSeriesChart) {
        this.roiTimeSeriesChart.dispose();
      }
      
      this.roiTimeSeriesChart = echarts.init(chartDom);
      
      // 데이터가 없으면 빈 차트 표시
      if (!this.roiTimeSeriesData || this.roiTimeSeriesData.length === 0) {
        const emptyOption = {
          backgroundColor: 'transparent',
          title: {
            text: `ROI ${this.selectedRoiNumber} 온도 변화 추이`,
            textStyle: {
              color: '#ffffff',
              fontSize: 18,
              fontWeight: 'bold'
            },
            left: 'center',
            top: 10
          },
          graphic: {
            type: 'text',
            left: 'center',
            top: 'middle',
            style: {
              text: '데이터가 없습니다',
              fontSize: 16,
              fill: '#888'
            }
          }
        };
        this.roiTimeSeriesChart.setOption(emptyOption);
        return;
      }
      
      const timeData = this.roiTimeSeriesData.map((item, index) => {
        const date = new Date(item.time);
        
        // UTC 시간을 한국 시간(UTC+9)으로 변환
        const koreaTime = new Date(date.getTime() + (9 * 60 * 60 * 1000));
        
        // 디버깅용 로그 (첫 번째와 마지막 데이터만)
        if (index === 0 || index === this.roiTimeSeriesData.length - 1) {
          console.log(`⏰ 시계열 그래프 시간 변환 [${index === 0 ? '첫' : '마지막'} 데이터]:`);
          console.log(`  - API 응답 시간 (원본): ${item.time}`);
          console.log(`  - Date 객체 (UTC): ${date.toISOString()}`);
          console.log(`  - 한국 시간 (UTC+9): ${koreaTime.toISOString()}`);
          console.log(`  - 표시 시간: ${koreaTime.getUTCHours()}:${String(koreaTime.getUTCMinutes()).padStart(2, '0')}:${String(koreaTime.getUTCSeconds()).padStart(2, '0')}`);
        }
        
        // 한국 시간으로 표시
        return `${koreaTime.getUTCHours()}:${String(koreaTime.getUTCMinutes()).padStart(2, '0')}:${String(koreaTime.getUTCSeconds()).padStart(2, '0')}`;
      });
      
      const maxTempData = this.roiTimeSeriesData.map(item => item.maxTemp);
      const avgTempData = this.roiTimeSeriesData.map(item => item.avgTemp);
      const minTempData = this.roiTimeSeriesData.map(item => item.minTemp);
      
      // 온도 데이터의 최소값과 최대값 계산 (Y축 범위 동적 설정)
      const allTemps = [...maxTempData, ...avgTempData, ...minTempData].filter(temp => !isNaN(temp) && temp !== null && temp !== undefined);
      const minTemp = allTemps.length > 0 ? Math.min(...allTemps) : 0;
      const maxTemp = allTemps.length > 0 ? Math.max(...allTemps) : 100;
      
      // Y축 범위를 데이터에 맞게 조정 (여유 공간 추가)
      const tempRange = maxTemp - minTemp;
      const padding = tempRange > 0 ? tempRange * 0.1 : 5; // 10% 여유 공간 또는 최소 5도
      const yAxisMin = minTemp - padding; // 음수값 허용
      const yAxisMax = maxTemp + padding;
      
      const option = {
        backgroundColor: 'transparent',
        title: {
          text: `ROI ${this.selectedRoiNumber} 온도 변화 추이 (24시간)`,
          textStyle: {
            color: '#ffffff',
            fontSize: 18,
            fontWeight: 'bold'
          },
          left: 'center',
          top: 10
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderColor: '#ff6b6b',
          borderWidth: 1,
          textStyle: {
            color: '#ffffff'
          },
          axisPointer: {
            type: 'cross',
            lineStyle: {
              color: '#ff6b6b',
              width: 1
            }
          },
          formatter: function (params) {
            let tooltipContent = `<div style="padding: 8px;">
              <div style="font-weight: bold; margin-bottom: 8px;">${params[0].name}</div>`;
            
            params.forEach(param => {
              const color = param.color;
              const value = param.value;
              const seriesName = param.seriesName;
              tooltipContent += `<div style="color: ${color}; margin-bottom: 4px;">${seriesName}: ${value}°C</div>`;
            });
            
            tooltipContent += '</div>';
            return tooltipContent;
          }
        },
        grid: {
          left: '5%',
          right: '5%',
          bottom: '10%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: timeData,
          axisLine: {
            lineStyle: {
              color: '#666666',
              width: 2
            }
          },
          axisTick: {
            lineStyle: {
              color: '#666666'
            }
          },
          axisLabel: {
            color: '#ffffff',
            fontSize: 12,
            rotate: 45
          }
        },
        yAxis: {
          type: 'value',
          name: '온도 (°C)',
          min: yAxisMin,
          max: yAxisMax,
          nameTextStyle: {
            color: '#ffffff',
            fontSize: 14,
            fontWeight: 'bold'
          },
          axisLine: {
            lineStyle: {
              color: '#666666',
              width: 2
            }
          },
          axisTick: {
            lineStyle: {
              color: '#666666'
            }
          },
          axisLabel: {
            color: '#ffffff',
            fontSize: 12,
            formatter: function (value) {
              // 소수점 없이 정수로 표시
              return Math.round(value);
            }
          },
          splitLine: {
            lineStyle: {
              color: 'rgba(255, 255, 255, 0.1)',
              type: 'dashed'
            }
          }
        },
        legend: {
          data: ['최대온도', '평균온도', '최소온도'],
          textStyle: {
            color: '#ffffff',
            fontSize: 12
          },
          top: 40
        },
        series: [
          {
            name: '최대온도',
            type: 'line',
            data: maxTempData,
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: {
              color: '#ff4444',
              width: 3,
              shadowColor: 'rgba(255, 68, 68, 0.3)',
              shadowBlur: 8
            },
            itemStyle: {
              color: '#ff4444',
              borderColor: '#ffffff',
              borderWidth: 2
            }
          },
          {
            name: '평균온도',
            type: 'line',
            data: avgTempData,
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: {
              color: '#ff6b6b',
              width: 4,
              shadowColor: 'rgba(255, 107, 107, 0.3)',
              shadowBlur: 10
            },
            itemStyle: {
              color: '#ff6b6b',
              borderColor: '#ffffff',
              borderWidth: 2
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(255, 107, 107, 0.4)' },
                { offset: 0.5, color: 'rgba(255, 107, 107, 0.2)' },
                { offset: 1, color: 'rgba(255, 107, 107, 0.05)' }
              ])
            }
          },
          {
            name: '최소온도',
            type: 'line',
            data: minTempData,
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: {
              color: '#44aaff',
              width: 3,
              shadowColor: 'rgba(68, 170, 255, 0.3)',
              shadowBlur: 8
            },
            itemStyle: {
              color: '#44aaff',
              borderColor: '#ffffff',
              borderWidth: 2
            }
          }
        ]
      };
      
      this.roiTimeSeriesChart.setOption(option);
    },

    // ROI 데이터 다이얼로그 닫기
    closeRoiDataDialog() {
      this.showRoiDataDialog = false;
      this.selectedRoiNumber = null;
      this.roiTimeSeriesData = [];
      
      if (this.roiTimeSeriesChart) {
        this.roiTimeSeriesChart.dispose();
        this.roiTimeSeriesChart = null;
      }
    },

    // 시나리오 필터 관련 메서드
    applyScenarioFilter() {
      // "전체" 선택 시 (scenarioFilter가 null) 모든 경보 표시
      if (this.scenarioFilter === null || this.scenarioFilter === undefined) {
        this.filteredAlertHistory = [];
        // 필터가 없으므로 원본 리스트의 첫 번째 항목 선택
        if (this.alertHistory.length > 0) {
          this.selectedAlertIndex = 0;
          this.parseSnapshotImages(this.alertHistory[0].snapshotImages);
          this.updateAlertBoxes();
          this.updateCurrentScenario(this.alertHistory[0]);
        }
        return;
      }

      const filterScenario = parseInt(this.scenarioFilter);
      this.filteredAlertHistory = this.alertHistory.filter(alert => {
        try {
          // alert.type에서 시나리오 확인
          const alertType = alert.type;
          let detectedScenario = null;
          
          if (alertType === 'S001' || alertType === 1 || alertType === '1') {
            detectedScenario = 1;
          } else if (alertType === 'S002' || alertType === 2 || alertType === '2') {
            detectedScenario = 2;
          }

          // alert.type에서 시나리오를 찾지 못한 경우 alert_info_json에서 확인
          if (detectedScenario === null && alert.alert_info_json) {
            let alertInfo = {};
            if (typeof alert.alert_info_json === 'string') {
              const jsonStr = alert.alert_info_json.trim();
              if (jsonStr.endsWith('}') || jsonStr.endsWith(']')) {
                alertInfo = JSON.parse(jsonStr);
              } else {
                const lastCompleteJson = this.findLastCompleteJson(jsonStr);
                if (lastCompleteJson) {
                  alertInfo = JSON.parse(lastCompleteJson);
                }
              }
            } else if (typeof alert.alert_info_json === 'object') {
              alertInfo = alert.alert_info_json;
            }
            
            // scenario 필드에서 확인
            if (alertInfo.scenario === 'scenario1') {
              detectedScenario = 1;
            } else if (alertInfo.scenario === 'scenario2') {
              detectedScenario = 2;
            }
          }

          // 필터와 비교
          return detectedScenario !== null && detectedScenario === filterScenario;
        } catch (e) {
          console.error('시나리오 필터링 오류:', e, alert);
        }
        return false;
      });

      // 필터 적용 후 선택된 인덱스 조정
      if (this.filteredAlertHistory.length > 0 && this.selectedAlertIndex >= this.filteredAlertHistory.length) {
        this.selectedAlertIndex = 0;
        if (this.filteredAlertHistory.length > 0) {
          this.parseSnapshotImages(this.filteredAlertHistory[0].snapshotImages);
          this.updateAlertBoxes();
          this.updateCurrentScenario(this.filteredAlertHistory[0]);
        }
      } else if (this.filteredAlertHistory.length === 0) {
        this.selectedAlertIndex = -1;
        this.thermalImageSrc = null;
        this.visualImageSrc = null;
        this.alertBoxes = [];
      }
    },

  }
};
</script>

<style lang="scss" scoped>
.alert-status-container {
  display: flex;
  height: 100vh;
  background: #222736;
  gap: 8px;
  padding: 8px;
  overflow: hidden;
}

.left-sidebar {
  width: 25%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
  min-width: 250px;
}

.center-content {
  width: 50%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  flex-shrink: 0;
}

.right-sidebar {
  width: 25%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
  min-width: 250px;
}

// Time Layer
.time-layer {
  background: #3659e2;
  color: white;
  padding: 10px;
  text-align: center;
  border-radius: 8px;
  height: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  
  .location-info {
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 8px;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
    line-height: 1.2;
  }
  
  .current-time {
    font-size: 18px;
    font-weight: bold;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
  }
}

// Alert History Layer
.alert-history-layer {
  background: #2a3042;
  color: white;
  padding: 8px;
  border-radius: 8px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  
  .layer-title {
    background: #666;
    color: white;
    font-weight: bold;
    padding: 8px 10px;
    margin-bottom: 10px;
    font-size: 14px;
    text-align: left;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .roi-filter-section {
    padding: 8px;
    background: #3a3a3a;
    border-bottom: 1px solid #555;
    flex-shrink: 0;
    
    ::v-deep .v-select {
      .v-input__control {
        background: #4a4a4a !important;
      }
      
      .v-select__selection {
        color: #ffffff !important;
      }
      
      .v-input__slot {
        background: #4a4a4a !important;
        border: 1px solid #666 !important;
        border-radius: 2px !important;
      }
      
      .v-select__selection--placeholder {
        color: rgba(255, 255, 255, 0.6) !important;
      }
      
      // 선택 시 (focused/active)
      &.v-input--is-focused,
      &.v-input--is-active {
        .v-input__slot {
          border: 2px solid #ff4444 !important;
          background: #5a5a5a !important;
        }
      }
      
      // 호버 시
      &:hover {
        .v-input__slot {
          border: 1px solid #888 !important;
          background: #525252 !important;
        }
      }
      
      // 라벨 색상
      .v-label {
        color: rgba(255, 255, 255, 0.7) !important;
      }
      
      &.v-input--is-focused,
      &.v-input--is-active {
        .v-label {
          color: #ffffff !important;
        }
      }
      
      // 아이콘 색상
      .v-input__prepend-inner,
      .v-input__append-inner {
        i {
          color: #ffffff !important;
        }
      }
      
      // 선택된 값의 색상
      .v-select__selection--comma {
        color: #ffffff !important;
      }
      
      // 드롭다운 메뉴 아이템
      .v-list-item {
        color: #ffffff !important;
        
        &:hover {
          background: #5a5a5a !important;
        }
        
        &.v-list-item--active {
          background: #ff4444 !important;
          color: #ffffff !important;
        }
      }
    }
  }
  
  .alert-history-content {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    
            .alert-history-table {
          .table-row {
            background: #1e1e1e;
            border-radius: 4px;
            margin-bottom: 8px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            
            &:hover {
              background: #2a2a2a;
              transform: translateY(-1px);
              box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            }
            
            .roi-number {
              flex: 0.5;
              display: flex;
              align-items: center;
              justify-content: center;
              background: transparent !important;
              border-right: 1px solid #2d2d2d;
              
              .roi-label {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
              }
            }
            
            .data-table {
              flex: 3.5;
              display: flex;
              flex-direction: column;
              
              .table-item {
                display: flex;
                padding: 0;
                border-bottom: 1px solid #2d2d2d;
                
                &:last-child {
                  border-bottom: none;
                }
                
                .item-label {
                  background: #535e6c;
                  color: #ffffff;
                  font-size: 14px;
                  font-weight: bold;
                  padding: 8px 12px;
                  flex: 1;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                }
                
                .item-value {
                  background: #3659e2;
                  color: #ffffff;
                  font-size: 14px;
                  padding: 8px 12px;
                  flex: 3;
                  display: flex;
                  align-items: center;
                  justify-content: flex-start;
                }
              }
            }
        
        &.alert-level-3 {
          animation: blink-amber 1s infinite;
        }
        &.alert-level-4 {
          animation: blink-orange 1s infinite;
        }
        &.alert-level-5 {
          animation: blink-red 1s infinite;
        }
        
        &.selected-alert {
          background: #2a3042 !important;
          border: 2px solid #fff;
          box-shadow: 0 0 10px rgba(54, 89, 226, 0.5);
          
          .roi-number {
            background: #2a3042;
            
            .roi-label {
              color: #ffffff !important;
            }
          }
          
          .data-table {
            .table-item {
              .item-label {
                background: #2a3042;
              }
              
              .item-value {
                background: #3659e2;
                color: #fff;
                font-weight: bold;
              }
            }
          }
        }
      }
    }
  }
}

@keyframes blink-amber {
  0% { background-color: #1e1e1e; }
  50% { background-color: rgba(255, 193, 7, 0.2); }
  100% { background-color: #1e1e1e; }
}

@keyframes blink-orange {
  0% { background-color: #1e1e1e; }
  50% { background-color: rgba(255, 152, 0, 0.2); }
  100% { background-color: #1e1e1e; }
}

@keyframes blink-red {
  0% { background-color: #1e1e1e; }
  50% { background-color: rgba(244, 67, 54, 0.2); }
  100% { background-color: #1e1e1e; }
}



// Center Content - Image Boxes
.top-image-box, .bottom-image-box {
  background: #2a3042;
  border: 1px solid #2a3042;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.top-image-box {
  flex: 1;
}

.bottom-image-box {
  flex: 1;
}

.box-title {
  background: #666;
  color: #fff;
  font-weight: bold;
  padding: 8px 16px;
  border-bottom: 2px solid #555;
  border-radius: 8px 8px 0 0;
  flex-shrink: 0;
  position: relative;
  z-index: 2;
}

.image-container {
  flex: 1;
  position: relative;
  background: #000;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  z-index: 0;
  overflow: hidden;
}

.thermal-image {
  width: 100%;
  height: auto;
  max-width: 100%;
  object-fit: contain;
  border-radius: 8px;
  background: #000;
  cursor: pointer;
  transition: opacity 0.2s ease;
  
  &:hover {
    opacity: 0.9;
  }
}

.visual-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 8px;
  background: #000;
}


.thermal-image-placeholder, .visual-image-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed #444;
  
  .placeholder-text {
    color: #fff;
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 8px;
  }
  
  .placeholder-subtext {
    color: #888;
    font-size: 14px;
    text-align: center;
  }
}

// Right Sidebar
.gauge-box, .chart-box, .history-box {
  background: #2a3042;
  border: 1px solid #2a3042;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.gauge-box {
  height: 280px;
}

.chart-box {
  height: 220px;
}

.history-box {
  flex: 1;
}

.gauge-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 8px;
}

.gauge-meter {
  width: 100%;
  height: 220px;
  min-width: 160px;
  min-height: 160px;
}

.scenario-info {
  padding: 12px 16px;
  border-top: 1px solid #444;
  background: #1e1e1e;
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .scenario-label {
    color: #888;
    font-size: 14px;
    font-weight: 500;
  }
  
  .scenario-value {
    color: #fff;
    font-size: 16px;
    font-weight: bold;
  }
}

.chart-container {
  flex: 1;
  padding: 8px;
  background: #2a3042;
}

.alert-table {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;

  .table-header {
    display: flex;
    background: #444;
    font-weight: bold;
    flex-shrink: 0;
    
    .header-cell {
      flex: 1;
      text-align: center;
      color: #fff;
      padding: 8px 0;
      font-size: 12px;
    }
  }
  
  .table-body {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    
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
        font-size: 12px;
        
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

@media (max-width: 1200px) {
  .alert-status-container {
    flex-direction: column;
    height: auto;
    gap: 4px;
  }
  
  .left-sidebar, .right-sidebar {
    width: 100%;
  }
  
  .center-content {
    min-height: 400px;
  }
}

// ROI 데이터 팝업 스타일
.roi-dialog-card {
  background: #2a3042 !important;
  border-radius: 12px;
  overflow: hidden;
  
  .roi-dialog-title {
    background: linear-gradient(135deg, #3659e2 0%, #764ba2 100%);
    color: white;
    padding: 20px 24px;
    border-bottom: 1px solid #444;
    
    .title-content {
      .main-title {
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 4px;
      }
      
      .sub-title {
        font-size: 14px;
        opacity: 0.8;
      }
    }
    
    .close-btn {
      color: white;
      
      &:hover {
        background: rgba(255, 255, 255, 0.1);
      }
    }
  }
  
  .roi-dialog-content {
    padding: 24px;
    background: #2a3042;
    
    .roi-data-container {
      .temperature-summary {
        display: flex;
        gap: 16px;
        margin-bottom: 24px;
        padding: 16px;
        background: #1e1e1e;
        border-radius: 8px;
        border: 1px solid #444;
        
        .summary-item {
          flex: 1;
          text-align: center;
          padding: 12px;
          background: #2a3042;
          border-radius: 6px;
          border: 1px solid #555;
          
          .item-label {
            font-size: 12px;
            color: #888;
            margin-bottom: 4px;
            font-weight: 500;
          }
          
          .item-value {
            font-size: 18px;
            color: #ff6b6b;
            font-weight: bold;
          }
        }
      }
      
      .chart-container {
        background: #1e1e1e;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #444;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      }
      
      .no-data {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 200px;
        background: #1e1e1e;
        border-radius: 8px;
        border: 1px solid #444;
        
        .no-data-text {
          color: #888;
          font-size: 16px;
        }
      }
    }
  }
  
  .roi-dialog-actions {
    padding: 16px 24px;
    background: #2a3042;
    border-top: 1px solid #444;
    
    .close-action-btn {
      background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
      color: white;
      border-radius: 6px;
      padding: 8px 24px;
      font-weight: 500;
      
      &:hover {
        background: linear-gradient(135deg, #ff5252 0%, #d32f2f 100%);
      }
    }
  }
}
</style>
