<template lang="pug">
.dashboard-2by2
  .cell.cell-topleft
    .topleft-inner-row
      .topleft-inner-left
        .time-display
          .current-time {{ currentTime }}
        .weather-widget
          .weather-info
            .temperature {{ weather.temperature }}°C
            .weather-description {{ weather.description }}
            .location {{ weather.location }}
      .topleft-inner-right
        //- No title
  .cell.cell-topright
    .box-title Thermal Camera
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
  .cell.cell-bottomleft
    .bottomleft-inner-col
      .bottomleft-inner-top
        .box-title ROI List
        .table-container
          table.zone-table
            thead
              tr
                th ROI
                th Max Temp
                th Min Temp
                th Avg Temp
                th Graph
                th Download
            tbody
              tr(
                v-for="(zone, idx) in zones"
                :key="zone.name"
                :class="{selected: selectedZoneIdx === idx}"
                @click="selectZone(idx)"
              )
                td {{ zone.name }}
                td {{ zone.maxTemp }}
                td {{ zone.minTemp }}
                td {{ zone.avgTemp }}
                td
                  span.icon-chart 📈
                td
                  span.icon-excel 📊
      .bottomleft-inner-bottom
        .box-title Time Series Temperature
        .chart-container
          VChart(v-if="selectedZone" :option="chartOption" autoresize)
          .no-data(v-else) Please select a ROI.
  .cell.cell-bottomright
    .box-title Visible Camera
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
</template>
  
<script>
import VideoCard from '@/components/camera-card.vue';
import { getCameras, getCameraSettings } from '@/api/cameras.api';
import { getRoiDataList } from '@/api/statistic.api';
import VChart from 'vue-echarts';
import VueAspectRatio from 'vue-aspect-ratio';
import socket from '@/mixins/socket';

export default {
name: 'Dashboard',
  components: {
    VideoCard,
    VChart,
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
    zones: [],
    selectedZoneIdx: null,
    loading: true,
    socketConnected: false
  };
},
computed: {
  selectedZone() {
    return this.selectedZoneIdx !== null ? this.zones[this.selectedZoneIdx] : null;
  },
  chartOption() {
    if (!this.selectedZone) return {};
    const temps = this.selectedZone.temps || [];
    return {
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: temps.map((t) => t.time.slice(11, 16)),
        name: '시간',
        boundaryGap: false
      },
      yAxis: {
        type: 'value',
        name: '온도(°C)',
        min: Math.min(...temps.map(t => t.value)) - 5,
        max: Math.max(...temps.map(t => t.value)) + 5
      },
      series: [
        {
          data: temps.map((t) => t.value),
          type: 'line',
          smooth: true,
          areaStyle: {
            opacity: 0.3
          },
          lineStyle: {
            width: 2
          },
          itemStyle: {
            borderWidth: 2
          },
          name: `${this.selectedZone.name} 온도(°C)`
        }
      ],
      grid: { 
        left: 40, 
        right: 20, 
        top: 30, 
        bottom: 30,
        containLabel: true
      }
    };
  }
},
mounted() {
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
},
beforeDestroy() {
  if (this.timeInterval) {
    clearInterval(this.timeInterval);
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
    this.currentTime = now.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  },
  async fetchWeather() {
    try {
      // TODO: 실제 날씨 API 연동
      this.weather = {
        temperature: '23',
        description: '맑음',
        location: '서울'
      };
    } catch (error) {
      console.error('날씨 정보를 가져오는데 실패했습니다:', error);
    }
  },
  async loadZones() {
    try {
      const res = await getRoiDataList();
      this.zones = res.data.result || [];
      if (this.zones.length > 0) {
        this.selectedZoneIdx = 0;
      }
    } catch (e) {
      console.error('영역 통계 정보를 불러오지 못했습니다:', e);
    }
  },
  selectZone(idx) {
    this.selectedZoneIdx = idx;
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
      this.thermalCamera = this.cameraList[0] || null;
      this.visibleCamera = this.cameraList[1] || null;
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
  }
}
};
</script>

<style scoped>
.dashboard-2by2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 16px;
  height: calc(100vh - 32px);
  background: #222;
  padding: 16px;
  overflow: hidden;
}

.cell {
  background: #333;
  border: 2px solid #555;
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
}

.bottomleft-inner-bottom {
  flex: 1;
  border-radius: 0 0 8px 8px;
  background: transparent;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.box-title {
  background: #666;
  color: #fff;
  font-weight: bold;
  padding: 8px 16px;
  border-bottom: 2px solid #555;
  border-radius: 8px 8px 0 0;
  flex-shrink: 0;
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
  width: 100%;
  height: 100%;
}

.video-container .video-card {
  width: 100%;
  height: 100%;
}

.time-display {
  background: #0066cc;
  color: white;
  padding: 20px;
  text-align: center;
  border-radius: 8px 8px 0 0;
  height: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.weather-widget {
  background: #1a1a1a;
  color: white;
  padding: 20px;
  text-align: center;
  border-radius: 0 0 8px 8px;
  height: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.weather-info {
  width: 100%;
}

.temperature {
  font-size: 2em;
  font-weight: bold;
  margin-bottom: 10px;
}

.weather-description {
  font-size: 1.2em;
  margin-bottom: 5px;
}

.location {
  font-size: 1em;
  color: #888;
}

.zone-table {
  width: 100%;
  border-collapse: collapse;
  background: #555;
  color: #fff;
  font-size: 1.1em;
  margin-top: 8px;
  flex-shrink: 0;
}

.zone-table th,
.zone-table td {
  padding: 8px 12px;
  text-align: center;
  white-space: nowrap;
}

.zone-table th {
  background: #444;
  font-weight: bold;
  position: sticky;
  top: 0;
  z-index: 1;
}

.zone-table tr {
  border-bottom: 1px solid #666;
  cursor: pointer;
}

.zone-table tr.selected,
.zone-table tr:hover {
  background: #666;
}

.icon-chart {
  font-size: 1.3em;
}

.icon-excel {
  font-size: 1.3em;
  color: #4caf50;
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
</style>
