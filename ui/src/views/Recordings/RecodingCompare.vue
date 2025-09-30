<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.recording-compare
  v-container(fluid)
    v-row
      v-col(cols="12")
        .tw-flex.tw-gap-4
          // 첫 번째 비디오 플레이어
          .video-player.tw-flex-1(:class="{ expanded: expandedVideo === 1 }")
            video(
              ref="videoPlayer1"
              controls
              :src="selectedVideo1"
              @error="handleVideoError"
              @loadeddata="handleVideoLoaded"
              crossorigin="anonymous"
              preload="metadata"
              :style="expandedVideo === 1 ? 'width: 1280px; height: 720px;' : 'width: 640px; height: 480px;'"
            )
          
          // 두 번째 비디오 플레이어
          .video-player.tw-flex-1(:class="{ expanded: expandedVideo === 2 }")
            video(
              ref="videoPlayer2"
              controls
              :src="selectedVideo2"
              @error="handleVideoError"
              @loadeddata="handleVideoLoaded"
              crossorigin="anonymous"
              preload="metadata"
              :style="expandedVideo === 2 ? 'width: 1280px; height: 720px;' : 'width: 640px; height: 480px;'"
            )
          
          // 세 번째 박스 (컨트롤 + 카메라 목록 + 달력)
          .tw-flex-1.tw-flex
            // 왼쪽 박스 (컨트롤만)
            .tw-flex-1.tw-flex.tw-flex-col.tw-gap-4
              // 컨트롤 버튼 박스
              .button-box.button-box-dark.tw-p-4
                .tw-flex.tw-flex-col.tw-gap-2
                  v-btn.control-btn.common-dark-btn(color="gray" @click="togglePauseAllVideos")
                    v-icon(left class="common-dark-btn__icon") {{ isPaused ? icons.mdiPlay : icons.mdiPause }}
                    span {{ isPaused ? '재생' : '일시정지' }}
                  v-btn.control-btn.common-dark-btn(color="gray" @click="stopAllVideos")
                    v-icon(left class="common-dark-btn__icon") {{ icons.mdiStop }}
                    span 중지
            
            // 오른쪽 박스 (달력)
            .tw-w-96.tw-ml-4
              .button-box.button-box-dark.tw-p-4.tw-h-full
                v-date-picker(
                  v-model="selectedDate"
                  :first-day-of-week="1"
                  locale="ko"
                  color="secondary"
                  elevation="0"
                  full-width
                  no-title
                  @change="handleDateChange"
                )
              // 달력 아래 버튼 박스
              .tw-mt-5-tw-w-full.tw-bg-gray-900.tw-rounded.tw-p-5
                <!-- v-btn.export-btn.tw-mb-2.tw-w-full(color="secondary" @click="onExportRecording") 녹화내보내기 -->
                v-btn.snapshot-btn.tw-w-full(color="secondary" @click="onSaveSnapshot") 정지이미지 저장

        // 🕐 타임라인 영역 표시
        .tw-mt-4
          .timeline-section.tw-bg-gray-800.tw-p-4.tw-rounded-lg
            // 타임라인 제목 및 현재 시간
            .timeline-header.tw-flex.tw-justify-between.tw-items-center.tw-mb-4
              h3.tw-text-white.tw-text-lg.tw-font-semibold 🕐 타임라인 영역
              .current-time-display.tw-text-white.tw-text-lg.tw-font-bold.tw-bg-gray-800.tw-px-3.tw-py-2.tw-rounded.tw-border.tw-border-gray-600.tw-font-mono
                | {{ formattedPlayheadTime }}
            
            // NLE 타임라인 박스
            .nle-timeline-box.tw-bg-gray-700.tw-p-4.tw-rounded-lg.tw-flex.tw-items-center.tw-relative
              // NLE 슬라이더
              .timeline-slider.tw-flex-1.tw-relative(@click="handleTimelineClick")
                // 시간 눈금 (24시간)
                .timeline-hours.tw-relative.tw-h-6.tw-mb-2
                  span(
                    v-for="h in 25"
                    :key="h"
                    :style="{ position: 'absolute', left: `calc(${(h-1)/24*100}% - 15px)` }"
                    class="tw-text-xs tw-text-gray-400 tw-font-medium"
                  ) {{ h-1 }}:00
                
                // 통합 비디오 타임라인
                .timeline-videos.tw-relative.tw-h-8
                  .timeline-bar.tw-relative.tw-h-6.tw-bg-gray-600.tw-rounded.tw-mr-2
                    // 첫 번째 카메라의 모든 비디오 구간 표시
                    .timeline-segment.tw-absolute.tw-h-full.tw-rounded.tw-bg-blue-500.tw-border-2.tw-border-blue-300.tw-cursor-pointer(
                      v-for="segment in getFirstVideoSegments()"
                      :key="segment.startTime + '-' + segment.endTime"
                      :style="segmentStyle(segment)"
                      :title="`${formatTime(segment.startTime)} ~ ${formatTime(segment.endTime)}`"
                      @click.stop="selectVideoBySegment(segment)"
                    )
                
                // 수직 스크롤 바 (현재 위치)
                .vertical-bar(
                  :style="verticalBarStyle" 
                  @mousedown="startVerticalBarDrag"
                  class="tw-absolute tw-top-0 tw-w-1 tw-h-full tw-bg-red-500 tw-cursor-pointer tw-z-10"
                  :title="`현재 위치: ${formattedPlayheadTime}`"
                )


        // 데이터 테이블 (체크박스 제거, row 클릭 이벤트 추가)
        v-card.mt-4
          v-data-table(
            :headers="tableHeaders"
            :items="formattedRecordingHistory"
            :loading="loading"
            :items-per-page="4"
            class="elevation-1 recording-table"
            @click:row="handleTableRowClick"
            :item-class="getRowClass"
            ref="dataTable"
          )
            template(#item.cameraName="{ item }")
              span {{ getShortCameraName(item.cameraName) }}
            
            template(#item.formattedStartTime="{ item }")
              span {{ formatTime2(item.formattedStartTime) }}
            
            template(#item.formattedEndTime="{ item }")
              span {{ formatTime2(item.formattedEndTime) }}
            
            template(#item.filename="{ item }")
              span {{ getShortFilename(item.filename) }}
            
            template(#item.fileSize="{ item }")
              span {{ formatFileSize(item.fileSize) }}
            
            template(#item.download="{ item }")
              v-btn(
                color="primary"
                small
                @click.stop="downloadVideo(item)"
                :loading="downloadingVideos.includes(item.id)"
              )
                v-icon(left small) {{ icons.mdiDownload }}
                | 다운로드
            
            template(#body="{ items }")
              tbody
                tr(
                  v-for="item in items"
                  :key="item.id"
                  :data-id="item.id"
                  @click="handleTableRowClick(item)"
                  :class="getRowClass(item)"
                )
                  td {{ getShortCameraName(item.cameraName) }}
                  td {{ formatTime2(item.formattedStartTime) }}
                  td {{ formatTime2(item.formattedEndTime) }}
                  td {{ getShortFilename(item.filename) }}
                  td {{ formatFileSize(item.fileSize) }}
                  td
                    v-btn(
                      color="secondary"
                      small
                      @click.stop="downloadVideo(item)"
                      :loading="downloadingVideos.includes(item.id)"
                    )
                      v-icon(left small) {{ icons.mdiDownload }}
                      | 다운로드
            
            template(#no-data)
              .text-center.pa-4
                v-icon(color="grey" size="40") {{ icons.mdiVideo }}
                .mt-2 녹화 기록이 없습니다.

</template>

<script>
import { 
  mdiVideo, 
  mdiFile, 
  mdiCalendar, 
  mdiMagnify, 
  mdiRefresh,
  mdiCheckboxMarkedCircle,
  mdiClose,
  mdiClockOutline,
  mdiDelete,
  mdiPlay,
  mdiStop,
  mdiPause,
  mdiDownload
} from '@mdi/js'
import moment from 'moment';
import { getRecordingHistory, getRecordingSegments } from '@/api/recordingService.api.js';
import { getApiBaseUrl } from '@/config/api.config.js';

const API_BASE_URL = getApiBaseUrl();
export default {
  name: 'RecodingCompare',

  components: {},

  props: {},

  data: () => ({
        icons: {
      mdiVideo, 
      mdiFile, 
      mdiCalendar, 
      mdiMagnify, 
      mdiRefresh,
      mdiCheckboxMarkedCircle,
      mdiClose,
      mdiClockOutline,
      mdiDelete,
      mdiPlay,
      mdiStop,
      mdiPause,
      mdiDownload
    },
    loading: false,
    recordingHistory: [],
    selectedVideo1: null,
    selectedVideo2: null,

    // 테이블용 헤더 (체크박스 제거, 타입/상태 제거, 다운로드 추가)
    tableHeaders: [
      { text: '카메라', value: 'cameraName', sortable: true },
      { text: '시작 시간', value: 'formattedStartTime', sortable: true },
      { text: '종료 시간', value: 'formattedEndTime', sortable: true },
      { text: '파일명', value: 'filename', sortable: true },
      { text: '파일 크기', value: 'fileSize', sortable: true },
      { text: '다운로드', value: 'download', sortable: false, width: '120px' }
    ],
    statusOptions: [
      { text: '녹화중', value: 'recording' },
      { text: '완료', value: 'completed' },
      { text: '오류', value: 'error' },
      { text: '중지됨', value: 'stopped' }
    ],
    videoDialog: false,
    selectedVideo: null,
    videoUrl: null,
    videoError: null,
    thumbnailErrors: {},
    imageData: new Map(),
    searchFilters: {
      dateRange: [],
      dateRangeText: '',
      status: null
    },
    expandedVideo: 0,
    isPaused: true,

    selectedDate: new Date().toISOString().substr(0, 10),
    playhead: 0, // 0~1 (0=00:00, 1=24:00)
    dragging: false,
    selectedVideos: [],
    thumbnailUrl: '',
    verticalBarPercent: 50, // 0~100, 디폴트 중앙
    draggingVerticalBar: false,
    timelineUpdateTimer: null, // 타임라인 업데이트 타이머
    isTimelineUpdating: false, // 타임라인 업데이트 중 플래그
    activeVideoIds: [], // 현재 활성화된 비디오 ID들
    downloadingVideos: [], // 다운로드 중인 비디오 ID들
    
    // 🕐 타임라인 영역 관련 변수들
    timelineStartTime: null, // 전체 영상 시작 시간
    timelineEndTime: null,   // 전체 영상 종료 시간
    timelineDuration: 0,     // 전체 영상 지속 시간 (초)
  }),

  computed: {
    formattedRecordingHistory() {
      if (!this.recordingHistory || this.recordingHistory.length === 0) {
        return [];
      }

      // API 응답 데이터를 테이블 표시용으로 포맷팅
      const formattedData = this.recordingHistory.map((record) => ({
        ...record,
        // 기존 필드들 유지
        id: record.id,
        cameraId: record.cameraId,
        cameraName: record.cameraName,
        filename: record.filename,
        startTime: record.startTime,
        endTime: record.endTime,
        duration: record.duration,
        fileSize: record.fileSize,
        status: record.status,
        filePath: record.filePath,
        streamUrl: record.streamUrl,
        fileType: record.fileType,
        // 포맷팅된 시간 필드 추가
        formattedStartTime: this.formatTime(record.startTime),
        formattedEndTime: this.formatTime(record.endTime)
      }));

      return formattedData;
    },
    formattedPlayheadTime() {
      // verticalBarPercent를 기준으로 계산 (0-24시간)
      const seconds = Math.round((this.verticalBarPercent / 100) * 86400);
      return this.secondsToTime(seconds);
    },
    playheadStyle() {
      return {
        left: `calc(${this.playhead * 100}% - 1px)`
      };
    },
    verticalBarStyle() {
      return {
        left: `calc(${this.verticalBarPercent}% - 2px)`, // 2px은 바의 절반
        width: '4px',
        background: 'red',
        position: 'absolute',
        top: 0,
        bottom: 0,
        zIndex: 10,
        cursor: 'ew-resize'
      };
    },

    // 카메라별로 그룹화하고 시간순으로 정렬된 녹화 기록
    groupedRecordingHistory() {
      if (!this.recordingHistory || this.recordingHistory.length === 0) {
        return {};
      }

      // 카메라별로 그룹화
      const grouped = {};
      this.recordingHistory.forEach(record => {
        const cameraName = record.cameraName || 'Unknown Camera';
        if (!grouped[cameraName]) {
          grouped[cameraName] = [];
        }
        grouped[cameraName].push(record);
      });

      // 각 카메라별로 시간순 정렬
      Object.keys(grouped).forEach(cameraName => {
        grouped[cameraName].sort((a, b) => {
          const timeA = new Date(a.startTime).getTime();
          const timeB = new Date(b.startTime).getTime();
          return timeA - timeB;
        });
      });

      return grouped;
    },

    // 카메라별 그룹화된 녹화 기록을 배열로 변환 (UI 표시용)
    cameraGroups() {
      const grouped = this.groupedRecordingHistory;
      return Object.keys(grouped).map(cameraName => ({
        cameraName,
        recordings: grouped[cameraName]
      }));
    },

    // 🕐 타임라인 영역 계산 속성들
    // 전체 영상의 시작 시간 (가장 빠른 시작 시간)
    computedTimelineStartTime() {
      if (!this.recordingHistory || this.recordingHistory.length === 0) {
        return null;
      }
      
      const startTimes = this.recordingHistory.map(record => new Date(record.startTime));
      return new Date(Math.min(...startTimes));
    },

    // 전체 영상의 종료 시간 (가장 늦은 종료 시간)
    computedTimelineEndTime() {
      if (!this.recordingHistory || this.recordingHistory.length === 0) {
        return null;
      }
      
      const endTimes = this.recordingHistory.map(record => new Date(record.endTime));
      return new Date(Math.max(...endTimes));
    },

    // 전체 영상의 지속 시간 (초)
    computedTimelineDuration() {
      if (!this.computedTimelineStartTime || !this.computedTimelineEndTime) {
        return 0;
      }
      
      return Math.round((this.computedTimelineEndTime - this.computedTimelineStartTime) / 1000);
    },


  },

  watch: {
    'searchFilters.dateRange': {
      handler(newRange) {
        if (newRange.length === 2) {
          const [start, end] = newRange;
          this.searchFilters.dateRangeText = `${start} ~ ${end}`;
        } else {
          this.searchFilters.dateRangeText = '';
        }
      },
      deep: true
    },
    selectedVideo1() {
      this.setupVideoPlayer1();
    },
    selectedVideo2() {
      this.setupVideoPlayer2();
    },
    
    // 🕐 녹화 기록이 변경될 때 타임라인 정보 업데이트
    recordingHistory: {
      handler(newHistory) {
        if (newHistory && newHistory.length > 0) {
          this.updateTimelineInfo();
        }
      },
      deep: true
    },

    // activeVideoIds 변경 감지 및 디버깅
    activeVideoIds: {
      handler(newIds, oldIds) {
        console.log('activeVideoIds changed:', {
          old: oldIds,
          new: newIds,
          formattedRecordingHistory: this.formattedRecordingHistory.map(item => ({ id: item.id, cameraName: item.cameraName }))
        });
        // 테이블의 행 스타일만 업데이트 (페이지 상태 유지)
        this.$nextTick(() => {
          this.updateTableRowStyles();
        });
      },
      deep: true
    }
  },

  created() {
    // 초기 날짜로 녹화 기록 로드
    if (this.selectedDate) {
      this.fetchRecordingHistoryForDate(this.selectedDate);
    }
  },

  mounted() {
    //this.fetchRecordingHistory();
    document.addEventListener('mousemove', this.onDrag);
    document.addEventListener('mouseup', this.stopDrag);
    // 키보드 이벤트 리스너 추가
    document.addEventListener('keydown', this.handleKeyDown);
    // 중앙에 위치
    this.verticalBarPercent = 50;
    
    // MP4 비디오 지원 확인
    const video = document.createElement('video');
    if (!video.canPlayType('video/mp4')) {
      this.$toast.warning('이 브라우저에서는 MP4 재생을 지원하지 않습니다. 최신 브라우저를 사용해주세요.');
    }
  },

  beforeDestroy() {
    // 비디오 플레이어 정리
    if (this.$refs.videoPlayer1) {
      this.$refs.videoPlayer1.pause();
      this.$refs.videoPlayer1.src = '';
      this.$refs.videoPlayer1.load();
    }
    if (this.$refs.videoPlayer2) {
      this.$refs.videoPlayer2.pause();
      this.$refs.videoPlayer2.src = '';
      this.$refs.videoPlayer2.load();
    }
    
    // 메모리 정리
    if (this.imageData) {
      this.imageData.clear();
    }
    
    // 이벤트 리스너 제거
    document.removeEventListener('mousemove', this.onDrag);
    document.removeEventListener('mouseup', this.stopDrag);
    document.removeEventListener('keydown', this.handleKeyDown);
    
    // 타임라인 업데이트 타이머 정리
    this.stopTimelineUpdate();
  },

  methods: {
    async loadRecordingHistory() {
      try {
        this.loading = true;
        const response = await getRecordingHistory();
        if (response && Array.isArray(response)) {
          this.recordingHistory = response.map(record => {
            const data = record.dataValues || record;
            return {
              ...data,
              id: data.id || '',
              cameraName: data.cameraName || data.camera_name || 'Unknown Camera',
              filename: data.filename || 'Unknown File',
              startTime: data.startTime || data.start_time || new Date().toISOString(),
              endTime: data.endTime || data.end_time || null,
              status: data.status || 'error',
            selected: false
            };
          });
        } else {
          this.recordingHistory = [];
          console.error('Invalid response format:', response);
        }
      } catch (error) {
        console.error('Error loading recording history:', error);
        this.recordingHistory = [];
      } finally {
        this.loading = false;
      }
    },

    async fetchRecordingHistory() {
      this.loading = true;
      try {
        const response = await getRecordingHistory();
        console.log('Recording history response:', response);
        
        if (Array.isArray(response)) {
          this.recordingHistory = response.map(record => {
            const data = record.dataValues || record;
            return {
              ...data,
              id: data.id || '',
              cameraName: data.cameraName || data.camera_name || 'Unknown Camera',
              filename: data.filename || 'Unknown File',
              startTime: data.startTime || data.start_time || new Date().toISOString(),
              endTime: data.endTime || data.end_time || null,
              status: data.status || 'error',
            selected: false
            };
          });
          
          // 🕐 녹화 기록 로드 후 타임라인 정보 업데이트
          this.updateTimelineInfo();
        } else {
          this.recordingHistory = [];
          console.error('Invalid response format:', response);
        }
      } catch (error) {
        console.error('Failed to fetch recording history:', error);
        this.recordingHistory = [];
      } finally {
        this.loading = false;
      }
    },

    handleSelectionChange(item) {
      console.log('===> handleSelectionChange :',item.id);
      if (item.selected) {
        if (!this.selectedVideo1) {
          // MP4 파일 직접 스트리밍으로 변경
          this.selectedVideo1 = `${API_BASE_URL}/recordings/stream/${item.id}`;
          // 일반 HTML5 비디오 플레이어 사용 (HLS 플레이어 불필요)
          this.$nextTick(() => {
            this.setupVideoPlayer1();
          });
        } else if (!this.selectedVideo2) {
          // MP4 파일 직접 스트리밍으로 변경
          this.selectedVideo2 = `${API_BASE_URL}/recordings/stream/${item.id}`;
          // 일반 HTML5 비디오 플레이어 사용 (HLS 플레이어 불필요)
          this.$nextTick(() => {
            this.setupVideoPlayer2();
          });
        } else {
          item.selected = false;
          this.$toast.warning('최대 2개의 영상만 선택할 수 있습니다.');
        }
      } else {
        if (this.selectedVideo1 === `${API_BASE_URL}/recordings/stream/${item.id}`) {
          this.selectedVideo1 = null;
          // 비디오 플레이어 정리
          if (this.$refs.videoPlayer1) {
            this.$refs.videoPlayer1.src = '';
            this.$refs.videoPlayer1.load();
          }
        } else if (this.selectedVideo2 === `${API_BASE_URL}/recordings/stream/${item.id}`) {
          this.selectedVideo2 = null;
          // 비디오 플레이어 정리
          if (this.$refs.videoPlayer2) {
            this.$refs.videoPlayer2.src = '';
            this.$refs.videoPlayer2.load();
          }
        }
      }
    },

    // 새로운 MP4 비디오 플레이어 설정 메서드
    setupVideoPlayer1() {
      if (this.$refs.videoPlayer1 && this.selectedVideo1) {
        const videoElement = this.$refs.videoPlayer1;
        videoElement.src = this.selectedVideo1;
        videoElement.load();
        
        // 비디오 로드 완료 시 이벤트 리스너
        videoElement.addEventListener('loadeddata', () => {
          console.log('Video 1 loaded successfully');
        });
        
        videoElement.addEventListener('error', (e) => {
          console.error('Video 1 load error:', e);
          this.$toast.error('비디오 1을 로드할 수 없습니다.');
        });
      }
    },

    setupVideoPlayer2() {
      if (this.$refs.videoPlayer2 && this.selectedVideo2) {
        const videoElement = this.$refs.videoPlayer2;
        videoElement.src = this.selectedVideo2;
        videoElement.load();
        
        // 비디오 로드 완료 시 이벤트 리스너
        videoElement.addEventListener('loadeddata', () => {
          console.log('Video 2 loaded successfully');
        });
        
        videoElement.addEventListener('error', (e) => {
          console.error('Video 2 load error:', e);
          this.$toast.error('비디오 2를 로드할 수 없습니다.');
        });
      }
    },



    togglePauseAllVideos() {
      if (this.isPaused) {
        // 재생 전에 수직바 위치를 기준으로 비디오 시간 설정
        if (!this.syncVideosToTimelinePosition()) {
          return; // 범위 밖에 있으면 재생하지 않음
        }
        
        // 두 비디오 모두 재생
        if (this.$refs.videoPlayer1) {
          this.$refs.videoPlayer1.play().catch(error => {
            console.error('Error playing video 1:', error);
          });
        }
        
        if (this.$refs.videoPlayer2) {
          this.$refs.videoPlayer2.play().catch(error => {
            console.error('Error playing video 2:', error);
          });
        }
        
        this.startTimelineUpdate();
      } else {
        // 두 비디오 모두 일시정지
        if (this.$refs.videoPlayer1) {
          this.$refs.videoPlayer1.pause();
        }
        
        if (this.$refs.videoPlayer2) {
          this.$refs.videoPlayer2.pause();
        }
        
        this.stopTimelineUpdate();
      }
      this.isPaused = !this.isPaused;
    },

    stopAllVideos() {
      // 두 비디오 모두 중지
      if (this.$refs.videoPlayer1) {
        this.$refs.videoPlayer1.pause();
        this.$refs.videoPlayer1.currentTime = 0;
      }
      
      if (this.$refs.videoPlayer2) {
        this.$refs.videoPlayer2.pause();
        this.$refs.videoPlayer2.currentTime = 0;
      }
      
      this.stopTimelineUpdate();
      // 타임라인을 가장 빠른 비디오의 시작 위치로 리셋
      this.resetTimelineToEarliestVideo();
    },

    formatTime(date) {
      if (!date) return '';
      try {
        return moment(date).format('YYYY-MM-DD HH:mm:ss');
      } catch (error) {
        console.error('Error formatting date:', error);
        return date;
      }
    },
    formatTime2(date) {
      if (!date) return '';
      try {
        return moment(date).format('YYYY-MM-DD HH:mm:ss');
      } catch (error) {
        console.error('Error formatting date:', error);
        return date;
      }
    },
    getStatusColor(status) {
      const statusMap = {
        recording: 'blue',
        completed: 'green',
        error: 'red',
        stopped: 'grey'
      };
      return statusMap[status] || 'grey';
    },

    getStatusText(status) {
      const statusOption = this.statusOptions.find(opt => opt.value === status);
      return statusOption ? statusOption.text : status;
    },

    formatFileSize(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    getShortFilename(filename) {
      if (!filename) return 'Unknown File';
      
      // 전체 경로에서 파일명만 추출
      const pathParts = filename.split('/');
      const fileName = pathParts[pathParts.length - 1];
      
      // segment_000.mp4 형태로 표시
      return fileName;
    },

    getShortCameraName(cameraName) {
      if (!cameraName) return 'Unknown Camera';
      
      // 카메라 이름을 간단하게 표시 (예: "댐영상1" -> "댐1")
      if (cameraName.includes('댐영상')) {
        return cameraName.replace('댐영상', '댐');
      }
      
      return cameraName;
    },

    handleVideoError(event) {
      console.error('Video error:', event);
      const videoElement = event.target;
      
      // MP4 파일 에러 처리
      this.$toast.error('비디오를 재생할 수 없습니다. 파일이 손상되었거나 지원되지 않는 형식일 수 있습니다.');
      
      // 재시도 로직
      setTimeout(() => {
        if (videoElement === this.$refs.videoPlayer1 && this.selectedVideo1) {
          this.setupVideoPlayer1();
        } else if (videoElement === this.$refs.videoPlayer2 && this.selectedVideo2) {
          this.setupVideoPlayer2();
        }
      }, 2000);
    },

    handleVideoLoaded(event) {
      // 비디오가 로드되면 첫 프레임으로 이동
      const video = event.target;
      
      // MP4 파일의 경우 메타데이터 로드 후에 currentTime 설정
      if (video.readyState >= 1) {
        video.currentTime = 0;
      }
    },

    handleThumbnailError(item) {
      console.warn(`Failed to load thumbnail for recording: ${item.id}`);
      this.$set(this.thumbnailErrors, item.id, true);
      this.$set(this.thumbnails, item.id, '/assets/images/no-thumbnail.jpg');
    },

    // 컴포넌트가 업데이트될 때 캔버스 다시 그리기
    updateCanvases() {
      this.$nextTick(() => {
        Object.entries(this.thumbnails).forEach(([recordId, imageBitmap]) => {
          if (imageBitmap instanceof ImageBitmap) {
            const canvas = document.getElementById(`thumbnail-${recordId}`);
            if (canvas) {
              const ctx = canvas.getContext('2d');
              ctx.clearRect(0, 0, canvas.width, canvas.height);
              
              // 캔버스 크기에 맞게 이미지 그리기
              const scale = Math.min(
                canvas.width / imageBitmap.width,
                canvas.height / imageBitmap.height
              );
              
              const x = (canvas.width - imageBitmap.width * scale) / 2;
              const y = (canvas.height - imageBitmap.height * scale) / 2;
              
              ctx.drawImage(
                imageBitmap,
                x, y,
                imageBitmap.width * scale,
                imageBitmap.height * scale
              );
            }
          }
        });
      });
    },

    expandVideo(idx) {
      this.expandedVideo = this.expandedVideo === idx ? 0 : idx;
    },



    async handleDateChange(date) {
      // 날짜 변경 처리
      console.log('Selected date:', date);
      // 날짜만으로 녹화 기록을 조회 (카메라 선택과 무관)
      await this.fetchRecordingHistoryForDate(date);
    },

    async fetchRecordingHistoryForDate(date) {
      this.loading = true;
      try {
        // 비디오 플레이어 초기화
        this.selectedVideos = [];
        this.selectedVideo1 = null;
        this.selectedVideo2 = null;
        this.recordingHistory = [];
        this.activeVideoIds = []; // 활성 비디오 ID 초기화
        
        // 비디오 요소 정리
        if (this.$refs.videoPlayer1) {
          this.$refs.videoPlayer1.src = '';
          this.$refs.videoPlayer1.load();
        }
        if (this.$refs.videoPlayer2) {
          this.$refs.videoPlayer2.src = '';
          this.$refs.videoPlayer2.load();
        }

        // 새로운 segments API를 사용하여 MP4 파일 목록 조회
        // 여러 카메라의 file_path를 사용하여 정확한 파일 경로로 검색
        const filePaths = [
          `./outputs/nvr/recordings/camera1/${date}/segment_000.mp4`,
          `./outputs/nvr/recordings/camera2/${date}/segment_000.mp4`
        ];
        
        // 첫 번째 file_path로 검색 시도
        let response = await getRecordingSegments(date, filePaths[0]);
        
        // 결과가 없으면 두 번째 file_path로 시도
        if (!response || !response.segments || response.segments.length === 0) {
          response = await getRecordingSegments(date, filePaths[1]);
        }
        
        if (response && response.segments && Array.isArray(response.segments)) {
          // 모든 segment 파일을 표시 (최대 제한 없음)
          this.recordingHistory = response.segments.map(segment => ({
            id: segment.id,
            cameraId: segment.cameraId,
            cameraName: segment.cameraName,
            filename: segment.filename,
            startTime: segment.startTime,
            endTime: segment.endTime,
            duration: segment.duration,
            fileSize: segment.fileSize,
            status: segment.status,
            filePath: segment.filePath,
            streamUrl: segment.streamUrl,
            fileType: segment.fileType,
            selected: false
          }));

          // 녹화 기록이 있으면 카메라별로 그룹화하여 자동 선택
          if (this.recordingHistory.length > 0) {
            // 카메라별로 그룹화된 데이터를 사용하여 자동 선택
            const cameraGroups = this.cameraGroups;
            
            if (cameraGroups.length > 0) {
              // 첫 번째 카메라의 첫 번째 영상을 왼쪽 플레이어에
              if (cameraGroups[0].recordings.length > 0) {
                const firstVideo = cameraGroups[0].recordings[0];
                this.selectedVideo1 = firstVideo.streamUrl;
                this.selectedVideos.push({
                  ...firstVideo,
                  segments: [{ startTime: firstVideo.startTime, endTime: firstVideo.endTime }]
                });
                this.activeVideoIds.push(firstVideo.id); // 활성 비디오 ID 추가
              }
              
              // 두 번째 카메라의 첫 번째 영상을 오른쪽 플레이어에 (있는 경우)
              if (cameraGroups.length > 1 && cameraGroups[1].recordings.length > 0) {
                const secondVideo = cameraGroups[1].recordings[0];
                this.selectedVideo2 = secondVideo.streamUrl;
                this.selectedVideos.push({
                  ...secondVideo,
                  segments: [{ startTime: secondVideo.startTime, endTime: secondVideo.endTime }]
                });
                this.activeVideoIds.push(secondVideo.id); // 활성 비디오 ID 추가
              }
              
              // 타임라인을 가장 빠른 비디오의 시작 위치로 설정
              this.$nextTick(() => {
                this.resetTimelineToEarliestVideo();
              });
            }
          }
          
          // 🕐 녹화 기록 로드 후 타임라인 정보 업데이트
          this.updateTimelineInfo();
          
          // 총 segment 파일 수 표시
          console.log(`Found ${response.totalSegments} MP4 segment files for ${date}`);
          if (response.totalSegments > 0) {
            this.$toast.success(`${date} 날짜에 ${response.totalSegments}개의 녹화 파일을 찾았습니다.`);
          }
        } else {
          this.recordingHistory = [];
          console.warn('No segments found or invalid response format:', response);
        }
      } catch (error) {
        console.error('Failed to fetch recording segments:', error);
        this.recordingHistory = [];
        this.$toast.error('녹화 파일을 불러오는데 실패했습니다.');
      } finally {
        this.loading = false;
      }
    },

    // 타임라인에 표시할 segment 스타일 계산
    segmentStyle(segment) {
      try {
        // ISO 문자열을 Date 객체로 변환
        const start = new Date(segment.startTime);
        const end = new Date(segment.endTime);

        // 0시 기준 초 단위로 변환 (UTC 기준, 9시간 추가)
        const startSeconds = (start.getUTCHours() + 9) * 3600 + start.getUTCMinutes() * 60 + start.getUTCSeconds();
        const endSeconds = (end.getUTCHours() + 9) * 3600 + end.getUTCMinutes() * 60 + end.getUTCSeconds();

        const startPercent = (startSeconds / (24 * 60 * 60)) * 100;
        const duration = endSeconds - startSeconds;
        const widthPercent = (duration / (24 * 60 * 60)) * 100;

        // 모든 구간을 파란색으로 통일 (첫 번째 카메라의 모든 영상)
        const backgroundColor = '#3B82F6';

        return {
          left: `${startPercent}%`,
          width: `${widthPercent}%`,
          backgroundColor: backgroundColor,
          zIndex: 1,
          border: '2px solid rgba(255, 255, 255, 0.3)',
          borderRadius: '4px'
        };
      } catch (error) {
        console.error('Error calculating segment style:', error);
        return {
          left: '0%',
          width: '0%',
          backgroundColor: 'gray',
          zIndex: 1
        };
      }
    },

    startDrag(e) {
      console.log('startDrag :',e);
      this.dragging = true;
      document.addEventListener('mousemove', this.onDrag);
      document.addEventListener('mouseup', this.stopDrag);
    },

    onDrag(e) {
      // console.log('onDrag :',e);
      if (!this.dragging) return;
      const slider = this.$el.querySelector('.timeline-slider');
      if (!slider) return;
      const rect = slider.getBoundingClientRect();
      let x = e.clientX - rect.left;
      x = Math.max(0, Math.min(x, rect.width));
      this.playhead = x / rect.width;
      this.syncVideosToPlayhead();
    },

    stopDrag() {
      // console.log('stopDrag :');
      this.dragging = false;
      document.removeEventListener('mousemove', this.onDrag);
      document.removeEventListener('mouseup', this.stopDrag);
    },

    syncVideosToPlayhead() {  
      const seconds = this.playhead * 86400; // 사용하지 않으므로 제거
      // 실제 영상 컨트롤러와 연동 필요
      // 예: this.$refs.videoPlayer1.currentTime = seconds;
      console.log('syncVideosToPlayhead :',seconds);
    },

    onExportRecording() {
      // 선택된 영상이 있는지 확인
      if (!this.selectedVideo1 && !this.selectedVideo2) {
        this.$toast.warning('다운로드할 영상을 선택해주세요.');
        return;
      }

      // 선택된 영상 다운로드
      const downloadVideo = async (videoUrl, filename) => {
        try {
          const response = await fetch(videoUrl);
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        } catch (error) {
          console.error('Error downloading video:', error);
          this.$toast.error('영상 다운로드 중 오류가 발생했습니다.');
        }
      };

      // 선택된 영상들 다운로드
      if (this.selectedVideo1) {
        const video1 = this.recordingHistory.find(r => r.selected && this.selectedVideo1.includes(r.id));
        if (video1) {
          // HLS 스트림의 경우 MP4 다운로드 URL로 변경
          const downloadUrl = this.selectedVideo1.replace('/hls/', '/stream/');
          downloadVideo(downloadUrl, `${video1.cameraName}_${video1.startTime}.mp4`);
        }
      }
      if (this.selectedVideo2) {
        const video2 = this.recordingHistory.find(r => r.selected && this.selectedVideo2.includes(r.id));
        if (video2) {
          // HLS 스트림의 경우 MP4 다운로드 URL로 변경
          const downloadUrl = this.selectedVideo2.replace('/hls/', '/stream/');
          downloadVideo(downloadUrl, `${video2.cameraName}_${video2.startTime}.mp4`);
        }
      }
    },

    onSaveSnapshot() {
      // 현재 플레이어에 표시되고 있는 영상이 있는지 확인
      if (!this.selectedVideo1 && !this.selectedVideo2) {
        this.$toast.warning('스냅샷을 저장할 영상을 선택해주세요.');
        return;
      }

      // 스냅샷 저장 함수
      const saveSnapshot = (videoElement, filename) => {
        try {
          // 캔버스 생성
          const canvas = document.createElement('canvas');
          canvas.width = videoElement.videoWidth;
          canvas.height = videoElement.videoHeight;
          
          // 현재 프레임을 캔버스에 그리기
          const ctx = canvas.getContext('2d');
          ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
          
          // 캔버스를 이미지로 변환
          canvas.toBlob((blob) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
          }, 'image/jpeg', 0.95);
        } catch (error) {
          console.error('Error saving snapshot:', error);
          this.$toast.error('스냅샷 저장 중 오류가 발생했습니다.');
        }
      };

      let snapshotCount = 0;

      // 첫 번째 영상 스냅샷 저장
      if (this.selectedVideo1 && this.$refs.videoPlayer1) {
        const video1 = this.recordingHistory.find(r => this.selectedVideo1.includes(r.id));
        if (video1) {
          const videoElement = this.$refs.videoPlayer1;
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
          saveSnapshot(videoElement, `${video1.cameraName}_${timestamp}_snapshot1.jpg`);
          snapshotCount++;
        }
      }

      // 두 번째 영상 스냅샷 저장
      if (this.selectedVideo2 && this.$refs.videoPlayer2) {
        const video2 = this.recordingHistory.find(r => this.selectedVideo2.includes(r.id));
        if (video2) {
          const videoElement = this.$refs.videoPlayer2;
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
          saveSnapshot(videoElement, `${video2.cameraName}_${timestamp}_snapshot2.jpg`);
          snapshotCount++;
        }
      }

      if (snapshotCount > 0) {
        this.$toast.success(`${snapshotCount}개의 스냅샷이 저장되었습니다.`);
      }
    },

    // 개별 비디오 다운로드 메서드
    async downloadVideo(videoItem) {
      try {
        // 다운로드 중인 비디오 ID 추가
        this.downloadingVideos.push(videoItem.id);
        
        // 다운로드 URL 생성
        const downloadUrl = `${API_BASE_URL}/recordings/stream/${videoItem.id}`;
        
        // 파일명 생성 (카메라명_시작시간.mp4)
        const startTime = new Date(videoItem.startTime);
        const timeString = startTime.toISOString().replace(/[:.]/g, '-').substring(0, 19);
        const filename = `${videoItem.cameraName}_${timeString}.mp4`;
        
        // fetch를 사용하여 파일 다운로드
        const response = await fetch(downloadUrl);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Blob으로 변환
        const blob = await response.blob();
        
        // 다운로드 링크 생성
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // 정리
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        this.$toast.success(`${filename} 다운로드가 완료되었습니다.`);
        
      } catch (error) {
        console.error('Error downloading video:', error);
        this.$toast.error('비디오 다운로드 중 오류가 발생했습니다.');
      } finally {
        // 다운로드 중인 비디오 ID 제거
        const index = this.downloadingVideos.indexOf(videoItem.id);
        if (index > -1) {
          this.downloadingVideos.splice(index, 1);
        }
      }
    },

    startVerticalBarDrag(e) {
      console.log('startVerticalBarDrag :',e);
      this.draggingVerticalBar = true;
      // 타임라인 업데이트 일시 중지
      this.stopTimelineUpdate();
      document.addEventListener('mousemove', this.onVerticalBarDrag);
      document.addEventListener('mouseup', this.stopVerticalBarDrag);
    },

    onVerticalBarDrag(e) {
      if (!this.draggingVerticalBar) return;
      const timeline = this.$el.querySelector('.timeline-slider');
      const rect = timeline.getBoundingClientRect();
      let percent = ((e.clientX - rect.left) / rect.width) * 100;
      percent = Math.max(0, Math.min(100, percent));

      // 드래그한 위치가 비디오 범위 내에 있는지 확인
      if (this.isPositionWithinVideoRange(percent)) {
        this.verticalBarPercent = percent;
        // 각 비디오의 시간 업데이트
        this.updateVideosTime(percent);
      } else {
        // 범위 밖에 있으면 비디오 플레이어에서 영상 제거
        this.verticalBarPercent = percent;
        
        // 현재 선택된 비디오들이 있는지 확인하고 범위 밖에 있으면 제거
        if (this.selectedVideos.length > 0) {
          this.selectedVideo1 = null;
          this.selectedVideo2 = null;
          this.selectedVideos = [];
          
          if (this.$refs.videoPlayer1) {
            this.$refs.videoPlayer1.src = '';
            this.$refs.videoPlayer1.load();
          }
          if (this.$refs.videoPlayer2) {
            this.$refs.videoPlayer2.src = '';
            this.$refs.videoPlayer2.load();
          }
        }
      }
    },

    stopVerticalBarDrag() {
      this.draggingVerticalBar = false;
      document.removeEventListener('mousemove', this.onVerticalBarDrag);
      document.removeEventListener('mouseup', this.stopVerticalBarDrag);
      // 드래그 종료 후 타임라인 업데이트 재시작
      setTimeout(() => {
        if (!this.isPaused) {
          this.startTimelineUpdate();
        }
      }, 100);
    },

    handleKeyDown(event) {
      // 스페이스바 처리 - 두 비디오 모두 재생/일시정지
      if (event.key === ' ') {
        event.preventDefault(); // 페이지 스크롤 방지
        this.togglePauseAllVideos();
        return;
      }

      // 왼쪽/오른쪽 화살표 키만 처리 - 두 비디오 모두 시간 이동
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;

      // 타임라인 업데이트 일시 중지
      this.stopTimelineUpdate();

      // 1초를 퍼센트로 변환 (24시간 = 86400초)
      const oneSecondPercent = (1 / 86400) * 100;

      // 현재 위치에서 1초만큼 이동
      let newPercent;
      if (event.key === 'ArrowLeft') {
        newPercent = Math.max(0, this.verticalBarPercent - oneSecondPercent);
      } else {
        newPercent = Math.min(100, this.verticalBarPercent + oneSecondPercent);
      }

      // 새로운 위치가 비디오 범위 내에 있는지 확인
      if (this.isPositionWithinVideoRange(newPercent)) {
        this.verticalBarPercent = newPercent;
        // 두 비디오 모두 시간 업데이트
        this.updateVideosTime(this.verticalBarPercent);
      } else {
        // 범위 밖에 있으면 비디오 플레이어에서 영상 제거
        this.verticalBarPercent = newPercent;
        
        // 현재 선택된 비디오들이 있는지 확인하고 범위 밖에 있으면 제거
        if (this.selectedVideos.length > 0) {
          this.selectedVideo1 = null;
          this.selectedVideo2 = null;
          this.selectedVideos = [];
          
          if (this.$refs.videoPlayer1) {
            this.$refs.videoPlayer1.src = '';
            this.$refs.videoPlayer1.load();
          }
          if (this.$refs.videoPlayer2) {
            this.$refs.videoPlayer2.src = '';
            this.$refs.videoPlayer2.load();
          }
        }
      }
      
      // 1초 후 타임라인 업데이트 재시작
      setTimeout(() => {
        if (!this.isPaused) {
          this.startTimelineUpdate();
        }
      }, 1000);
    },

    handleTimelineClick(event) {
      // 이미 드래그 중이면 클릭 무시
      if (this.draggingVerticalBar) return;

      // 타임라인 업데이트 일시 중지
      this.stopTimelineUpdate();

      const timeline = this.$el.querySelector('.timeline-slider');
      const rect = timeline.getBoundingClientRect();
      
      // 클릭 위치를 퍼센트로 변환
      let percent = ((event.clientX - rect.left) / rect.width) * 100;
      percent = Math.max(0, Math.min(100, percent));
      
      // 수직바 위치 업데이트 (클릭한 위치로 무조건 이동)
      this.verticalBarPercent = percent;
      
      // 클릭 시 영상이 즉시 이동하도록 플래그 설정
      this.isTimelineUpdating = false;
      
      // 비디오 시간 업데이트
      this.updateVideosTime(percent);

      // 타임라인 클릭 시 해당 시간에 속한 비디오 2개를 찾아서 표시
      this.selectVideosAtTimelinePosition(percent);

      // 1초 후 타임라인 업데이트 재시작
      setTimeout(() => {
        if (!this.isPaused) {
          this.startTimelineUpdate();
        }
      }, 1000);
    },

    // 타임라인 위치에 해당하는 시간의 비디오 2개를 선택하여 표시
    selectVideosAtTimelinePosition(percent) {
      try {
        // 24시간(86400초)을 기준으로 현재 시간 계산
        const totalSeconds = 86400;
        const currentTimeSeconds = (percent / 100) * totalSeconds;
        
        // 카메라별로 그룹화된 데이터 사용
        const cameraGroups = this.cameraGroups;
        let leftVideo = null;
        let rightVideo = null;
        
        // 각 카메라에서 해당 시간대의 영상 찾기
        for (const group of cameraGroups) {
          const videoAtTime = this.findVideoAtTimelinePosition(group.recordings, currentTimeSeconds);
          
          if (videoAtTime) {
            if (!leftVideo) {
              leftVideo = videoAtTime;
            } else if (!rightVideo) {
              rightVideo = videoAtTime;
              break; // 두 개 찾았으면 종료
            }
          }
        }
        
        // 비디오 플레이어에 설정
        this.selectedVideos = [];
        this.activeVideoIds = []; // 활성 비디오 ID 초기화
        
        if (leftVideo) {
          this.selectedVideo1 = leftVideo.streamUrl;
          this.selectedVideos.push({
            ...leftVideo,
            segments: [{ startTime: leftVideo.startTime, endTime: leftVideo.endTime }]
          });
          this.activeVideoIds.push(leftVideo.id); // 활성 비디오 ID 추가
        } else {
          // 해당 시간대에 영상이 없으면 플레이어에서 영상 제거
          this.selectedVideo1 = null;
          if (this.$refs.videoPlayer1) {
            this.$refs.videoPlayer1.src = '';
            this.$refs.videoPlayer1.load();
          }
        }
        
        if (rightVideo) {
          this.selectedVideo2 = rightVideo.streamUrl;
          this.selectedVideos.push({
            ...rightVideo,
            segments: [{ startTime: rightVideo.startTime, endTime: rightVideo.endTime }]
          });
          this.activeVideoIds.push(rightVideo.id); // 활성 비디오 ID 추가
        } else {
          // 해당 시간대에 영상이 없으면 플레이어에서 영상 제거
          this.selectedVideo2 = null;
          if (this.$refs.videoPlayer2) {
            this.$refs.videoPlayer2.src = '';
            this.$refs.videoPlayer2.load();
          }
        }
        
        // 두 비디오 모두 없으면 selectedVideos 배열도 비우기
        if (!leftVideo && !rightVideo) {
          this.selectedVideos = [];
          this.activeVideoIds = [];
        }
        
        console.log('Timeline click - Videos set for display - Left:', leftVideo, 'Right:', rightVideo);
        
      } catch (error) {
        console.error('Error selecting videos at timeline position:', error);
      }
    },





    startTimelineUpdate() {
      if (this.timelineUpdateTimer) {
        clearInterval(this.timelineUpdateTimer);
      }
      this.timelineUpdateTimer = setInterval(() => {
        this.updateTimelineFromVideos();
      }, 100);
    },

    stopTimelineUpdate() {
      clearInterval(this.timelineUpdateTimer);
    },

    updateTimelineFromVideos() {
      // 비디오의 현재 시간을 기반으로 타임라인 위치 계산
      if (this.isTimelineUpdating || this.draggingVerticalBar) return;
      
      this.isTimelineUpdating = true;
      
      try {
        // 활성 비디오 찾기 (재생 중이고 타임라인 위치가 범위 내에 있는 비디오)
        let activeVideo = null;
        let videoElement = null;
        
        const totalSeconds = 86400;
        const currentTimeSeconds = (this.verticalBarPercent / 100) * totalSeconds;
        
        // 각 비디오에 대해 재생 중이고 범위 내에 있는지 확인
        this.selectedVideos.forEach((video, index) => {
          if (!video.startTime || !video.endTime) return;
          
          const startDate = new Date(video.startTime);
          const startSeconds = (startDate.getUTCHours() + 9) * 3600 + 
                             startDate.getUTCMinutes() * 60 + 
                             startDate.getUTCSeconds();
          
          const endDate = new Date(video.endTime);
          const endSeconds = (endDate.getUTCHours() + 9) * 3600 + 
                           endDate.getUTCMinutes() * 60 + 
                           endDate.getUTCSeconds();
          
          const videoRef = this.$refs[`videoPlayer${index + 1}`];
          if (!videoRef) return;
          
          const element = Array.isArray(videoRef) ? videoRef[0] : videoRef;
          if (!element) return;
          
          // 재생 중이고 타임라인 위치가 범위 내에 있는 비디오 찾기
          if (!element.paused && currentTimeSeconds >= startSeconds && currentTimeSeconds <= endSeconds) {
            activeVideo = video;
            videoElement = element;
          }
        });
        
        if (activeVideo && videoElement) {
          // MP4 비디오의 현재 시간 가져오기
          let currentVideoTime = videoElement.currentTime;
          
          // 비디오의 총 길이를 확인하여 정확한 시간 계산
          if (videoElement.duration && currentVideoTime > videoElement.duration) {
            currentVideoTime = videoElement.duration;
          }
          
          const startDate = new Date(activeVideo.startTime);
          const startSeconds = (startDate.getUTCHours() + 9) * 3600 + 
                             startDate.getUTCMinutes() * 60 + 
                             startDate.getUTCSeconds();
          
          const timelinePosition = startSeconds + currentVideoTime;
          const percent = (timelinePosition / totalSeconds) * 100;
          
          // 타임라인 위치 업데이트 (드래그 중이 아닐 때만)
          if (!this.draggingVerticalBar) {
            this.verticalBarPercent = Math.max(0, Math.min(100, percent));
          }
        }
      } catch (error) {
        console.error('Error updating timeline from videos:', error);
      } finally {
        this.isTimelineUpdating = false;
      }
    },

    updateVideosTime(barPercent) {
      // 타임라인 업데이트 중이거나 드래그 중이 아닐 때는 실행하지 않음
      if (this.isTimelineUpdating && !this.draggingVerticalBar) return;
      
      // 24시간(86400초)을 기준으로 현재 시간 계산
      const totalSeconds = 86400; // 24시간을 초로 변환
      let currentTimeSeconds = (barPercent / 100) * totalSeconds;

      // 각 비디오에 대해 개별적으로 시간 설정
      this.selectedVideos.forEach((video, index) => {
        if (!video.startTime || !video.endTime) return;

        // 시작 시간을 초 단위로 변환 (9시간 추가)
        const startDate = new Date(video.startTime);
        const startSeconds = (startDate.getUTCHours() + 9) * 3600 + 
                           startDate.getUTCMinutes() * 60 + 
                           startDate.getUTCSeconds();

        // 종료 시간을 초 단위로 변환 (9시간 추가)
        const endDate = new Date(video.endTime);
        const endSeconds = (endDate.getUTCHours() + 9) * 3600 + 
                         endDate.getUTCMinutes() * 60 + 
                         endDate.getUTCSeconds();

        // 비디오 요소 찾기
        const videoRef = this.$refs[`videoPlayer${index + 1}`];
        if (!videoRef) return;

        const videoElement = Array.isArray(videoRef) ? videoRef[0] : videoRef;
        if (!videoElement) return;

        // 현재 타임라인 위치가 이 비디오 범위 내에 있는지 확인
        if (currentTimeSeconds >= startSeconds && currentTimeSeconds <= endSeconds) {
          // 범위 내에 있으면 해당 위치에서 재생
          const videoTime = currentTimeSeconds - startSeconds;
          const videoDuration = endSeconds - startSeconds;
          
          // 비디오 시간이 범위를 벗어나면 조정
          let adjustedVideoTime = Math.max(0, Math.min(videoDuration, videoTime));
          
          // 비디오 시간 설정 (드래그 중이거나 재생 중이거나 클릭 시)
          if (this.draggingVerticalBar || !this.isPaused || this.isTimelineUpdating === false) {
            // MP4 비디오 요소의 시간 설정
            if (videoElement.duration && adjustedVideoTime <= videoElement.duration) {
              videoElement.currentTime = adjustedVideoTime;
            } else if (videoElement.duration) {
              videoElement.currentTime = Math.min(adjustedVideoTime, videoElement.duration);
            } else {
              videoElement.currentTime = adjustedVideoTime;
            }
          }
        } else {
          // 범위 밖에 있으면 비디오 일시정지하고 시작 위치로 설정
          if (videoElement && !videoElement.paused) {
            videoElement.pause();
          }
          if (this.draggingVerticalBar || !this.isPaused || this.isTimelineUpdating === false) {
            videoElement.currentTime = 0;
          }
          
          // 범위 밖에 있을 때는 해당 비디오를 selectedVideos에서 제거
          const videoIndex = this.selectedVideos.findIndex(v => v.id === video.id);
          if (videoIndex > -1) {
            this.selectedVideos.splice(videoIndex, 1);
          }
        }
      });
    },

    timeToSeconds(timeStr) {
      if (!timeStr) return 0;
      const date = new Date(timeStr);
      return date.getUTCHours() * 3600 + date.getUTCMinutes() * 60 + date.getUTCSeconds();
    },

    secondsToTime(seconds) {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const secs = seconds % 60;
      return `${hours.toString().padStart(2, '0')}:${minutes
        .toString()
        .padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    },

    // 지속 시간을 포맷팅하는 메서드
    formatDuration(seconds) {
      if (!seconds || seconds <= 0) return '0초';
      
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const secs = seconds % 60;
      
      let result = '';
      if (hours > 0) result += `${hours}시간 `;
      if (minutes > 0) result += `${minutes}분 `;
      if (secs > 0) result += `${secs}초`;
      
      return result.trim() || '0초';
    },

    // 첫 번째 카메라의 모든 영상 구간을 반환하는 메서드
    getFirstVideoSegments() {
      if (!this.recordingHistory || this.recordingHistory.length === 0) {
        return [];
      }
      
      // 카메라별로 그룹화
      const cameraGroups = this.cameraGroups;
      if (cameraGroups.length === 0) {
        return [];
      }
      
      // 첫 번째 카메라의 모든 녹화 기록을 구간으로 변환
      const firstCameraRecordings = cameraGroups[0].recordings;
      const segments = firstCameraRecordings.map(recording => ({
        startTime: recording.startTime,
        endTime: recording.endTime,
        id: recording.id,
        cameraName: recording.cameraName
      }));
      
      return segments;
    },

    // 테이블 행의 클래스를 결정하는 메서드
    getRowClass(item) {
      // 현재 활성화된 비디오 ID들 확인
      const isActive = this.activeVideoIds.includes(item.id);
      
      // selectedVideos에서도 확인
      const isInSelectedVideos = this.selectedVideos.some(video => video.id === item.id);
      
      // selectedVideo1 또는 selectedVideo2의 URL에서 ID 추출하여 확인
      const video1Id = this.selectedVideo1 ? this.extractIdFromUrl(this.selectedVideo1) : null;
      const video2Id = this.selectedVideo2 ? this.extractIdFromUrl(this.selectedVideo2) : null;
      const isInPlayerUrls = (video1Id && video1Id === item.id) || (video2Id && video2Id === item.id);
      
      if (isActive || isInSelectedVideos || isInPlayerUrls) {
        return 'active-video-row';
      }
      
      return '';
    },

    // URL에서 ID를 추출하는 헬퍼 메서드
    extractIdFromUrl(url) {
      if (!url) return null;
      const match = url.match(/\/stream\/(\d+)/);
      return match ? parseInt(match[1]) : null;
    },

    // 클릭된 영상의 시작 시간으로 타임라인바를 이동시키는 메서드
    moveTimelineToVideoStart(videoItem) {
      try {
        if (!videoItem || !videoItem.startTime) {
          console.warn('No start time available for video:', videoItem);
          return;
        }

        // 영상의 시작 시간을 Date 객체로 변환
        const startDate = new Date(videoItem.startTime);
        
        // UTC 시간을 한국 시간으로 변환 (9시간 추가)
        const startSeconds = (startDate.getUTCHours() + 9) * 3600 + 
                           startDate.getUTCMinutes() * 60 + 
                           startDate.getUTCSeconds();
        
        // 24시간(86400초)을 기준으로 퍼센트 계산
        const totalSeconds = 86400; // 24시간
        const percent = (startSeconds / totalSeconds) * 100;
        
        // 타임라인바 위치 업데이트 (애니메이션 효과)
        this.animateTimelineToPosition(Math.max(0, Math.min(100, percent)));
        
        // 비디오 시간도 업데이트
        this.updateVideosTime(this.verticalBarPercent);
        
        console.log('Timeline moved to video start:', {
          videoId: videoItem.id,
          startTime: videoItem.startTime,
          startSeconds: startSeconds,
          percent: percent,
          verticalBarPercent: this.verticalBarPercent
        });
        
      } catch (error) {
        console.error('Error moving timeline to video start:', error);
      }
    },

    // 타임라인바를 부드럽게 애니메이션으로 이동시키는 메서드
    animateTimelineToPosition(targetPercent) {
      const startPercent = this.verticalBarPercent;
      const duration = 500; // 0.5초 애니메이션
      const startTime = Date.now();
      
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // easeOutCubic 이징 함수
        const easeOutCubic = 1 - Math.pow(1 - progress, 3);
        
        // 현재 위치 계산
        this.verticalBarPercent = startPercent + (targetPercent - startPercent) * easeOutCubic;
        
        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          // 애니메이션 완료 후 정확한 위치로 설정
          this.verticalBarPercent = targetPercent;
        }
      };
      
      requestAnimationFrame(animate);
    },

    // 테이블 행 스타일만 업데이트하는 메서드 (페이지 상태 유지)
    updateTableRowStyles() {
      try {
        // Vue의 반응성 시스템을 사용하여 부드럽게 업데이트
        this.$nextTick(() => {
          // 현재 페이지의 아이템들만 확인
          const currentPageItems = this.formattedRecordingHistory;
          currentPageItems.forEach(item => {
            const isActive = this.activeVideoIds.includes(item.id);
            // DOM에서 해당 행을 찾아서 클래스 업데이트
            const rowElement = document.querySelector(`[data-id="${item.id}"]`);
            if (rowElement) {
              if (isActive) {
                rowElement.classList.add('active-video-row');
              } else {
                rowElement.classList.remove('active-video-row');
              }
            }
          });
        });
      } catch (error) {
        console.error('Error updating table row styles:', error);
      }
    },

    // 타임라인 구간을 클릭했을 때 해당 비디오를 선택하는 메서드
    selectVideoBySegment(segment) {
      try {
        // 해당 구간의 비디오를 찾기
        const video = this.recordingHistory.find(record => record.id === segment.id);
        if (!video) {
          console.warn('Video not found for segment:', segment);
          return;
        }

        // 첫 번째 플레이어에 해당 비디오 설정
        this.selectedVideo1 = video.streamUrl;
        this.selectedVideos = [{
          ...video,
          segments: [{ startTime: video.startTime, endTime: video.endTime }]
        }];
        this.activeVideoIds = [video.id];

        // 두 번째 플레이어는 비우기
        this.selectedVideo2 = null;
        if (this.$refs.videoPlayer2) {
          this.$refs.videoPlayer2.src = '';
          this.$refs.videoPlayer2.load();
        }

        // 비디오 플레이어 설정
        this.$nextTick(() => {
          this.setupVideoPlayer1();
        });

        console.log('Video selected by segment:', video);
        console.log('Active video IDs updated:', this.activeVideoIds);

        // 구간의 시작 시간으로 타임라인바 이동
        this.moveTimelineToVideoStart(video);

      } catch (error) {
        console.error('Error selecting video by segment:', error);
      }
    },

    syncVideosToTimelinePosition() {
      // 수직바 위치가 비디오 범위 내에 있는지 확인
      const totalSeconds = 86400; // 24시간
      const currentTimeSeconds = (this.verticalBarPercent / 100) * totalSeconds;
      
      let isWithinVideoRange = false;
      
      // 각 비디오에 대해 범위 확인
      this.selectedVideos.forEach((video) => {
        if (!video.startTime || !video.endTime) return;
        
        const startDate = new Date(video.startTime);
        const startSeconds = (startDate.getUTCHours() + 9) * 3600 + 
                           startDate.getUTCMinutes() * 60 + 
                           startDate.getUTCSeconds();
        
        const endDate = new Date(video.endTime);
        const endSeconds = (endDate.getUTCHours() + 9) * 3600 + 
                         endDate.getUTCMinutes() * 60 + 
                         endDate.getUTCSeconds();

        // 현재 타임라인 위치가 이 비디오 범위 내에 있는지 확인
        if (currentTimeSeconds >= startSeconds && currentTimeSeconds <= endSeconds) {
          isWithinVideoRange = true;
      }
      });

      // 범위 내에 있을 때만 비디오 시간 설정
      if (isWithinVideoRange) {
        this.updateVideosTime(this.verticalBarPercent);
        return true;
      } else {
        // 범위 밖에 있으면 비디오 플레이어에서 영상 제거
        if (this.selectedVideos.length > 0) {
          this.selectedVideo1 = null;
          this.selectedVideo2 = null;
          this.selectedVideos = [];
          
          if (this.$refs.videoPlayer1) {
            this.$refs.videoPlayer1.src = '';
            this.$refs.videoPlayer1.load();
          }
          if (this.$refs.videoPlayer2) {
            this.$refs.videoPlayer2.src = '';
            this.$refs.videoPlayer2.load();
          }
        }
        
        return false;
      }
    },

    resetTimelineToEarliestVideo() {
      // 가장 빠른 비디오의 시작 위치 찾기
      let earliestVideoStart = Infinity;
      
      this.selectedVideos.forEach((video) => {
        if (!video.startTime) return;

        const startDate = new Date(video.startTime);
        const startSeconds = (startDate.getUTCHours() + 9) * 3600 + 
                           startDate.getUTCMinutes() * 60 + 
                           startDate.getUTCSeconds();
        
        if (startSeconds < earliestVideoStart) {
          earliestVideoStart = startSeconds;
        }
      });
      
      // 타임라인을 가장 빠른 비디오의 시작 위치로 설정
      if (earliestVideoStart !== Infinity) {
        const totalSeconds = 86400; // 24시간
        this.verticalBarPercent = (earliestVideoStart / totalSeconds) * 100;
        this.updateVideosTime(this.verticalBarPercent);
      }
    },

    isPositionWithinVideoRange(percent) {
      // 수직바 위치가 비디오 범위 내에 있는지 확인
      const totalSeconds = 86400; // 24시간을 초로 변환
      const currentTimeSeconds = (percent / 100) * totalSeconds;
      
      let isWithinVideoRange = false;
      
      // 각 비디오에 대해 범위 확인
      this.selectedVideos.forEach((video) => {
        if (!video.startTime || !video.endTime) return;
        
        const startDate = new Date(video.startTime);
        const startSeconds = (startDate.getUTCHours() + 9) * 3600 + 
                           startDate.getUTCMinutes() * 60 + 
                           startDate.getUTCSeconds();
        
        const endDate = new Date(video.endTime);
        const endSeconds = (endDate.getUTCHours() + 9) * 3600 + 
                         endDate.getUTCMinutes() * 60 + 
                         endDate.getUTCSeconds();
        
        // 현재 타임라인 위치가 이 비디오 범위 내에 있는지 확인
        if (currentTimeSeconds >= startSeconds && currentTimeSeconds <= endSeconds) {
          isWithinVideoRange = true;
        }
      });
      
      return isWithinVideoRange;
    },

    // 테이블 행 클릭 시 카메라별로 다른 비디오 플레이어에 표시
    handleTableRowClick(item) {
      try {
        console.log('Table row clicked:', item);
        
        // 클릭된 항목의 카메라 이름 확인
        const clickedCameraName = item.cameraName;
        const clickedTime = new Date(item.startTime);
        
        // 카메라별로 그룹화된 데이터에서 해당 시간대의 영상 찾기
        const cameraGroups = this.cameraGroups;
        let leftVideo = null;
        let rightVideo = null;
        
        // 클릭된 카메라가 첫 번째 카메라인 경우
        if (cameraGroups.length > 0 && cameraGroups[0].cameraName === clickedCameraName) {
          // 클릭된 영상을 왼쪽 플레이어에 표시
          leftVideo = item;
          
          // 두 번째 카메라에서 같은 시간대의 영상 찾기
          if (cameraGroups.length > 1) {
            rightVideo = this.findVideoAtSameTime(cameraGroups[1].recordings, clickedTime);
          }
        }
        // 클릭된 카메라가 두 번째 카메라인 경우
        else if (cameraGroups.length > 1 && cameraGroups[1].cameraName === clickedCameraName) {
          // 클릭된 영상을 오른쪽 플레이어에 표시
          rightVideo = item;
          
          // 첫 번째 카메라에서 같은 시간대의 영상 찾기
          if (cameraGroups.length > 0) {
            leftVideo = this.findVideoAtSameTime(cameraGroups[0].recordings, clickedTime);
          }
        }
        // 기타 카메라인 경우
        else {
          // 클릭된 영상을 왼쪽 플레이어에 표시
          leftVideo = item;
          
          // 다른 카메라에서 같은 시간대의 영상 찾기
          for (const group of cameraGroups) {
            if (group.cameraName !== clickedCameraName) {
              const foundVideo = this.findVideoAtSameTime(group.recordings, clickedTime);
              if (foundVideo) {
                rightVideo = foundVideo;
                break;
              }
            }
          }
        }
        
        // 비디오 플레이어에 설정
        this.selectedVideos = [];
        this.activeVideoIds = []; // 활성 비디오 ID 초기화
        
        if (leftVideo) {
          this.selectedVideo1 = leftVideo.streamUrl;
          this.selectedVideos.push({
            ...leftVideo,
            segments: [{ startTime: leftVideo.startTime, endTime: leftVideo.endTime }]
          });
          this.activeVideoIds.push(leftVideo.id); // 활성 비디오 ID 추가
        } else {
          // 해당 시간대에 영상이 없으면 플레이어에서 영상 제거
          this.selectedVideo1 = null;
          if (this.$refs.videoPlayer1) {
            this.$refs.videoPlayer1.src = '';
            this.$refs.videoPlayer1.load();
          }
        }
        
        if (rightVideo) {
          this.selectedVideo2 = rightVideo.streamUrl;
          this.selectedVideos.push({
            ...rightVideo,
            segments: [{ startTime: rightVideo.startTime, endTime: rightVideo.endTime }]
          });
          this.activeVideoIds.push(rightVideo.id); // 활성 비디오 ID 추가
        } else {
          // 해당 시간대에 영상이 없으면 플레이어에서 영상 제거
          this.selectedVideo2 = null;
          if (this.$refs.videoPlayer2) {
            this.$refs.videoPlayer2.src = '';
            this.$refs.videoPlayer2.load();
          }
        }
        
        // 두 비디오 모두 없으면 selectedVideos 배열도 비우기
        if (!leftVideo && !rightVideo) {
          this.selectedVideos = [];
          this.activeVideoIds = [];
        }
        
        console.log('Videos set for display - Left:', leftVideo, 'Right:', rightVideo);
        
        // 클릭된 영상의 시작 시간으로 타임라인바 이동
        this.moveTimelineToVideoStart(item);
        
      } catch (error) {
        console.error('Error handling table row click:', error);
      }
    },

    // 같은 시간대의 영상을 찾는 헬퍼 메서드
    findVideoAtSameTime(recordings, targetTime) {
      const targetTimeSeconds = targetTime.getTime();
      
      // 가장 가까운 시간대의 영상 찾기
      let closestVideo = null;
      let minTimeDiff = Infinity;
      
      for (const recording of recordings) {
        const recordStart = new Date(recording.startTime);
        const recordEnd = new Date(recording.endTime);
        const recordStartSeconds = recordStart.getTime();
        const recordEndSeconds = recordEnd.getTime();
        
        // 목표 시간이 녹화 범위 내에 있는지 확인
        if (targetTimeSeconds >= recordStartSeconds && targetTimeSeconds <= recordEndSeconds) {
          return recording; // 정확히 같은 시간대
        }
        
        // 가장 가까운 시간대 계산
        const timeDiff = Math.min(
          Math.abs(targetTimeSeconds - recordStartSeconds),
          Math.abs(targetTimeSeconds - recordEndSeconds)
        );
        
        if (timeDiff < minTimeDiff) {
          minTimeDiff = timeDiff;
          closestVideo = recording;
        }
      }
      
      return closestVideo;
    },

    // 타임라인 위치에 해당하는 시간의 영상을 찾는 헬퍼 메서드
    findVideoAtTimelinePosition(recordings, currentTimeSeconds) {
      // 가장 가까운 시간대의 영상 찾기
      let closestVideo = null;
      let minTimeDiff = Infinity;
      
      for (const recording of recordings) {
        const recordStart = new Date(recording.startTime);
        const recordEnd = new Date(recording.endTime);
        
        // UTC 시간을 한국 시간으로 변환 (9시간 추가)
        const startSeconds = (recordStart.getUTCHours() + 9) * 3600 + 
                           recordStart.getUTCMinutes() * 60 + 
                           recordStart.getUTCSeconds();
        const endSeconds = (recordEnd.getUTCHours() + 9) * 3600 + 
                         recordEnd.getUTCMinutes() * 60 + 
                         recordEnd.getUTCSeconds();
        
        // 현재 시간이 녹화 범위 내에 있는지 확인
        if (currentTimeSeconds >= startSeconds && currentTimeSeconds <= endSeconds) {
          return recording; // 정확히 같은 시간대
        }
        
        // 가장 가까운 시간대 계산
        const timeDiff = Math.min(
          Math.abs(currentTimeSeconds - startSeconds),
          Math.abs(currentTimeSeconds - endSeconds)
        );
        
        if (timeDiff < minTimeDiff) {
          minTimeDiff = timeDiff;
          closestVideo = recording;
        }
      }
      
      return closestVideo;
    },

    // 🕐 타임라인 정보 업데이트 메서드 (누락된 메서드 추가)
    updateTimelineInfo() {
      try {
        if (!this.recordingHistory || this.recordingHistory.length === 0) {
          this.timelineStartTime = null;
          this.timelineEndTime = null;
          this.timelineDuration = 0;
          this.selectedVideos = [];
          return;
        }

        // 전체 영상의 시작 시간과 종료 시간 계산
        this.timelineStartTime = this.computedTimelineStartTime;
        this.timelineEndTime = this.computedTimelineEndTime;
        this.timelineDuration = this.computedTimelineDuration;

        // 카메라별로 그룹화하여 타임라인에 표시할 비디오 데이터 준비
        const cameraGroups = this.cameraGroups;
        this.selectedVideos = [];
        this.activeVideoIds = []; // 활성 비디오 ID 초기화

        // 첫 번째 카메라의 첫 번째 영상을 첫 번째 비디오로 설정
        if (cameraGroups.length > 0 && cameraGroups[0].recordings.length > 0) {
          const firstVideo = cameraGroups[0].recordings[0];
          this.selectedVideos.push({
            id: firstVideo.id,
            cameraName: firstVideo.cameraName,
            startTime: firstVideo.startTime,
            endTime: firstVideo.endTime,
            segments: [{
              startTime: firstVideo.startTime,
              endTime: firstVideo.endTime
            }]
          });
          this.activeVideoIds.push(firstVideo.id); // 활성 비디오 ID 추가
        }

        // 두 번째 카메라의 첫 번째 영상을 두 번째 비디오로 설정
        if (cameraGroups.length > 1 && cameraGroups[1].recordings.length > 0) {
          const secondVideo = cameraGroups[1].recordings[0];
          this.selectedVideos.push({
            id: secondVideo.id,
            cameraName: secondVideo.cameraName,
            startTime: secondVideo.startTime,
            endTime: secondVideo.endTime,
            segments: [{
              startTime: secondVideo.startTime,
              endTime: secondVideo.endTime
            }]
          });
          this.activeVideoIds.push(secondVideo.id); // 활성 비디오 ID 추가
        }

        console.log('Timeline info updated:', {
          startTime: this.timelineStartTime,
          endTime: this.timelineEndTime,
          duration: this.timelineDuration,
          selectedVideos: this.selectedVideos,
          activeVideoIds: this.activeVideoIds
        });

      } catch (error) {
        console.error('Error updating timeline info:', error);
        this.timelineStartTime = null;
        this.timelineEndTime = null;
        this.timelineDuration = 0;
        this.selectedVideos = [];
      }
    },
  }
};
</script>

<style lang="scss">
.recording-compare {
  padding: 20px;

  .video-container {
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
  }

  .video-player {
    flex: 1;
    background: #000;
    border-radius: 8px;
    overflow: hidden;
    transition: all 0.3s;
    cursor: pointer;

    video {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
  }

  .video-player.expanded {
    z-index: 10;
    box-shadow: 0 4px 24px rgba(0,0,0,0.25);
    border: 2px solid #fff;
  }

  .control-btn {
    height: 36px !important;
    min-width: 120px !important;
    border: 2px solid white !important;
    text-transform: none !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: normal !important;
    border-radius: 8px !important;
    color: white !important;
    background: var(--cui-bg-card) !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
  }

  .control-btn:hover {
    background: var(--cui-primary) !important;
    border-color: var(--cui-primary) !important;
    color: white !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2) !important;
  }

  .control-btn:hover .v-icon {
    color: white !important;
  }

  .control-btn:active {
    background: var(--cui-primary) !important;
    border-color: var(--cui-primary) !important;
    color: white !important;
    transform: translateY(1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
  }

  .control-btn .v-icon {
    margin-right: 4px !important;
    color: var(--cui-primary) !important;
  }

  .v-card-title {
    color: var(--cui-text-default) !important;
    font-size: 1.25rem;
    font-weight: 500;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(var(--cui-bg-nav-border-rgb));
  }

  .v-data-table ::v-deep {
    .v-data-table__wrapper {
      overflow-x: auto;
    }

    tbody tr {
      cursor: pointer;

      &:hover {
        background-color: rgba(0, 0, 0, 0.03);
      }
    }
  }

  // 녹화 테이블 스타일 (최대 4개 항목, 수직 스크롤)
  .recording-table ::v-deep {
    .v-data-table__wrapper {
      max-height: 400px; // 최대 4개 항목 높이
      overflow-y: auto;
      overflow-x: hidden;
    }

    tbody tr {
      cursor: pointer;
      transition: background-color 0.2s ease;

      &:hover {
        background-color: rgba(79, 140, 255, 0.1) !important;
        border-left: 3px solid var(--cui-primary);
      }

      &.v-data-table__selected {
        background-color: rgba(79, 140, 255, 0.2) !important;
        border-left: 3px solid var(--cui-primary);
      }

      // 현재 활성화된 비디오 행 스타일
      &.active-video-row {
        background: linear-gradient(90deg, rgba(34, 197, 94, 0.3) 0%, rgba(34, 197, 94, 0.1) 100%) !important;
        border: 3px solid #22c55e !important;
        border-radius: 8px !important;
        box-shadow: 0 6px 20px rgba(34, 197, 94, 0.4) !important;
        transform: scale(1.01) !important;
        transition: all 0.3s ease !important;
        position: relative !important;
        
        // 행 전체에 테두리 효과
        &::before {
          content: '';
          position: absolute;
          top: -2px;
          left: -2px;
          right: -2px;
          bottom: -2px;
          background: linear-gradient(45deg, #22c55e, #16a34a, #22c55e);
          border-radius: 10px;
          z-index: -1;
          animation: borderGlow 2s ease-in-out infinite alternate;
        }
        
        &:hover {
          background: linear-gradient(90deg, rgba(34, 197, 94, 0.4) 0%, rgba(34, 197, 94, 0.2) 100%) !important;
          border-color: #16a34a !important;
          transform: scale(1.02) !important;
          box-shadow: 0 8px 25px rgba(34, 197, 94, 0.5) !important;
        }
        
        // 모든 자식 요소에도 스타일 적용
        td {
          background: transparent !important;
          color: #fff !important;
          font-weight: 700 !important;
          text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5) !important;
          border: none !important;
        }
      }
    }

    // 테두리 글로우 애니메이션
    @keyframes borderGlow {
      0% {
        opacity: 0.7;
      }
      100% {
        opacity: 1;
      }
    }

    // 스크롤바 스타일링
    .v-data-table__wrapper::-webkit-scrollbar {
      width: 8px;
    }

    .v-data-table__wrapper::-webkit-scrollbar-track {
      background: #f1f1f1;
      border-radius: 4px;
    }

    .v-data-table__wrapper::-webkit-scrollbar-thumb {
      background: #c1c1c1;
      border-radius: 4px;
    }

    .v-data-table__wrapper::-webkit-scrollbar-thumb:hover {
      background: #a8a8a8;
    }
  }

  .video-player-card {
    background-color: var(--cui-bg-gray-800) !important;
    border: 1px solid rgba(var(--cui-bg-nav-border-rgb));
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;

    .v-card-title {
      color: var(--cui-text-default) !important;
      font-size: 1.25rem;
      font-weight: 500;
      padding: 16px 24px;
      border-bottom: 1px solid rgba(var(--cui-bg-nav-border-rgb));
      display: flex;
      align-items: center;

      .v-btn--icon {
        color: var(--cui-text-default) !important;
      }
    }

    .video-container {
      background-color: var(--cui-bg-gray-800);
      border-radius: 4px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      align-items: center;

      .video-wrapper {
        position: relative;
        width: 100%;
        max-width: 900px;
        margin: 0 auto;
        background-color: #000;
        border-radius: 4px;
        overflow: hidden;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);

        .video-player {
          width: 100%;
          max-height: 600px;
          background-color: #000;
          display: block;
          margin: 0 auto;
        }
      }

      .video-info {
        width: 100%;
        max-width: 900px;
        margin: 24px auto 0;
        background-color: var(--cui-bg-gray-700);
        border-radius: 4px;
        padding: 16px;

        .v-list-item {
          padding: 8px 16px;

          .v-list-item-icon {
            .v-icon {
              color: var(--cui-text-default) !important;
            }
          }

          .v-list-item-content {
            .v-list-item-title {
              color: var(--cui-text-default) !important;
              font-weight: 500;
              opacity: 0.9;
            }

            .v-list-item-subtitle {
              color: var(--cui-text-default) !important;
              opacity: 0.7;
            }
          }
        }
      }
    }

    .v-card-actions {
      padding: 16px 24px;
      border-top: 1px solid rgba(var(--cui-bg-nav-border-rgb));

      .v-btn {
        &.close-btn {
          background-color: var(--cui-text-default) !important;
          color: var(--cui-bg-gray-800) !important;
          padding: 0 24px;
          height: 36px;
          font-weight: 500;
        }
      }
    }

    .error-container {
      min-height: 200px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--cui-bg-gray-700);
      border-radius: 4px;
      margin: 20px;
    }
  }

  .v-dialog {
    max-width: 1200px;
    width: 95%;
    margin: 0 auto;
  }

  .v-data-table ::v-deep .actions-column {
    width: 100px;
    text-align: center;
  }

  .thumbnail-container {
    position: relative;
    width: 120px;
    height: 68px;
    background: #000;
    border-radius: 4px;
    overflow: hidden;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: opacity 0.2s ease;
    }

    .error-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.5);
    }
  }

  .delete-btn {
    height: 36px !important;
    min-width: 90px !important;
    border: 2px solid var(--cui-danger) !important;
    text-transform: none !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: normal !important;
    border-radius: 8px !important;
    color: red !important;
    background: var(--cui-bg-card) !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 4px rgba(239, 68, 68, 0.1) !important;
  }

  .delete-btn:hover {
    background: var(--cui-danger) !important;
    border-color: var(--cui-danger) !important;
    color: white !important;
    box-shadow: 0 4px 6px rgba(239, 68, 68, 0.2) !important;
  }

  .delete-btn:hover .v-icon {
    color: white !important;
  }

  .delete-btn:active {
    background: var(--cui-danger) !important;
    border-color: var(--cui-danger) !important;
    color: white !important;
    transform: translateY(1px);
    box-shadow: 0 2px 4px rgba(239, 68, 68, 0.1) !important;
  }

  .delete-btn .v-icon {
    margin-right: 4px !important;
    color: var(--cui-danger) !important;
  }
}

.common-dark-btn {
  background: #444857 !important;
  color: #fff !important;
  border: none !important;
  font-weight: bold !important;
  width: 132px !important;
  margin-bottom: 14px !important;
  margin-left:10px;
  margin-right:10px;
  font-size: 1rem !important;
  box-shadow: 0 2px 8px rgba(79,140,255,0.10) !important;
  border-radius: 8px !important;
  letter-spacing: 1px !important;
  display: flex;
  align-items: center;
  justify-content: center;
}
.common-dark-btn:last-child {
  margin-bottom: 0 !important;
}
.common-dark-btn__icon {
  color: #fff !important;
}

.button-box-dark {
  border-radius: 12px;
  background: #1e1e20;
  padding: 24px 0 16px 0;
  margin: 32px 0 16px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 24px rgba(0,0,0,0.25);
  min-width: 200px;
  max-height:200px;
}

.nle-timeline-box { min-height: 80px; }
.timeline-slider { height: 60px; }
.timeline-videos { 
  position: relative; 
  height: 40px; 
  margin: 10px 0;
}
.timeline-bar { 
  position: relative; 
  height: 24px; 
  background: #222; 
  border-radius: 4px; 
  border: 1px solid #444;
  width: 100%;
}
.timeline-segment { 
  border-radius: 4px; 
  background: #3B82F6 !important;
  border: 2px solid #60A5FA !important;
}

.vertical-bar {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 4px;
  background: red;
  cursor: ew-resize;
  z-index: 10;
  transition: left 0.1s ease-out;
  box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
}

.current-time-display {
  background: rgba(0, 0, 0, 0.9) !important;
  border: 2px solid #3b82f6 !important;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4) !important;
  font-family: 'Courier New', monospace !important;
  letter-spacing: 1px !important;
  min-width: 100px !important;
  text-align: center !important;
}
</style> 
