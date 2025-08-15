<template lang="pug">
.dashboard-2by2
  .cell.cell-topleft
    .topleft-inner-row
      .topleft-inner-left
        .time-display
          .site-time-block
            .site-name(v-if="location_info") {{ location_info }}
            .current-time {{ currentTime }}
        .weather-widget
          .weather-info
            .temperature {{ weather.temperature }}°C
            .weather-description {{ weather.description }}
            .location {{ weather.location }}
      .topleft-inner-right
        .gauge-container
          .gauge-meter(ref="gaugeChart" style="width:100%;height:180px;min-width:180px;min-height:180px;")
        .bottom-box
          .table-title 경보 이력
          .alert-table
            .table-header
              .header-cell 경보레벨
              .header-cell 발생일자
            .table-body
              .table-row(
                v-for="alert in alertHistory"
                :key="alert.id"
                :class="['alert-row', `level-${alert.level}`]"
                )
                .table-cell
                  span.level-icon(:class="`level-${alert.level}`")
                    span(v-if="alert.level == 4") ⚠️
                    span(v-else-if="alert.level == 3") 🔶
                    span(v-else-if="alert.level == 2") 🟡
                    span(v-else-if="alert.level == 1") 🟦
                    span(v-else) 🟩
                  span.level-text {{ getLevelText(alert.level) }}
                .table-cell {{ alert.time }}
  .cell.cell-topright
    .box-title 열화상 영상
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
                th Min Temp
                th Max Temp
                th Avg Temp
                th Graph
                th Download
            tbody
              tr(
                v-for="(zone, idx) in zones"
                :key="zone.name"
                :class="{selected: selectedZoneIdx === idx}"
                @click="showChart(zone)"
              )
                td {{ zone.zone_desc }}
                td {{ zone.maxTemp }}
                td {{ zone.minTemp }}
                td {{ zone.avgTemp }}
                td
                  span.icon-chart 📈
                td
                  span.icon-excel(@click.stop="downloadExcel(zone)") 📊
      .bottomleft-inner-bottom
        .box-title Time Series Temperature
        .chart-container
          v-chart(:options="chartOption" autoresize ref="trendChart" style="width:100%;height:160%;background:var(--cui-bg-card);")
  .cell.cell-bottomright
    .box-title 실화상 영상
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
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { BarChart, LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import VideoCard from '@/components/camera-card.vue';
import { getCameras, getCameraSettings } from '@/api/cameras.api';
import { getRoiDataList } from '@/api/statistic.api';
import VChart from 'vue-echarts';
import VueAspectRatio from 'vue-aspect-ratio';
import socket from '@/mixins/socket';
import * as XLSX from 'xlsx';
import * as echarts from 'echarts';
import { getAlerts} from '@/api/alerts.api';
import { getEventSetting } from '@/api/eventSetting.api.js'
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
    zones: [],
    selectedZoneIdx: null,
    selectedZone: null,
    loading: true,
    socketConnected: false,
    alertHistory: [],
    gaugeChart: null,
    location_info: '',
    address: '',
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
      return date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
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
        min: Math.min(...minTemps) - 5,
        max: Math.max(...maxTemps) + 5,
        axisLabel: {
          color: '#fff',
          formatter: '{value}°C'
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
        left: 40, 
        right: 20, 
        top: 60, 
        bottom: 60,
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
  this.initGaugeChart();
  this.initializeData();
  this.loadAlertHistory();
  this.loadSiteName();
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
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const day = now.getDate();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    
    this.currentTime = `${year}년 ${month}월 ${day}일 ${hours}:${minutes}:${seconds}`;
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
      }
    } catch (e) {
      console.error('영역 통계 정보를 불러오지 못했습니다:', e);
    }
  },
  selectZone(idx) {
    this.selectedZoneIdx = idx;
    this.selectedZone = this.zones[idx];
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
  downloadExcel(zone) {
    try {
      // Create worksheet data
      const worksheetData = [];
      
      // Add headers
      worksheetData.push(['시간', '최소온도 (°C)', '최대온도 (°C)', '평균온도 (°C)']);
      
      // Add data rows
      if (zone.temps && Array.isArray(zone.temps)) {
        zone.temps.forEach(temp => {
          worksheetData.push([
            new Date(temp.time).toLocaleString('ko-KR'),
            temp.min,
            temp.max,
            temp.avg
          ]);
        });
      }

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
    } catch (error) {
      console.error('Error downloading Excel:', error);
      this.$toast.error('Excel 다운로드 중 오류가 발생했습니다.');
    }
  },
  showChart(zone) {
    console.log('Selected Zone Data:', zone);
    this.selectedZone = zone;
    const index = this.zones.findIndex(z => z.zone_desc === zone.zone_desc);
    if (index !== -1) {
      this.selectedZoneIdx = index;
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
        }
      } catch (error) {
        console.error('알림 이력 조회 실패:', error);
        this.$toast?.error('알림 이력을 불러오는 중 오류가 발생했습니다.');
      }
    },
    formatDate(dateStr) {
      const date = new Date(dateStr);
      const now = new Date();
      const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
      
      // 오늘인 경우
      if (diffDays === 0) {
        return date.toLocaleTimeString('ko-KR', { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false 
        });
      }
      
      // 어제인 경우
      if (diffDays === 1) {
        return '어제 ' + date.toLocaleTimeString('ko-KR', { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false 
        });
      }
      
      // 이번 주인 경우
      if (diffDays < 7) {
        const days = ['일', '월', '화', '수', '목', '금', '토'];
        return days[date.getDay()] + ' ' + date.toLocaleTimeString('ko-KR', { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false 
        });
      }
      
      // 그 외의 경우
      return date.toLocaleDateString('ko-KR', { 
        month: '2-digit', 
        day: '2-digit' 
      }) + ' ' + date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
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
    async loadSiteName() {
      try {
        const data = await getEventSetting();
        if (data && data.system_json) {
          const system = JSON.parse(data.system_json);
          this.location_info = system.location_info || '';
          this.address = system.address || '';
          this.weather.location = system.address || '';
        }
      } catch (e) {
        this.location_info = '';
        this.address = '';
      }
    },
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
  margin-top: 10px;

  th, td {
    padding: 8px;
    text-align: center;
    border-bottom: 1px solid #555;
  }

  th {
    background: #444;
    color: #fff;
  }

  tr {
    cursor: pointer;
    transition: background-color 0.3s;

    &:hover {
      background-color: #333;
    }

    &.selected {
      background-color: #2c2c2c;
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
  padding: 2vw 1vw 1vw 1vw;
  background: var(--cui-bg-card);
  border-radius: 0 0 8px 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0;
  height: 28vh;

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

.site-time-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.site-name {
  white-space: pre-line;
  word-break: break-all;
  max-width: 180px;
  font-size: 22px;
  color: #fff;
  line-height: 1.3;
  text-align: left;
  display: block;
}

.current-time {
  font-size: 22px;
  color: #ccc;
  line-height: 1.2;
  text-align: left;
  display: block;
}
</style>
