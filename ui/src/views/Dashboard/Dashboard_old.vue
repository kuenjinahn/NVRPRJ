<template lang="pug">
.sidebar-root
  .notification-status
    v-container(fluid)
      v-row
        v-col(cols="12")
          v-card.notification-card
            .camera-status
              .status-header
              .camera-list-container
                .camera-grid(v-if="cameras && cameras.length > 0")
                  .camera-box(
                    v-for="(camera, index) in cameras"
                    :key="`camera-${index}`"
                    :class="{ 'active': selectedCameraIndex === index }"
                    @click="selectCamera(index)"
                  )
                    .camera-thumbnail
                      VideoCard(
                        :ref="`thumbnail-${camera.name}`"
                        :camera="camera"
                        stream
                        noLink
                        hideNotifications
                        hideIndicatorFullscreen
                        :style="{ height: '120px' }"
                      )
                    .camera-info
                      .camera-name {{ camera.name }}
                .no-cameras(v-else)
                  span.no-cameras-text 카메라 목록이 없습니다. ({{ cameras.length }})
            .camera-display-area
              .display-box.left-box
                .alert-history
                  .alert-history-title
                    | 경보 이력
                    v-btn(
                      icon
                      :color="autoRefreshAlertHistory ? 'primary' : 'grey'"
                      @click="toggleAlertHistoryRefresh"
                      class="ml-2"
                      small
                    )
                      v-icon {{ icons.mdiRefresh }}
                  .alert-history-table
                    .table-row(
                      v-for="alert in alertHistory" 
                      :key="alert.id"
                      :class="{'alert-level-3': Number(alert.level) >= 3, 'alert-level-4': Number(alert.level) >= 4, 'alert-level-5': Number(alert.level) >= 5}"
                    )
                      .table-item
                        .item-label 경보시간
                        .item-value {{ alert.time }}
                      .table-item
                        .item-label 경보종류
                        .item-value {{ getTypeText(alert.type) }}
                      .table-item
                        .item-label 경보단계
                        .item-value {{ getLevelText(alert.level) }}
                      .table-item
                        .item-label 최고온도
                        .item-value {{ alert.maxTemp }}°C
                      .table-item
                        .item-label 최저온도
                        .item-value {{ alert.minTemp }}°C
              .display-box.center-box
                VideoCard(
                  v-if="selectedCamera"
                  :ref="`main-${selectedCamera.name}`"
                  :key="`video-${selectedCamera.name}-${videoKey}`"
                  :camera="selectedCamera"
                  stream
                  noLink
                  hideNotifications
                  hideIndicatorFullscreen
                  :style="{ height: '100%' }"
                )
                .no-video(v-else)
                  span.no-video-text 영상을 선택해주세요
              .display-box.right-box
                .right-box-content
                  .top-box
  
                    .gauge-container
                      .gauge-meter(ref="gaugeChart")
                  .center-box
                    .chart-title 최근 7일 경보건수
                    .chart-container
                      div(ref="alertChart" style="width:100%;height:200px;min-width:200px;min-height:200px;")
                  .bottom-box
                    .table-title 경보 이력
                    .alert-table
                      .table-header
                        .header-cell 경보레벨
                        .header-cell 발생일자
                      .table-body
                        .table-row(v-for="alert in alertHistory" :key="alert.id")
                          .table-cell {{ getLevelText(alert.level) }}
                          .table-cell {{ alert.time }}
</template>
  
