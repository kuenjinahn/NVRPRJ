<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.recording-compare
  v-container(fluid)
    v-row
      v-col(cols="12")
        .tw-flex.tw-justify-between.tw-items-center
          .video-container.tw-flex.tw-gap-4(style="position:relative;")
            .video-player.tw-flex-1(:class="{ expanded: expandedVideo === 1 }" @click="expandVideo(1)")
              video(
                ref="videoPlayer1"
                controls
                :src="selectedVideo1"
                @error="handleVideoError"
                crossorigin="anonymous"
                preload="metadata"
                controlsList="nodownload"
                :style="expandedVideo === 1 ? 'width: 1280px; height: 720px;' : 'width: 640px; height: 480px;'"
              )
            .tw-flex.tw-gap-4
              .video-player.tw-flex-1(:class="{ expanded: expandedVideo === 2 }" @click="expandVideo(2)")
                video(
                  ref="videoPlayer2"
                  controls
                  :src="selectedVideo2"
                  @error="handleVideoError"
                  crossorigin="anonymous"
                  preload="metadata"
                  controlsList="nodownload"
                  :style="expandedVideo === 2 ? 'width: 1280px; height: 720px;' : 'width: 640px; height: 480px;'"
                )
              .button-box.button-box-dark
                v-btn.play-all-btn.common-dark-btn(color="gray" @click="playAllVideos")
                  v-icon(left class="common-dark-btn__icon") {{ icons.mdiPlay }}
                  span 모두 재생
                v-btn.play-all-btn.common-dark-btn(color="gray" @click="togglePauseAllVideos")
                  v-icon(left class="common-dark-btn__icon") {{ isPaused ? icons.mdiPlay : icons.mdiPause }}
                  span {{ isPaused ? '재생' : '일시정지' }}
                v-btn.play-all-btn.common-dark-btn(color="gray" @click="stopAllVideos")
                  v-icon(left class="common-dark-btn__icon") {{ icons.mdiStop }}
                  span 중지

        .tw-flex.tw-mt-4.tw-gap-4
          .tw-flex-1
            .button-box.button-box-dark.tw-p-4
              v-data-table(
                :headers="cameraHeaders"
                :items="cameras"
                :loading="loading"
                hide-default-header
                class="elevation-1"
              )
                template(#item.selected="{ item }")
                  v-checkbox(
                    v-model="item.selected"
                    @change="handleCameraSelectionChange(item)"
                  )
                template(#item.name="{ item }")
                  span {{ item.name }}
          .tw-w-96
            .button-box.button-box-dark.tw-p-4
              v-date-picker(
                v-model="selectedDate"
                :first-day-of-week="1"
                locale="ko"
                color="primary"
                elevation="0"
                full-width
                @change="handleDateChange"
              )

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
                @change="handleSelectionChange(item)"
              )
            
            template(#item.formattedStartTime="{ item }")
              span {{ item.formattedStartTime }}
            
            template(#item.formattedEndTime="{ item }")
              span {{ item.formattedEndTime }}
            
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
import { getRecordingHistory} from '@/api/recordingService.api.js';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { getCameras } from '@/api/cameras.api';

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
    isPaused: false,
    cameraHeaders: [
      { text: '선택', value: 'selected', sortable: false, width: '80px' },
      { text: '카메라', value: 'name', sortable: true }
    ],
    cameras: [],
    selectedDate: new Date().toISOString().substr(0, 10),
  }),

  computed: {
    formattedRecordingHistory() {
      if (!this.recordingHistory || !Array.isArray(this.recordingHistory)) {
        return [];
      }
      
      return this.recordingHistory.map((record) => ({
        ...record,
        formattedStartTime: this.formatDateTime(record.startTime),
        formattedEndTime: this.formatDateTime(record.endTime),
        selected: false
      }));
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
    }
  },

  created() {
    this.loadRecordingHistory();
    this.loadCameras();
  },

  mounted() {
    this.fetchRecordingHistory();
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
      if (item.selected) {
        if (!this.selectedVideo1) {
          this.selectedVideo1 = `/api/recordings/stream/${item.id}`;
        } else if (!this.selectedVideo2) {
          this.selectedVideo2 = `/api/recordings/stream/${item.id}`;
        } else {
          item.selected = false;
          this.$toast.warning('최대 2개의 영상만 선택할 수 있습니다.');
        }
      } else {
        if (this.selectedVideo1 === `/api/recordings/stream/${item.id}`) {
          this.selectedVideo1 = null;
        } else if (this.selectedVideo2 === `/api/recordings/stream/${item.id}`) {
          this.selectedVideo2 = null;
        }
      }
    },

    playAllVideos() {
      if (this.$refs.videoPlayer1) {
        this.$refs.videoPlayer1.play();
      }
      if (this.$refs.videoPlayer2) {
        this.$refs.videoPlayer2.play();
      }
    },

    togglePauseAllVideos() {
      if (this.isPaused) {
        if (this.$refs.videoPlayer1) this.$refs.videoPlayer1.play();
        if (this.$refs.videoPlayer2) this.$refs.videoPlayer2.play();
      } else {
        if (this.$refs.videoPlayer1) this.$refs.videoPlayer1.pause();
        if (this.$refs.videoPlayer2) this.$refs.videoPlayer2.pause();
      }
      this.isPaused = !this.isPaused;
    },

    stopAllVideos() {
      if (this.$refs.videoPlayer1) {
        this.$refs.videoPlayer1.pause();
        this.$refs.videoPlayer1.currentTime = 0;
      }
      if (this.$refs.videoPlayer2) {
        this.$refs.videoPlayer2.pause();
        this.$refs.videoPlayer2.currentTime = 0;
      }
    },

    formatDateTime(date) {
      if (!date) return '';
      try {
        return format(new Date(date), 'yyyy-MM-dd HH:mm:ss', { locale: ko });
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
      this.$toast.error('비디오를 재생할 수 없습니다.');
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
        if (response && Array.isArray(response)) {
          this.cameras = response.map(camera => ({
            ...camera,
            selected: false
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
    },

    handleDateChange(date) {
      // 날짜 변경 처리
      console.log('Selected date:', date);
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
</style> 
