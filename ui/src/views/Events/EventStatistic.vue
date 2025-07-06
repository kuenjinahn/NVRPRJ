<template lang="pug">
.event-statistic
  v-container.custom-container(fluid)
    v-row
      v-col(cols="12")
        v-card.mb-3
          v-card-title.d-flex.align-center.py-2
            v-icon.mr-2(color="primary" small) {{ icons.mdiChartLine }}
            span.subtitle-1 ROI별 실시간 온도 변화 추이
          v-card-text.pa-2
            v-chart(:options="eventTrendOption" autoresize height="400" ref="trendChart" style="width:100%;height:400px;background:var(--cui-bg-card);")

    v-row
      v-col(cols="12" md="6")
        v-card.mb-3(style="height: 500px")
          v-card-title.d-flex.align-center.py-2
            v-icon.mr-2(color="primary" small) {{ icons.mdiChartBar }}
            span.subtitle-1 ROI별 일일 평균 온도
          v-card-text.pa-2(style="height: calc(100% - 168px)")
            v-chart(:options="roiAvgTempOption" autoresize height="100%" ref="roiAvgTempChart" style="width:100%;height:100%;background:var(--cui-bg-card);")
      v-col(cols="12" md="6")
        v-card.mb-3(style="height: 500px")
          v-card-title.d-flex.align-center.py-2
            v-icon.mr-2(color="primary" small) {{ icons.mdiChartBar }}
            span.subtitle-1 ROI별 최소온도 변화율 TOP10
          v-card-text.pa-2(style="height: calc(100% - 168px)")
            v-data-table(
              :headers="roiMinChangeHeaders"
              :items="roiMinChange"
              class="elevation-1"
              dense
              style="height: 100%"
            )

    
</template>

<script>
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import {
  LineChart,
  BarChart,
  PieChart
} from 'echarts/charts';
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  ToolboxComponent,
  MarkLineComponent,
  VisualMapComponent
} from 'echarts/components';
import VChart from 'vue-echarts';
import { 
  mdiChartLine,
  mdiChartPie,
  mdiChartBar
} from '@mdi/js';
import { getRealtimeTemp, getDailyRoiAvgTemp, getDailyRoiMinChange } from '@/api/statistic.api';
import * as echarts from 'echarts';

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  ToolboxComponent,
  MarkLineComponent,
  VisualMapComponent
]);