<script>
import { 
  mdiRefresh
} from '@mdi/js';
import { getCameras, getCameraSettings } from '@/api/cameras.api';
import { getAlerts, getRecentAlertCounts } from '@/api/alerts.api';
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
    autoRefreshAlertHistory: true
  }),

  computed: {
    selectedCamera() {
      return this.selectedCameraIndex !== null && this.cameras.length > 0 
        ? this.cameras[this.selectedCameraIndex] 
        : null;
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
    //this.startAlertRefresh();
  },

  beforeDestroy() {
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
    this.$socket.client.off('connect', this.handleSocketConnect);
    this.stopAlertRefresh();
  },

  methods: {
    async initializeData() {
      try {
        await this.fetchCameras();
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

    async loadAlertHistory() {
      try {
        const response = await getAlerts('');
        this.alertHistory = response.data.result.map(alert => {
          let minTemp = '-';
          let maxTemp = '-';
          try {
            const info = alert.alert_info_json ? JSON.parse(alert.alert_info_json) : {};
            minTemp = (typeof info.min_roi_value === 'number') ? info.min_roi_value.toFixed(1) : '-';
            maxTemp = (typeof info.max_roi_value === 'number') ? info.max_roi_value.toFixed(1) : '-';
          } catch (e) {
            // no-op
          }
          return {
            id: alert.id,
            time: this.formatDate(alert.alert_accur_time),
            type: alert.alert_type,
            level: alert.alert_level,
            maxTemp,
            minTemp
          }
        });

        // 최신 경보단계로 gaugeChart 값 반영 (한글 문구로)
        if (this.alertHistory.length > 0) {
          this.alertCount = Number(this.alertHistory[0].level) || 0;
          const levelLabel = this.getLevelText(this.alertHistory[0].level);
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

    formatDate(dateStr) {
      const date = new Date(dateStr);
      return date.toLocaleString();
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

        // 최근 7일 날짜 배열 생성 (오늘 포함)
        const today = new Date();
        const categories = [];
        for (let i = 6; i >= 0; i--) {
          const d = new Date(today);
          d.setDate(today.getDate() - i);
          categories.push(d.toISOString().slice(0, 10));
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
      }, 2000);
    },

    stopAlertRefresh() {
      if (this.alertRefreshTimer) {
        clearInterval(this.alertRefreshTimer);
        this.alertRefreshTimer = null;
      }
    },

    toggleAlertHistoryRefresh() {
      this.autoRefreshAlertHistory = !this.autoRefreshAlertHistory;
      if (this.autoRefreshAlertHistory) {
        this.startAlertRefresh();
      } else {
        this.stopAlertRefresh();
      }
    }
  }
};
</script>

<style lang="scss" scoped>
.notification-status {
  height: 100vh;
  background-color: #1e1e1e;
  
  .notification-card {
    background-color: transparent !important;
    height: 100%;
    
    .camera-status {
      background-color: #2d2d2d;
      border-radius: 8px;
      margin-bottom: 10px;
      padding: 2px;
      
      .status-header {
        display: flex;
        flex-direction: row;
        align-items: center;
        margin-bottom: 10px;
        
        .status-title {
          font-size: 1.25rem;
          color: #ffffff;
          margin-right: auto;
        }
      }

      .camera-list-container {
        width: 100%;
        
        .camera-grid {
          display: flex;
          flex-direction: row;
          gap: 16px;
          overflow-x: auto;
          padding: 8px 0;
          width: 100%;
          
          &::-webkit-scrollbar {
            height: 8px;
          }
          
          &::-webkit-scrollbar-track {
            background: #1e1e1e;
            border-radius: 4px;
          }
          
          &::-webkit-scrollbar-thumb {
            background: #3d3d3d;
            border-radius: 4px;
            
            &:hover {
              background: #4d4d4d;
            }
          }
        }
        
        .camera-box {
          min-width: 250px;
          max-width: 350px;
          flex: 0 0 auto;
          background: #1e1e1e;
          border: 1px solid #3d3d3d;
          border-radius: 4px;
          padding: 8px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          align-items: center;
          cursor: pointer;
          transition: all 0.3s ease;
          
          &:hover {
            transform: scale(1.02);
          }
          
          &.active {
            background: #3d3d3d;
            border-color: var(--cui-primary);
          }
          
          .camera-thumbnail {
            width: 100px;
            height: 80px;
            margin-bottom: 8px;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            
            :deep(.video-card) {
              width: 100px;
              height: 80px;
              background: transparent;
              display: flex;
              align-items: center;
              justify-content: center;
              
              .video-card-content {
                border-radius: 4px;
                width: 100px;
                height: 80px;
                display: flex;
                align-items: center;
                justify-content: center;

                video, img {
                  width: 100px;
                  height: 80px;
                  object-fit: contain;
                }
              }
            }
          }
          
          .camera-info {
            width: 100%;
            padding: 4px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            
            &:hover {
              background: #3d3d3d;
              border-radius: 4px;
            }
            
            .camera-name {
              color: #ffffff;
              font-size: 0.7rem;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
              text-align: center;
            }
          }
        }
      }
    }

    .camera-display-area {
      flex: 1;
      display: flex;
      gap: 16px;
      margin-top: auto;
      height: calc(100vh - 200px);
      
      .display-box {
        background-color: #2d2d2d;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        height: 100%;

        &.left-box {
          width: 15%;
          
          .alert-history {
            height: 100%;
            display: flex;
            flex-direction: column;
            
            .alert-history-title {
              padding: 12px;
              font-size: 0.95rem;
              color: #ffffff;
              border-bottom: 1px solid #3d3d3d;
              flex-shrink: 0;
            }
            
            .alert-history-table {
              flex: 1;
              overflow-y: auto;
              padding: 8px;
              min-height: 0;
              
              .table-row {
                background: #1e1e1e;
                border-radius: 4px;
                margin-bottom: 8px;
                
                .table-item {
                  display: flex;
                  justify-content: space-between;
                  padding: 6px 10px;
                  border-bottom: 1px solid #2d2d2d;
                  
                  .item-label {
                    color: #888888;
                    font-size: 0.8rem;
                  }
                  
                  .item-value {
                    color: #ffffff;
                    font-size: 0.8rem;
                  }
                }
              }
            }
          }
        }

        &.center-box {
          width: 60%;
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: hidden;
          padding: 8px;
          
          position: relative;
          height: 100%;
          min-height: 400px;
          
          :deep(.video-card) {
            width: 100%;
            height: 100%;
            background: transparent;
            
            .video-card-content {
              border-radius: 4px;
              overflow: hidden;
              display: flex;
              align-items: center;
              justify-content: center;
            }
          }
          
          .no-video {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            color: #666;
          }
        }

        &.right-box {
          width: 25%;
          
          .right-box-content {
            height: 100%;
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding: 12px;

            .top-box, .center-box, .bottom-box {
              background: #1e1e1e;
              border-radius: 4px;
              padding: 12px;
              flex: 1;
              display: flex;
              flex-direction: column;
            }

            .gauge-title, .chart-title, .table-title {
              color: #ffffff;
              font-size: 0.45rem;
              margin-bottom: 10px;
              text-align: center;
            }

            .gauge-container {
              flex: 1;
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;

              .gauge-meter {
                width: 100%;
                height: 240px;
              }
            }

            .chart-container {
              flex: 1;
              position: relative;
              height: 200px;
            }

            .alert-table {
              flex: 1;
              overflow-y: auto;
              min-height: 0;
              
              .table-header {
                display: flex;
                background: #2d2d2d;
                padding: 6px;
                border-radius: 4px 4px 0 0;
                margin-bottom: 1px;
                
                .header-cell {
                  flex: 1;
                  color: #ffffff;
                  font-size: 0.7rem;
                  text-align: center;
                  font-weight: 600;
                }
              }

              .table-body {
                overflow-y: auto;
                
                .table-row {
                  display: flex;
                  padding: 6px;
                  border-bottom: 1px solid #2d2d2d;
                  transition: background-color 0.2s;
                  
                  &:hover {
                    background: #2d2d2d;
                  }
                  
                  &:last-child {
                    border-bottom: none;
                  }

                  .table-cell {
                    flex: 1;
                    color: #ffffff;
                    font-size: 0.7rem;
                    text-align: center;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    padding: 0 4px;
                    
                    &:first-child {
                      color: #888888;
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}

.camera-box {
  cursor: pointer;
  transition: all 0.3s ease;
  
  &:hover {
    transform: scale(1.02);
  }
  
  &.active {
    border: 2px solid #4CAF50;
  }
}

.display-box.center-box {
  position: relative;
  height: 100%;
  min-height: 400px;
  
  .no-video {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: #666;
  }
}

.alert-history-table {
  .table-row {
    &.alert-level-3 {
      animation: blink-amber 1s infinite;
    }
    &.alert-level-4 {
      animation: blink-orange 1s infinite;
    }
    &.alert-level-5 {
      animation: blink-red 1s infinite;
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
</style>
