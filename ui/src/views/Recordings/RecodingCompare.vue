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
            // 왼쪽 박스 (컨트롤 + 카메라 목록)
            .tw-flex-1.tw-flex.tw-flex-col.tw-gap-4
              // 컨트롤 버튼 박스
              .button-box.button-box-dark.tw-p-4
                .tw-flex.tw-flex-col.tw-gap-2
                  v-btn.play-all-btn.common-dark-btn(color="gray" @click="playAllVideos")
                    v-icon(left class="common-dark-btn__icon") {{ icons.mdiPlay }}
                    span 모두 재생
                  v-btn.play-all-btn.common-dark-btn(color="gray" @click="togglePauseAllVideos")
                    v-icon(left class="common-dark-btn__icon") {{ isPaused ? icons.mdiPlay : icons.mdiPause }}
                    span {{ isPaused ? '재생' : '일시정지' }}
                  v-btn.play-all-btn.common-dark-btn(color="gray" @click="stopAllVideos")
                    v-icon(left class="common-dark-btn__icon") {{ icons.mdiStop }}
                    span 중지
              
              // 카메라 목록 테이블
              .button-box.button-box-dark.tw-p-4.tw-flex-1
                v-data-table(
                  :headers="cameraHeaders"
                  :items="cameras"
                  :loading="loading"
                  hide-default-header
                  hide-default-footer
                  :items-per-page="-1"
                  class="elevation-1"
                )
                  template(#item.selected="{ item }")
                    v-checkbox(
                      v-model="item.selected"
                    )
                  template(#item.name="{ item }")
                    span {{ item.name }}
            
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

        v-card.mt-4
          v-data-table(
            :headers="headers"
            :items="formattedRecordingHistory"
            :loading="loading"
            :items-per-page="10"
            class="elevation-1"
          )
            template(#item.selected="{ item }")
              v-checkbox(
                v-model="item.selected"
              )
            
            template(#item.formattedStartTime="{ item }")
              span {{ formatTime2(item.formattedStartTime) }}
            
            template(#item.formattedEndTime="{ item }")
              span {{ formatTime2(item.formattedEndTime) }}
            
            template(#item.filename="{ item }")
              span {{ item.filename }}
            
            template(#item.status="{ item }")
              v-chip(
                :color="getStatusColor(item.status)"
                small
                label
              ) {{ getStatusText(item.status) }}
            
            template(#no-data)
              .text-center.pa-4
                v-icon(color="grey" size="40") {{ icons.mdiVideo }}
                .mt-2 녹화 기록이 없습니다.

        // 하단 전체 너비 NLE 타임라인 박스
        .tw-mt-4
          .nle-timeline-box.tw-bg-gray-800.tw-p-4.tw-rounded-lg.tw-flex.tw-items-center.tw-relative
            // NLE 슬라이더
            .timeline-slider.tw-flex-1.tw-relative(@click="handleTimelineClick")
              .timeline-hours.tw-relative.tw-h-4
                span(
                  v-for="h in 13"
                  :key="h"
                  :style="{ position: 'absolute', left: `calc(${(h-1)/12*100}% - 10px)` }"
                  class="tw-text-xs tw-text-gray-400"
                ) {{ (h-1)*2 }}
              .timeline-videos
                .timeline-row(v-for="(video, idx) in selectedVideos || []" :key="video.id")
                  <!-- .timeline-label.tw-w-10.tw-text-xs.tw-text-white {{ video.cameraName || 'Unknown Camera' }} -->
                  .timeline-bar.tw-relative.tw-h-2.tw-bg-gray-700.tw-rounded.tw-ml-0
                    // 비디오별 구간 표시
                    .timeline-segment.tw-absolute.tw-h-full.tw-rounded(
                      v-for="segment in video.segments || []"
                      :key="segment.startTime + '-' + segment.endTime"
                      :style="segmentStyle(segment)"
                    )
              // 수직 스크롤 바
              .vertical-bar(:style="verticalBarStyle" @mousedown="startVerticalBarDrag")
            // 현재 시간 표시
            .current-time.tw-absolute.tw-top-2.tw-right-4.tw-text-white.tw-text-lg
              | {{ formattedPlayheadTime }}

</template>

<script>
import { 
  mdiVideo, 
  mdiCamera, 
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
  mdiPause
} from '@mdi/js'
import moment from 'moment';
import { getRecordingHistory} from '@/api/recordingService.api.js';
import { getCameras } from '@/api/cameras.api';
import Hls from 'hls.js';
const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:9091' 
  : 'http://20.41.121.184:9091';
export default {
  name: 'RecodingCompare',

  components: {},

  props: {},

  data: () => ({
    icons: {
      mdiVideo,
      mdiCamera,
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
      mdiPause
    },
    loading: false,
    recordingHistory: [],
    selectedVideo1: null,
    selectedVideo2: null,
    headers: [
      { text: '선택', value: 'selected', sortable: false, width: '80px' },
      { text: '카메라', value: 'cameraName', sortable: true },
      { text: '시작 시간', value: 'formattedStartTime', sortable: true },
      { text: '종료 시간', value: 'formattedEndTime', sortable: true },
      { text: '파일명', value: 'filename', sortable: true },
      { text: '상태', value: 'status', sortable: true }
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
      camera: null,
      status: null
    },
    expandedVideo: 0,
    isPaused: true,
    cameraHeaders: [
      { text: '선택', value: 'selected', sortable: false, width: '80px' },
      { text: '카메라', value: 'name', sortable: true }
    ],
    cameras: [],
    selectedDate: new Date().toISOString().substr(0, 10),
    playhead: 0, // 0~1 (0=00:00, 1=24:00)
    dragging: false,
    selectedVideos: [],
    thumbnailUrl: '',
    verticalBarPercent: 50, // 0~100, 디폴트 중앙
    draggingVerticalBar: false,
    hlsPlayer1: null,
    hlsPlayer2: null,
    timelineUpdateTimer: null, // 타임라인 업데이트 타이머
    isTimelineUpdating: false, // 타임라인 업데이트 중 플래그
  }),

  computed: {
    formattedRecordingHistory() {
      if (!this.recordingHistory || this.recordingHistory.length === 0) {
        // 녹화 데이터가 없으면 비디오 화면 초기화
        this.$nextTick(() => {
          this.$refs.videoPlayer?.forEach(player => {
            if (player) {
              player.reset();
            }
          });
        });
        return [];
      }

      // 녹화 데이터가 있으면 자동으로 체크하여 비디오 화면에 표시
      const formattedData = this.recordingHistory.map((record) => ({
        ...record,
        formattedStartTime: this.formatTime(record.startTime),
        formattedEndTime: this.formatTime(record.endTime),
        selected: true  // 자동으로 체크
      }));

      // 비디오 플레이어 업데이트
      this.$nextTick(() => {
        formattedData.forEach((record, index) => {
          const player = this.$refs.videoPlayer?.[index];
          if (player && record.selected) {
            player.loadVideo(record);
          }
        });
      });

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
    }
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
      this.createHLSPlayer1();
    },
    selectedVideo2() {
      this.createHLSPlayer2();
    }
  },

  created() {
    // this.loadRecordingHistory();
    this.loadCameras();
  },

  mounted() {
    //this.fetchRecordingHistory();
    document.addEventListener('mousemove', this.onDrag);
    document.addEventListener('mouseup', this.stopDrag);
    // 키보드 이벤트 리스너 추가
    document.addEventListener('keydown', this.handleKeyDown);
    // 중앙에 위치
    this.verticalBarPercent = 50;
    
    // HLS 지원 확인
    if (!Hls.isSupported() && !document.createElement('video').canPlayType('application/vnd.apple.mpegurl')) {
      this.$toast.warning('이 브라우저에서는 HLS 재생을 지원하지 않습니다. 최신 브라우저를 사용해주세요.');
    }
  },

  beforeDestroy() {
    if (this.$refs.videoPlayer) {
      this.$refs.videoPlayer.pause();
    }
    // Cleanup thumbnail URLs
    Object.values(this.thumbnails).forEach(url => {
      if (url && url.startsWith('blob:')) {
        URL.revokeObjectURL(url);
      }
    });
    // 메모리 정리
    this.thumbnails = {};
    this.imageData.clear();
    // ImageBitmap 객체 정리
    Object.values(this.thumbnails).forEach(imageBitmap => {
      if (imageBitmap instanceof ImageBitmap) {
        imageBitmap.close();
      }
    });
    document.removeEventListener('mousemove', this.onDrag);
    document.removeEventListener('mouseup', this.stopDrag);
    // 키보드 이벤트 리스너 제거
    document.removeEventListener('keydown', this.handleKeyDown);
    if (this.hlsPlayer1) {
      this.hlsPlayer1.destroy();
      this.hlsPlayer1 = null;
    }
    if (this.hlsPlayer2) {
      this.hlsPlayer2.destroy();
      this.hlsPlayer2 = null;
    }
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
          this.selectedVideo1 = `${API_BASE_URL}/api/recordings/hls/${item.id}`;
          // HLS 플레이어 생성
          this.$nextTick(() => {
            this.createHLSPlayer1();
          });
        } else if (!this.selectedVideo2) {
          this.selectedVideo2 = `${API_BASE_URL}/api/recordings/hls/${item.id}`;
          // HLS 플레이어 생성
          this.$nextTick(() => {
            this.createHLSPlayer2();
          });
        } else {
          item.selected = false;
          this.$toast.warning('최대 2개의 영상만 선택할 수 있습니다.');
        }
      } else {
        if (this.selectedVideo1 === `${API_BASE_URL}/api/recordings/hls/${item.id}`) {
          this.selectedVideo1 = null;
          // HLS 플레이어 정리
          if (this.hlsPlayer1) {
            this.hlsPlayer1.destroy();
            this.hlsPlayer1 = null;
          }
        } else if (this.selectedVideo2 === `${API_BASE_URL}/api/recordings/hls/${item.id}`) {
          this.selectedVideo2 = null;
          // HLS 플레이어 정리
          if (this.hlsPlayer2) {
            this.hlsPlayer2.destroy();
            this.hlsPlayer2 = null;
          }
        }
      }
    },

    playAllVideos() {
      // 재생 전에 수직바 위치를 기준으로 비디오 시간 설정
      if (!this.syncVideosToTimelinePosition()) {
        return; // 범위 밖에 있으면 재생하지 않음
      }
      
      // 각 비디오별로 개별적으로 재생 가능 여부 확인
      this.selectedVideos.forEach((video, index) => {
        if (!video.startTime || !video.endTime) return;
        
        const totalSeconds = 86400;
        const currentTimeSeconds = (this.verticalBarPercent / 100) * totalSeconds;
        
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
          const videoRef = this.$refs[`videoPlayer${index + 1}`];
          if (videoRef) {
            const videoElement = Array.isArray(videoRef) ? videoRef[0] : videoRef;
            if (videoElement) {
              // HLS 플레이어가 있으면 HLS 방식으로 재생
              const hlsPlayer = index === 0 ? this.hlsPlayer1 : this.hlsPlayer2;
              if (hlsPlayer && hlsPlayer.media) {
                hlsPlayer.media.play();
              } else {
                videoElement.play();
              }
            }
          }
        }
      });
      
      this.startTimelineUpdate();
    },

    togglePauseAllVideos() {
      if (this.isPaused) {
        // 재생 전에 수직바 위치를 기준으로 비디오 시간 설정
        if (!this.syncVideosToTimelinePosition()) {
          return; // 범위 밖에 있으면 재생하지 않음
        }
        
        // 각 비디오별로 개별적으로 재생 가능 여부 확인
        this.selectedVideos.forEach((video, index) => {
          if (!video.startTime || !video.endTime) return;
          
          const totalSeconds = 86400;
          const currentTimeSeconds = (this.verticalBarPercent / 100) * totalSeconds;
          
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
            const videoRef = this.$refs[`videoPlayer${index + 1}`];
            if (videoRef) {
              const videoElement = Array.isArray(videoRef) ? videoRef[0] : videoRef;
              if (videoElement) {
                // HLS 플레이어가 있으면 HLS 방식으로 재생
                const hlsPlayer = index === 0 ? this.hlsPlayer1 : this.hlsPlayer2;
                if (hlsPlayer && hlsPlayer.media) {
                  hlsPlayer.media.play();
                } else {
                  videoElement.play();
                }
              }
            }
          }
        });
        
        this.startTimelineUpdate();
      } else {
        // HLS 플레이어가 있으면 HLS 방식으로 일시정지
        if (this.hlsPlayer1 && this.hlsPlayer1.media) {
          this.hlsPlayer1.media.pause();
        } else if (this.$refs.videoPlayer1) {
          this.$refs.videoPlayer1.pause();
        }
        
        if (this.hlsPlayer2 && this.hlsPlayer2.media) {
          this.hlsPlayer2.media.pause();
        } else if (this.$refs.videoPlayer2) {
          this.$refs.videoPlayer2.pause();
        }
        
        this.stopTimelineUpdate();
      }
      this.isPaused = !this.isPaused;
    },

    stopAllVideos() {
      // HLS 플레이어가 있으면 HLS 방식으로 중지
      if (this.hlsPlayer1 && this.hlsPlayer1.media) {
        this.hlsPlayer1.media.pause();
        if (this.hlsPlayer1.media.seekable && this.hlsPlayer1.media.seekable.length > 0) {
          this.hlsPlayer1.media.currentTime = this.hlsPlayer1.media.seekable.start(0);
        } else {
          this.hlsPlayer1.media.currentTime = 0;
        }
      } else if (this.$refs.videoPlayer1) {
        this.$refs.videoPlayer1.pause();
        this.$refs.videoPlayer1.currentTime = 0;
      }
      
      if (this.hlsPlayer2 && this.hlsPlayer2.media) {
        this.hlsPlayer2.media.pause();
        if (this.hlsPlayer2.media.seekable && this.hlsPlayer2.media.seekable.length > 0) {
          this.hlsPlayer2.media.currentTime = this.hlsPlayer2.media.seekable.start(0);
        } else {
          this.hlsPlayer2.media.currentTime = 0;
        }
      } else if (this.$refs.videoPlayer2) {
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

    handleVideoError(event) {
      console.error('Video error:', event);
      const videoElement = event.target;
      
      // HLS 플레이어 에러 처리
      if (videoElement.src && videoElement.src.includes('/hls/')) {
        this.$toast.error('HLS 스트림을 재생할 수 없습니다. 잠시 후 다시 시도해주세요.');
        
        // HLS 플레이어 재시도 로직
        setTimeout(() => {
          if (videoElement === this.$refs.videoPlayer1 && this.selectedVideo1) {
            this.createHLSPlayer1();
          } else if (videoElement === this.$refs.videoPlayer2 && this.selectedVideo2) {
            this.createHLSPlayer2();
          }
        }, 2000);
      } else {
        this.$toast.error('비디오를 재생할 수 없습니다.');
      }
    },

    handleVideoLoaded(event) {
      // 비디오가 로드되면 첫 프레임으로 이동
      const video = event.target;
      
      // HLS 플레이어의 경우 currentTime 설정을 조심스럽게 처리
      if (video.src && video.src.includes('/hls/')) {
        // HLS 플레이어는 메타데이터 로드 후에 currentTime 설정
        if (video.readyState >= 1) {
          // HLS 플레이어의 경우 seekable 범위 확인
          if (video.seekable && video.seekable.length > 0) {
            video.currentTime = video.seekable.start(0);
          } else {
            video.currentTime = 0;
          }
        }
      } else {
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

    async loadCameras() {
      try {
        const response = await getCameras();
        if (response && response.data && response.data.result) {
          this.cameras = response.data.result.map(camera => ({
            ...camera,
            selected: true
          }));
        }
      } catch (error) {
        console.error('Error loading cameras:', error);
        this.cameras = [];
      }
    },

    handleCameraSelectionChange(item) {
      // 카메라 선택 변경 처리
      console.log('Selected cameras:', this.cameras.filter(cam => cam.selected),',item:',item);
      // 선택된 카메라가 있으면 현재 선택된 날짜에 대한 녹화 기록을 조회
      const selectedCameras = this.cameras.filter(cam => cam.selected);
      if (selectedCameras.length > 0 && this.selectedDate) {
        this.fetchRecordingHistoryForDate(this.selectedDate, selectedCameras);
      }
    },

    async handleDateChange(date) {
      // 날짜 변경 처리
      console.log('Selected date:', date);
      // 선택된 카메라가 있으면 해당 날짜에 대한 녹화 기록을 조회
      const selectedCameras = this.cameras.filter(cam => cam.selected);
      if (selectedCameras.length > 0) {
        await this.fetchRecordingHistoryForDate(date, selectedCameras);
      }
    },

    async fetchRecordingHistoryForDate(date, selectedCameras) {
      this.loading = true;
      try {
        // 선택된 카메라의 ID 목록
        this.selectedVideos = [];
        const cameraIds = selectedCameras.map(cam => cam.id);
        // 날짜 범위 설정 (선택된 날짜의 시작부터 끝까지)
        const startDate = new Date(date);
        startDate.setHours(0, 0, 0, 0);
        const endDate = new Date(date);
        endDate.setHours(23, 59, 59, 999);
        this.selectedVideo1 = null;
        this.selectedVideo2 = null;
        this.recordingHistory = [];
        this.$nextTick(() => {
          this.$refs.videoPlayer?.forEach(player => {
            if (player) {
              player.reset();
            }
          });
        });

        // 녹화 기록 조회
        const response = await getRecordingHistory({
          startDate: startDate.toISOString(),
          endDate: endDate.toISOString(),
          cameraIds: cameraIds
        });
        
        if (Array.isArray(response)) {
          // startTime 기준으로 정렬하고 최근 두 개의 녹화만 사용
          const sortedRecordings = response.sort((a, b) => {
            const timeA = new Date(a.startTime || a.start_time).getTime();
            const timeB = new Date(b.startTime || b.start_time).getTime();
            return timeB - timeA; // 내림차순 정렬 (최신순)
          });
          const recentRecordings = sortedRecordings.slice(0, 2);
          
          this.recordingHistory = recentRecordings.map(record => {
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
                      if(this.recordingHistory.length > 0) {
              this.recordingHistory.forEach(item => {
                item.selected = true;
                this.selectedVideos.push({
                  ...item,
                  segments: [{ startTime: item.startTime, endTime: item.endTime }]
                });
                this.handleSelectionChange(item);
              });
              // 비디오 선택 후 타임라인을 가장 빠른 비디오의 시작 위치로 설정
              this.$nextTick(() => {
                this.resetTimelineToEarliestVideo();
              });
            } else {
              this.selectedVideo1 = null;
              this.selectedVideo2 = null;
              // HLS 플레이어 정리
              if (this.hlsPlayer1) {
                this.hlsPlayer1.destroy();
                this.hlsPlayer1 = null;
              }
              if (this.hlsPlayer2) {
                this.hlsPlayer2.destroy();
                this.hlsPlayer2 = null;
              }
              // 비디오 요소 정리
              const videoElements = document.querySelectorAll('video');
              videoElements.forEach(video => {
                video.src = '';      // 비디오 소스 제거
                video.load();        // 비디오 리로드
                video.poster = '';   // 섬네일 이미지 제거
              });
            }
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

    // 타임라인에 표시할 segment 스타일 계산
    segmentStyle(segment) {
      // ISO 문자열을 Date 객체로 변환
      const start = new Date(segment.startTime);
      const end = new Date(segment.endTime);

      // 0시 기준 초 단위로 변환 (UTC 기준, 9시간 추가)
      const startSeconds = (start.getUTCHours() + 9) * 3600 + start.getUTCMinutes() * 60 + start.getUTCSeconds();
      const endSeconds = (end.getUTCHours() + 9) * 3600 + end.getUTCMinutes() * 60 + end.getUTCSeconds();

      const startPercent = (startSeconds / (24 * 60 * 60)) * 100;
      const duration = endSeconds - startSeconds;
      const widthPercent = (duration / (24 * 60 * 60)) * 100;

      return {
        left: `${startPercent}%`,
        width: `${widthPercent}%`,
        backgroundColor: 'yellow',
        zIndex: 1
      };
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
      // 선택된 영상이 있는지 확인
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

      // 선택된 영상들의 스냅샷 저장
      if (this.selectedVideo1 && this.$refs.videoPlayer1) {
        const video1 = this.recordingHistory.find(r => r.selected && this.selectedVideo1.includes(r.id));
        if (video1) {
          // HLS 플레이어가 있으면 HLS 미디어 요소 사용
          const videoElement = this.hlsPlayer1 && this.hlsPlayer1.media ? this.hlsPlayer1.media : this.$refs.videoPlayer1;
          saveSnapshot(videoElement, `${video1.cameraName}_${video1.startTime}_snapshot.jpg`);
        }
      }
      if (this.selectedVideo2 && this.$refs.videoPlayer2) {
        const video2 = this.recordingHistory.find(r => r.selected && this.selectedVideo2.includes(r.id));
        if (video2) {
          // HLS 플레이어가 있으면 HLS 미디어 요소 사용
          const videoElement = this.hlsPlayer2 && this.hlsPlayer2.media ? this.hlsPlayer2.media : this.$refs.videoPlayer2;
          saveSnapshot(videoElement, `${video2.cameraName}_${video2.startTime}_snapshot.jpg`);
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
      // 스페이스바 처리
      if (event.key === ' ') {
        event.preventDefault(); // 페이지 스크롤 방지
        this.togglePauseAllVideos();
        return;
      }

      // 왼쪽/오른쪽 화살표 키만 처리
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
        // 비디오 시간 업데이트
        this.updateVideosTime(this.verticalBarPercent);
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

      // 1초 후 타임라인 업데이트 재시작
      setTimeout(() => {
        if (!this.isPaused) {
          this.startTimelineUpdate();
        }
      }, 1000);
    },

    createHLSPlayer1() {
      if (this.hlsPlayer1) {
        this.hlsPlayer1.destroy();
        this.hlsPlayer1 = null;
      }
      if (this.selectedVideo1 && this.$refs.videoPlayer1) {
        this.initializeHLSPlayer(this.$refs.videoPlayer1, this.selectedVideo1, 1);
      }
    },

    createHLSPlayer2() {
      if (this.hlsPlayer2) {
        this.hlsPlayer2.destroy();
        this.hlsPlayer2 = null;
      }
      if (this.selectedVideo2 && this.$refs.videoPlayer2) {
        this.initializeHLSPlayer(this.$refs.videoPlayer2, this.selectedVideo2, 2);
      }
    },

    initializeHLSPlayer(videoElement, videoUrl, playerIndex) {
      if (Hls.isSupported()) {
        const hls = new Hls({
          debug: false,
          enableWorker: true,
          lowLatencyMode: false, // 녹화된 영상이므로 false
          backBufferLength: 30,
          maxBufferLength: 30,
          maxMaxBufferLength: 600,
          maxBufferSize: 30 * 1000 * 1000, // 30MB
          maxBufferHole: 0.5,
          highBufferWatchdogPeriod: 2,
          nudgeOffset: 0.2,
          nudgeMaxRetry: 5,
          maxFragLookUpTolerance: 0.25,
          // liveSyncDurationCount: 3,   // 삭제
          // liveMaxLatencyDurationCount: 10, // 삭제
          // liveSyncDuration: 3,        // 삭제
          // liveMaxLatencyDuration: 10, // 삭제
          // liveDurationInfinity: false, // 삭제
          progressive: false,
          startLevel: -1, // 자동 품질 선택
          abrEwmaDefaultEstimate: 500000, // 500kbps
          abrBandWidthFactor: 0.95,
          abrBandWidthUpFactor: 0.7,
          abrMaxWithRealBitrate: true,
          startFragPrefetch: true,
          testBandwidth: true
        });

        hls.loadSource(videoUrl);
        hls.attachMedia(videoElement);

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          console.log(`HLS Player ${playerIndex} manifest parsed`);
          if (playerIndex === 1) {
            this.hlsPlayer1 = hls;
          } else {
            this.hlsPlayer2 = hls;
          }
          
          // 비디오 요소에 이벤트 리스너 추가
          videoElement.addEventListener('seeking', () => {
            console.log(`HLS Player ${playerIndex} seeking`);
          });
          
          videoElement.addEventListener('seeked', () => {
            console.log(`HLS Player ${playerIndex} seeked`);
          });
          
          videoElement.addEventListener('waiting', () => {
            console.log(`HLS Player ${playerIndex} waiting for data`);
          });
          
          videoElement.addEventListener('canplay', () => {
            console.log(`HLS Player ${playerIndex} can play`);
          });
        });

        hls.on(Hls.Events.ERROR, (event, data) => {
          console.error(`HLS Player ${playerIndex} error:`, data);
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                console.log(`HLS Player ${playerIndex} network error, trying to recover...`);
                hls.startLoad();
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                console.log(`HLS Player ${playerIndex} media error, trying to recover...`);
                hls.recoverMediaError();
                break;
              default:
                console.error(`HLS Player ${playerIndex} fatal error, destroying player`);
                hls.destroy();
                this.$toast.error(`HLS 플레이어 ${playerIndex}에서 오류가 발생했습니다.`);
                break;
            }
          } else {
            // 비치명적 오류는 로그만 출력
            console.warn(`HLS Player ${playerIndex} non-fatal error:`, data);
          }
        });

        hls.on(Hls.Events.FRAG_LOADED, () => {
          // 프래그먼트 로드 완료 시 타임라인 업데이트
          if (!this.isPaused && !this.draggingVerticalBar) {
            this.updateTimelineFromVideos();
          }
        });

        hls.on(Hls.Events.MANIFEST_LOADED, () => {
          console.log(`HLS Player ${playerIndex} manifest loaded`);
        });

        hls.on(Hls.Events.LEVEL_LOADED, () => {
          console.log(`HLS Player ${playerIndex} level loaded`);
        });

        hls.on(Hls.Events.FRAG_PARSED, () => {
          // 프래그먼트 파싱 완료 시 타임라인 업데이트
          if (!this.isPaused && !this.draggingVerticalBar) {
            this.updateTimelineFromVideos();
          }
        });
      } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
        // Safari의 네이티브 HLS 지원
        videoElement.src = videoUrl;
        videoElement.addEventListener('loadedmetadata', () => {
          console.log(`Native HLS Player ${playerIndex} loaded`);
          if (playerIndex === 1) {
            this.hlsPlayer1 = { 
              destroy: () => {
                videoElement.src = '';
                videoElement.load();
              },
              media: videoElement
            };
          } else {
            this.hlsPlayer2 = { 
              destroy: () => {
                videoElement.src = '';
                videoElement.load();
              },
              media: videoElement
            };
          }
        });
        
        videoElement.addEventListener('error', (event) => {
          console.error(`Native HLS Player ${playerIndex} error:`, event);
        });
      } else {
        console.error(`HLS is not supported in this browser for player ${playerIndex}`);
        this.$toast.error('이 브라우저에서는 HLS 재생을 지원하지 않습니다.');
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
        let hlsPlayer = null;
        
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
            hlsPlayer = index === 0 ? this.hlsPlayer1 : this.hlsPlayer2;
          }
        });
        
        if (activeVideo && videoElement) {
          // HLS 플레이어의 경우 현재 시간을 가져오는 방법이 다름
          let currentVideoTime = videoElement.currentTime;
          
          // HLS 플레이어가 있고 현재 프래그먼트 정보가 있으면 사용
          if (hlsPlayer && hlsPlayer.media && hlsPlayer.media.currentTime) {
            currentVideoTime = hlsPlayer.media.currentTime;
          }
          
          // HLS 플레이어의 경우 현재 프래그먼트 정보도 확인
          if (hlsPlayer && hlsPlayer.media && hlsPlayer.media.duration) {
            // 비디오의 총 길이를 확인하여 정확한 시간 계산
            const videoDuration = hlsPlayer.media.duration;
            if (currentVideoTime > videoDuration) {
              currentVideoTime = videoDuration;
            }
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

        // HLS 플레이어 참조
        const hlsPlayer = index === 0 ? this.hlsPlayer1 : this.hlsPlayer2;

        // 현재 타임라인 위치가 이 비디오 범위 내에 있는지 확인
        if (currentTimeSeconds >= startSeconds && currentTimeSeconds <= endSeconds) {
          // 범위 내에 있으면 해당 위치에서 재생
          const videoTime = currentTimeSeconds - startSeconds;
          const videoDuration = endSeconds - startSeconds;
          
          // 비디오 시간이 범위를 벗어나면 조정
          let adjustedVideoTime = Math.max(0, Math.min(videoDuration, videoTime));
          
          // 비디오 시간 설정 (드래그 중이거나 재생 중이거나 클릭 시)
          if (this.draggingVerticalBar || !this.isPaused || this.isTimelineUpdating === false) {
            // HLS 플레이어가 있으면 HLS 방식으로 시간 설정
            if (hlsPlayer && hlsPlayer.media) {
              // HLS 플레이어의 경우 seekable 범위 확인
              if (hlsPlayer.media.seekable && hlsPlayer.media.seekable.length > 0) {
                const seekableStart = hlsPlayer.media.seekable.start(0);
                const seekableEnd = hlsPlayer.media.seekable.end(0);
                const clampedTime = Math.max(seekableStart, Math.min(seekableEnd, adjustedVideoTime));
                hlsPlayer.media.currentTime = clampedTime;
              } else {
                hlsPlayer.media.currentTime = adjustedVideoTime;
              }
            } else {
              // 일반 HTML5 비디오 요소
              videoElement.currentTime = adjustedVideoTime;
            }
          }
        } else {
          // 범위 밖에 있으면 시작 위치로 설정 (재생하지 않음)
          if (this.draggingVerticalBar || !this.isPaused || this.isTimelineUpdating === false) {
            if (hlsPlayer && hlsPlayer.media) {
              // HLS 플레이어의 경우 seekable 범위 확인
              if (hlsPlayer.media.seekable && hlsPlayer.media.seekable.length > 0) {
                hlsPlayer.media.currentTime = hlsPlayer.media.seekable.start(0);
              } else {
                hlsPlayer.media.currentTime = 0;
              }
            } else {
              videoElement.currentTime = 0;
            }
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
      } else {
        return false;
      }
      
      return true;
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
      // 타임라인 업데이트 중이거나 드래그 중이 아닐 때는 실행하지 않음
      if (this.isTimelineUpdating && !this.draggingVerticalBar) return true;
      
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

  .play-all-btn {
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

  .play-all-btn:hover {
    background: var(--cui-primary) !important;
    border-color: var(--cui-primary) !important;
    color: white !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2) !important;
  }

  .play-all-btn:hover .v-icon {
    color: white !important;
  }

  .play-all-btn:active {
    background: var(--cui-primary) !important;
    border-color: var(--cui-primary) !important;
    color: white !important;
    transform: translateY(1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
  }

  .play-all-btn .v-icon {
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

.nle-timeline-box { min-height: 100px; }
.timeline-slider { height: 80px; }
.timeline-row { display: flex; align-items: center; height: 18px; }
.timeline-label { width: 40px; color: #bbb; font-size: 12px; }
.timeline-bar { flex: 1; position: relative; height: 8px; background: #222; border-radius: 4px; margin-left: 8px; }
.timeline-segment { border-radius: 4px; }
.playhead-bar { }

.vertical-bar {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 4px;
  background: red;
  cursor: ew-resize;
  z-index: 10;
}
</style> 