export default {
  name: 'EventStatistic',

  components: {
    'v-chart': VChart
  },

  data: () => ({
    icons: {
      mdiChartLine,
      mdiChartPie,
      mdiChartBar
    },

    // 이벤트 발생 추이 차트 옵션
    eventTrendOption: {
      tooltip: { trigger: 'axis' },
      legend: { 
        data: Array.from({ length: 10 }, (_, i) => `ROI${i+1}`),
        textStyle: {
          color: '#fff'
        }
      },
      xAxis: { 
        type: 'category', 
        data: [],
        axisLabel: {
          color: '#fff'
        }
      },
      yAxis: { 
        type: 'value',
        axisLabel: {
          color: '#fff'
        }
      },
      series: Array.from({ length: 10 }, (_, i) => ({
        name: `ROI${i+1}`,
        type: 'line',
        data: []
      })),
      markLine: {
        data: [
          {
            name: '최대',
            type: 'max',
            lineStyle: {
              color: '#ff4d4f',
              type: 'dashed'
            },
            label: {
              formatter: '최대: {c}',
              color: '#fff'
            }
          },
          {
            name: '최소',
            type: 'min',
            lineStyle: {
              color: '#52c41a',
              type: 'dashed'
            },
            label: {
              formatter: '최소: {c}',
              color: '#fff'
            }
          },
          {
            name: '평균',
            type: 'average',
            lineStyle: {
              color: '#1890ff',
              type: 'dashed'
            },
            label: {
              formatter: '평균: {c}',
              color: '#fff'
            }
          }
        ]
      }
    },

    // 영상별 이벤트 발생 건수 파이 차트 옵션
    eventByVideoOption: {
      tooltip: {
        trigger: 'item'
      },
      legend: {
        orient: 'vertical',
        left: 'left'
      },
      series: [{
        name: '이벤트 발생 건수',
        type: 'pie',
        radius: '70%',
        data: [
          { value: 335, name: '영상 1' },
          { value: 310, name: '영상 2' },
          { value: 234, name: '영상 3' },
          { value: 135, name: '영상 4' }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    },

    // 온도 변화 추이 차트 옵션
    temperatureOption: {
      tooltip: {
        trigger: 'axis'
      },
      legend: {
        data: ['영상 1', '영상 2', '영상 3', '영상 4']
      },
      xAxis: {
        type: 'category',
        data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00']
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: '{value} °C'
        }
      },
      visualMap: {
        top: 50,
        right: 10,
        pieces: [{
          gt: 30,
          lte: 50,
          color: '#d94e5d'
        }, {
          gt: 10,
          lte: 30,
          color: '#50a3ba'
        }],
        outOfRange: {
          color: '#999'
        }
      },
      series: [{
        name: '영상 1',
        type: 'line',
        data: [25, 27, 31, 33, 32, 30]
      }, {
        name: '영상 2',
        type: 'line',
        data: [24, 25, 29, 32, 31, 28]
      }, {
        name: '영상 3',
        type: 'line',
        data: [23, 26, 30, 34, 33, 29]
      }, {
        name: '영상 4',
        type: 'line',
        data: [26, 28, 32, 35, 34, 31]
      }],
      markLine: {
        data: [{
          yAxis: 30,
          lineStyle: {
            color: '#d94e5d'
          },
          label: {
            formatter: '기준온도 (30°C)'
          }
        }]
      }
    },

    // 이벤트 처리 현황 막대 차트 옵션
    eventStatusBarOption: {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      legend: {
        data: ['처리', '미처리', '대기']
      },
      xAxis: {
        type: 'category',
        data: ['1주차', '2주차', '3주차', '4주차']
      },
      yAxis: {
        type: 'value'
      },
      series: [{
        name: '처리',
        type: 'bar',
        stack: 'total',
        data: [320, 302, 301, 334]
      }, {
        name: '미처리',
        type: 'bar',
        stack: 'total',
        data: [120, 132, 101, 134]
      }, {
        name: '대기',
        type: 'bar',
        stack: 'total',
        data: [220, 182, 191, 234]
      }]
    },

    // 이벤트 처리 현황 파이 차트 옵션
    eventStatusPieOption: {
      tooltip: {
        trigger: 'item'
      },
      legend: {
        orient: 'vertical',
        left: 'left'
      },
      series: [{
        name: '처리 현황',
        type: 'pie',
        radius: '70%',
        data: [
          { value: 1257, name: '처리' },
          { value: 487, name: '미처리' },
          { value: 827, name: '대기' }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    },

    roiAvgTempOption: {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      legend: {
        data: ['평균 온도'],
        textStyle: {
          color: '#fff'
        }
      },
      xAxis: {
        type: 'category',
        data: Array.from({ length: 10 }, (_, i) => `ROI${i+1}`),
        axisLabel: {
          color: '#fff'
        }
      },
      yAxis: {
        type: 'value',
        name: '온도 (°C)',
        axisLabel: {
          color: '#fff',
          formatter: '{value} °C'
        }
      },
      series: [{
        name: '평균 온도',
        type: 'bar',
        data: [],
        itemStyle: {
          color: '#1890ff'
        },
        label: {
          show: true,
          position: 'top',
          color: '#fff',
          formatter: '{c}°C'
        }
      }]
    },

    realtimeTemp: [],
    tempChart: null,
    tempChartOption: null,
    tempTimer: null,

    roiMinChange: [],
    roiMinChangeHeaders: [
      { text: 'NO', value: 'no', align: 'center' },
      { text: 'ROI 번호', value: 'roi', align: 'center' },
      { text: '평균온도', value: 'averageTemp', align: 'center' },
      { text: '최소온도', value: 'minTemp', align: 'center' },
      { text: '변화율(%)', value: 'changeRate', align: 'center' }
    ],
  }),

  mounted() {
    console.log('trendChart:', this.$refs.trendChart);
    console.log('videoChart:', this.$refs.videoChart);
    console.log('tempChart:', this.$refs.tempChart);
    console.log('barChart:', this.$refs.barChart);
    console.log('pieChart:', this.$refs.pieChart);
    this.loadRoiTempTrend();
    this.loadRoiAvgTemp();
    this.startTempTimer();
    this.loadRoiMinChange();
  },

  beforeDestroy() {
    if (this.tempChart) this.tempChart.dispose();
    this.stopTempTimer();
  },

  methods: {
    startTempTimer() {
      this.tempTimer = setInterval(() => {
        this.loadRoiTempTrend();
      }, 3000);
    },

    stopTempTimer() {
      if (this.tempTimer) {
        clearInterval(this.tempTimer);
        this.tempTimer = null;
      }
    },

    async loadRoiTempTrend() {
      try {
        const res = await getRealtimeTemp();
        const result = res.data.result || [];
        const xData = result.map(d => new Date(d.time).toLocaleTimeString());
        const roiSeries = Array.from({ length: 10 }, (_, i) =>
          result.map(d => d.rois[i])
        );

        // 최신 데이터의 min, max, avg 값 가져오기
        const latestData = result[0] || {};
        const minValue = latestData.min;
        const maxValue = latestData.max;
        const avgValue = latestData.avg;

        this.eventTrendOption = {
          tooltip: { trigger: 'axis' },
          legend: { 
            data: Array.from({ length: 10 }, (_, i) => `ROI${i+1}`),
            textStyle: {
              color: '#fff'
            }
          },
          xAxis: { 
            type: 'category', 
            data: xData,
            axisLabel: {
              color: '#fff'
            }
          },
          yAxis: { 
            type: 'value',
            axisLabel: {
              color: '#fff'
            }
          },
          series: roiSeries.map((data, i) => ({
            name: `ROI${i+1}`,
            type: 'line',
            data
          })),
          markLine: {
            data: [
              {
                name: '최대',
                yAxis: maxValue,
                lineStyle: {
                  color: '#ff4d4f',
                  type: 'dashed'
                },
                label: {
                  formatter: `최대: ${maxValue}°C`,
                  color: '#fff'
                }
              },
              {
                name: '최소',
                yAxis: minValue,
                lineStyle: {
                  color: '#52c41a',
                  type: 'dashed'
                },
                label: {
                  formatter: `최소: ${minValue}°C`,
                  color: '#fff'
                }
              },
              {
                name: '평균',
                yAxis: avgValue,
                lineStyle: {
                  color: '#1890ff',
                  type: 'dashed'
                },
                label: {
                  formatter: `평균: ${avgValue}°C`,
                  color: '#fff'
                }
              }
            ]
          }
        };
      } catch (e) {
        console.error('Error loading ROI temperature trend:', e);
      }
    },

    async loadRoiAvgTemp() {
      try {
        const res = await getDailyRoiAvgTemp();
        const result = res.data.result || [];
        
        this.roiAvgTempOption = {
          ...this.roiAvgTempOption,
          series: [{
            ...this.roiAvgTempOption.series[0],
            data: result.map(item => item.averageTemp)
          }]
        };
      } catch (e) {
        console.error('Error loading ROI average temperature:', e);
      }
    },

    initTempChart() {
      this.tempChart = echarts.init(this.$refs.tempChart);
      this.tempChartOption = {
        tooltip: { trigger: 'axis' },
        legend: { data: [
          ...Array.from({ length: 10 }, (_, i) => `ROI${i+1}`),
          '최소', '최대', '평균'
        ] },
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value' },
        series: [
          ...Array.from({ length: 10 }, (_, i) => ({
            name: `ROI${i+1}`,
            type: 'line',
            data: [],
          })),
          { name: '최소', type: 'line', data: [], lineStyle: { type: 'dashed' } },
          { name: '최대', type: 'line', data: [], lineStyle: { type: 'dashed' } },
          { name: '평균', type: 'line', data: [], lineStyle: { type: 'dashed' } },
        ]
      };
      this.tempChart.setOption(this.tempChartOption);
    },

    updateTempChart() {
      if (!this.tempChart) return;
      const xData = this.realtimeTemp.map(d => new Date(d.time).toLocaleTimeString());
      const roiSeries = Array.from({ length: 10 }, (_, i) =>
        this.realtimeTemp.map(d => d.rois[i])
      );
      const minSeries = this.realtimeTemp.map(d => d.min);
      const maxSeries = this.realtimeTemp.map(d => d.max);
      const avgSeries = this.realtimeTemp.map(d => d.avg);
      this.tempChart.setOption({
        xAxis: { data: xData },
        series: [
          ...roiSeries.map((data, i) => ({ name: `ROI${i+1}`, data })),
          { name: '최소', data: minSeries, lineStyle: { type: 'dashed' } },
          { name: '최대', data: maxSeries, lineStyle: { type: 'dashed' } },
          { name: '평균', data: avgSeries, lineStyle: { type: 'dashed' } },
        ]
      });
    },

    async loadRoiMinChange() {
      try {
        const res = await getDailyRoiMinChange();
        this.roiMinChange = res.data.result || [];
      } catch (e) {
        console.error('Error loading ROI min change:', e);
      }
    },
  }
};
</script>

<style lang="scss" scoped>
.event-statistic {
  .custom-container {
    width: 90% !important;
    max-width: 90% !important;
    flex: 0 0 90% !important;
    margin-left: 0 !important;
    padding-left: 0 !important;
  }

  .v-card {
    .v-card__title {
      font-size: 0.9rem;
      min-height: 120px;
    }
  }

  :deep(.echarts) {
    width: 100%;
    height: 100%;
  }
}
</style> 
