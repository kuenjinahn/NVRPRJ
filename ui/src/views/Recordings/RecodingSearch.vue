<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.recording-search
  v-container(fluid)
    v-row
      v-col(cols="12")
        v-card.search-card.mb-4
          v-card-title.search-title
            v-icon.mr-2(color="primary") {{ icons.mdiMagnify }}
            span 녹화 기록 검색
            v-spacer
            v-btn(
              color="primary"
              text
              @click="resetFilters"
              :disabled="!hasActiveFilters"
            )
              v-icon.mr-1 {{ icons.mdiRefresh }}
              span 초기화
          v-divider
          v-card-text.search-content
            v-row(align="center" justify="start")
              v-col(cols="12" sm="2")
                v-text-field(
                  v-model="searchFilters.cameraName"
                  label="카메라 이름"
                  prepend-inner-icon="mdi-camera"
                  dense
                  outlined
                  hide-details="auto"
                  clearable
                  @input="handleSearch"
                )
              v-col(cols="12" sm="2")
                v-text-field(
                  v-model="searchFilters.filename"
                  label="파일명"
                  prepend-inner-icon="mdi-file"
                  dense
                  outlined
                  hide-details="auto"
                  clearable
                  @input="handleSearch"
                )
              v-col(cols="12" sm="3")
                v-menu(
                  ref="dateMenu"
                  v-model="dateMenu"
                  :close-on-content-click="false"
                  transition="scale-transition"
                  offset-y
                  max-width="290px"
                  min-width="290px"
                )
                  template(v-slot:activator="{ on, attrs }")
                    v-text-field(
                      v-model="searchFilters.dateRangeText"
                      label="날짜 범위"
                      prepend-inner-icon="mdi-calendar"
                      dense
                      outlined
                      hide-details="auto"
                      readonly
                      v-bind="attrs"
                      v-on="on"
                      clearable
                      color="secondary"
                      @click:clear="clearDateRange"
                    )
                  v-date-picker(
                    v-model="searchFilters.dateRange"
                    range
                    no-title
                    scrollable
                    color="secondary"
                    @change="handleDateRangeChange"
                  )
              v-col(cols="12" sm="2")
                v-select(
                  v-model="searchFilters.status"
                  :items="statusOptions"
                  label="상태"
                  prepend-inner-icon="mdi-checkbox-marked-circle"
                  dense
                  outlined
                  hide-details="auto"
                  clearable
                  @input="handleSearch"
                )
              <!-- v-col(cols="12" sm="4")
                v-chip-group(
                  v-if="activeFiltersCount > 0"
                  column
                )
                  v-chip(
                    v-if="searchFilters.cameraName"
                    small
                    close
                    @click:close="searchFilters.cameraName = ''"
                  )
                    v-icon(left small) {{ icons.mdiCamera }}
                    | {{ searchFilters.cameraName }}
                  v-chip(
                    v-if="searchFilters.filename"
                    small
                    close
                    @click:close="searchFilters.filename = ''"
                  )
                    v-icon(left small) {{ icons.mdiFile }}
                    | {{ searchFilters.filename }}
                  v-chip(
                    v-if="searchFilters.dateRange.length === 2"
                    small
                    close
                    @click:close="clearDateRange"
                  )
                    v-icon(left small) {{ icons.mdiCalendar }}
                    | {{ searchFilters.dateRangeText }}
                  v-chip(
                    v-if="searchFilters.status"
                    small
                    close
                    @click:close="searchFilters.status = ''"
                  )
                    v-icon(left small) {{ icons.mdiCheckboxMarkedCircle }}
                    | {{ getStatusText(searchFilters.status) }} -->
    v-row
      v-col(cols="12")
        v-card
          v-data-table(
            :headers="headers"
            :items="filteredRecordingHistory"
            :loading="loading"
            :items-per-page="10"
            class="elevation-1"
            @click:row="handleRowClick"
          )
            template(#item.cameraName="{ item }")
              span {{ item.cameraName }}
            
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
            
            template(#item.actions="{ item }")
              v-btn(
                icon
                small
                @click.stop="confirmDelete(item)"
                color="error"
                class="delete-btn"
              )
                v-icon(color="red") {{ icons.mdiDelete }}
                span(class="error--text") 삭제
            
            template(#no-data)
              .text-center.pa-4
                v-icon(color="grey" size="40") {{ icons.mdiVideo }}
                .mt-2 녹화 기록이 없습니다.

  // 비디오 플레이어 다이얼로그
  v-dialog(
    v-model="videoDialog"
    max-width="800px"
    persistent
  )
    v-card.video-player-card
      v-card-title.d-flex.align-center
        span.text-h6 {{ selectedVideo ? selectedVideo.cameraName : '' }} 녹화 영상
        v-spacer
        v-btn(
          icon
          color="white"
          @click="closeVideoDialog"
        )
          v-icon {{ icons.mdiClose }}
      v-divider
      v-card-text.pa-0
        .video-container.tw-flex.tw-flex-col.tw-gap-4(style="position:relative;")
          .video-player.tw-flex-1.tw-flex.tw-justify-center
            video(
              ref="videoPlayer"
              controls
              :src="videoUrl"
              @error="handleVideoError"
              crossorigin="anonymous"
              preload="metadata"
              controlsList="nodownload"
              width="576"
              height="324"
              style="background:#000; max-width:100%; display:block;"
            )
          .video-info.mt-4.tw-flex.tw-justify-center
            v-card.elevation-2.tw-w-full.tw-max-w-xl.tw-p-4.tw-bg-gray-800.tw-border.tw-border-gray-600
              v-row
                v-col(cols="12" sm="6")
                  v-list-item(dense)
                    v-list-item-icon
                      v-icon {{ icons.mdiCamera }}
                    v-list-item-content
                      v-list-item-title 카메라
                      v-list-item-subtitle(style="color:white;") {{ selectedVideo ? selectedVideo.cameraName : '' }}
                v-col(cols="12" sm="6")
                  v-list-item(dense)
                    v-list-item-icon
                      v-icon {{ icons.mdiCalendar }}
                    v-list-item-content
                      v-list-item-title 녹화 시작
                      v-list-item-subtitle(style="color:white;") {{ selectedVideo ? selectedVideo.formattedStartTime : '' }}
                v-col(cols="12" sm="6")
                  v-list-item(dense)
                    v-list-item-icon
                      v-icon {{ icons.mdiClockOutline }}
                    v-list-item-content
                      v-list-item-title 녹화 종료
                      v-list-item-subtitle(style="color:white;") {{ selectedVideo ? selectedVideo.formattedEndTime : '' }}
                v-col(cols="12" sm="6")
                  v-list-item(dense)
                    v-list-item-icon
                      v-icon {{ icons.mdiFile }}
                    v-list-item-content
                      v-list-item-title 파일명
                      v-list-item-subtitle(style="color:white; white-space:normal; word-break:break-all;") {{ selectedVideo ? selectedVideo.filename : '' }}
        .error-container.pa-4(v-if="videoError")
          v-alert(
            type="error"
            text
            dense
          ) {{ videoError }}
      v-card-actions.pa-4
        v-spacer
        v-btn.close-btn(
          color="white"
          text
          @click="closeVideoDialog"
        ) 닫기

  // 삭제 확인 다이얼로그
  v-dialog(
    v-model="deleteDialog"
    max-width="400"
  )
    v-card
      v-card-title.headline 녹화 삭제
      v-card-text
        span(style="color: white;") 선택한 녹화를 삭제하시겠습니까?
        .mt-2.grey--text.text--darken-1 {{ selectedRecordingToDelete ? selectedRecordingToDelete.filename : '' }}
      v-card-actions
        v-spacer
        v-btn(
          color="white"
          text
          @click="deleteDialog = false"
        ) 취소
        v-btn(
          color="error"
          @click="executeDelete"
          :loading="deleteLoading"
        ) 삭제
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
  mdiPlay
} from '@mdi/js'
import { getRecordingHistory} from '@/api/recordingService.api.js';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';

export default {
  name: 'RecodingSearch',

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
      mdiPlay
    },
    loading: false,
    recordingHistory: [],
    thumbnails: {},
    dateMenu: false,
    searchFilters: {
      cameraName: '',
      filename: '',
      dateRange: [],
      dateRangeText: '',
      status: ''
    },
    headers: [
      { text: '카메라', value: 'cameraName' },
      { text: '시작 시간', value: 'formattedStartTime' },
      { text: '종료 시간', value: 'formattedEndTime' },
      { text: '파일명', value: 'filename' },
      { text: '상태', value: 'status' },
      { text: '작업', value: 'actions', sortable: false, align: 'center' }
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
    deleteDialog: false,
    selectedRecordingToDelete: null,
    deleteLoading: false,
    thumbnailErrors: {},
    imageData: new Map(),
  }),

  computed: {
    formattedRecordingHistory() {
      return this.recordingHistory.map((record) => ({
        ...record,
        formattedStartTime: this.formatDateTime(record.startTime),
        formattedEndTime: this.formatDateTime(record.endTime)
      }));
    },

    hasActiveFilters() {
      return this.activeFiltersCount > 0
    },

    activeFiltersCount() {
      let count = 0
      if (this.searchFilters.cameraName) count++
      if (this.searchFilters.filename) count++
      if (this.searchFilters.dateRange.length === 2) count++
      if (this.searchFilters.status) count++
      return count
    },

    filteredRecordingHistory() {
      return this.formattedRecordingHistory.filter((record) => {
        const matchCamera = !this.searchFilters.cameraName ||
          record.cameraName.toLowerCase().includes(this.searchFilters.cameraName.toLowerCase())

        const matchFilename = !this.searchFilters.filename ||
          record.filename.toLowerCase().includes(this.searchFilters.filename.toLowerCase())

        const matchStatus = !this.searchFilters.status ||
          record.status === this.searchFilters.status

        let matchDate = true
        if (this.searchFilters.dateRange.length === 2) {
          const recordDate = new Date(record.startTime)
          const startDate = new Date(this.searchFilters.dateRange[0])
          const endDate = new Date(this.searchFilters.dateRange[1])
          endDate.setHours(23, 59, 59, 999)
          matchDate = recordDate >= startDate && recordDate <= endDate
        }

        return matchCamera && matchFilename && matchDate && matchStatus
      })
    }
  },

  watch: {

  },

  created() {
    // Vue 개발자 도구에서 thumbnails 객체를 쉽게 확인할 수 있도록 전역 변수로 할당
    if (process.env.NODE_ENV === 'development') {
      window.$thumbnails = this.thumbnails;
    }
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
              status: data.status || 'error'
            };
          });
          console.log('Mapped recording history:', this.recordingHistory);
          await this.fetchThumbnails();
        } else {
          console.error('Invalid response format:', response);
          this.recordingHistory = [];
        }
      } catch (error) {
        console.error('Failed to fetch recording history:', error);
        this.recordingHistory = [];
      } finally {
        this.loading = false;
      }
    },

    async fetchThumbnails() {
      console.log('Starting fetchThumbnails...');
      for (const record of this.recordingHistory) {
        if (!record.id) {
          console.warn('Record missing ID:', record);
          continue;
        }
        
        try {
          // 녹화 파일명에서 확장자를 제거하고 .png로 변경
          const thumbnailFilename = record.filename.replace(/\.[^/.]+$/, '.png');
          const thumbnailUrl = `/api/recordings/thumbnail/${record.id}/${thumbnailFilename}`;
          
          // 섬네일 URL을 저장
          this.$set(this.thumbnails, record.id, thumbnailUrl);
          
          // 이미지 로드 테스트
          const img = new Image();
          img.onload = () => {
            console.log(`Thumbnail loaded successfully for recording ${record.id}`);
          };
          img.onerror = () => {
            console.warn(`Failed to load thumbnail for recording ${record.id}`);
            this.$set(this.thumbnailErrors, record.id, true);
            this.$set(this.thumbnails, record.id, '/assets/images/no-thumbnail.jpg');
          };
          img.src = thumbnailUrl;
          
        } catch (error) {
          console.error(`Error setting thumbnail for recording ${record.id}:`, error);
          this.$set(this.thumbnailErrors, record.id, true);
          this.$set(this.thumbnails, record.id, '/assets/images/no-thumbnail.jpg');
        }
      }
    },

    handleSearch() {
      // 검색 조건이 변경될 때마다 필터링된 결과가 자동으로 업데이트됩니다
      // computed 속성인 filteredRecordingHistory가 처리합니다
    },

    handleDateRangeChange(range) {
      if (range.length === 2) {
        this.dateMenu = false;
        this.searchFilters.dateRange = range;
        this.searchFilters.dateRangeText = `${this.formatDateTime(range[0])} ~ ${this.formatDateTime(range[1])}`;
      }
    },

    clearDateRange() {
      this.searchFilters.dateRange = [];
      this.searchFilters.dateRangeText = '';
    },

    formatDateTime(dateString) {
      if (!dateString) {
        return '-';
      }
      try {
        const parsed = new Date(dateString);
        if (isNaN(parsed.getTime())) return '-';
        return format(parsed, 'yyyy-MM-dd HH:mm:ss', { locale: ko });
      } catch (error) {
        console.error('Error formatting date:', error);
        return '-';
      }
    },

    getStatusColor(status) {
      const colors = {
        recording: 'success',
        completed: 'info',
        error: 'error',
        stopped: 'warning'
      };
      return colors[status] || 'grey';
    },

    getStatusText(status) {
      const texts = {
        recording: '녹화중',
        completed: '완료',
        error: '오류',
        stopped: '중지됨'
      };
      return texts[status] || status;
    },

    resetFilters() {
      this.searchFilters = {
        cameraName: '',
        filename: '',
        dateRange: [],
        dateRangeText: '',
        status: ''
      }
    },

    async handleRowClick(record) {
      if (!record || !record.id) {
        console.error('Invalid record:', record);
        return;
      }
      this.selectedVideo = record;
      this.videoError = null;
      this.videoDialog = true;

      try {
        // stream API를 녹화 id로 요청 (프록시를 통해 백엔드로 전달)
        this.videoUrl = `/api/recordings/stream/${record.id}`;
        // 비디오 요소 설정
        if (this.$refs.videoPlayer) {
          const video = this.$refs.videoPlayer;
          video.load();
        }

      } catch (error) {
        console.error('Error setting video URL:', error);
        this.videoError = '비디오를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.';
      }
    },

    handleVideoError(event) {
      const videoElement = this.$refs.videoPlayer;
      console.error('Video error:', {
        error: event,
        videoState: videoElement ? {
          readyState: videoElement.readyState,
          networkState: videoElement.networkState,
          error: videoElement.error,
          currentSrc: videoElement.currentSrc
        } : null
      });

      let errorMessage = '비디오를 재생할 수 없습니다.';
      
      if (videoElement?.error) {
        switch (videoElement.error.code) {
          case 1:
            errorMessage = '재생이 중단되었습니다.';
            break;
          case 2:
            errorMessage = '네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
            this.retryVideoLoad();
            break;
          case 3:
            errorMessage = '비디오 형식이 올바르지 않습니다.';
            break;
          case 4:
            errorMessage = '비디오 파일을 찾을 수 없습니다.';
            break;
        }
      }

      this.videoError = errorMessage;
    },

    retryVideoLoad() {
      if (this.$refs.videoPlayer && this.videoUrl) {
        console.log('Retrying video load...');
        const video = this.$refs.videoPlayer;
        
        // 현재 시간 위치 저장
        const currentTime = video.currentTime;
        
        // 비디오 다시 로드
        setTimeout(() => {
          video.load();
          video.currentTime = currentTime;
        }, 2000);
      }
    },

    closeVideoDialog() {
      if (this.$refs.videoPlayer) {
        this.$refs.videoPlayer.pause();
      }
      this.videoDialog = false;
      this.selectedVideo = null;
      this.videoUrl = null;
      this.videoError = null;
    },

    confirmDelete(recording) {
      this.selectedRecordingToDelete = recording;
      this.deleteDialog = true;
    },

    async executeDelete() {
      if (!this.selectedRecordingToDelete) return;

      this.deleteLoading = true;
      try {
        // 로컬 스토리지에서 사용자 정보 가져오기
        const user = JSON.parse(localStorage.getItem('user'));
        if (!user || !user.access_token) {
          throw new Error('인증 토큰이 없습니다. 다시 로그인해주세요.');
        }

        const response = await fetch(`/api/recordings/${this.selectedRecordingToDelete.id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${user.access_token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          // 토큰 만료 체크
          if (response.status === 401) {
            await this.$store.dispatch('auth/logout');
            this.$router.push('/');
            throw new Error('세션이 만료되었습니다. 다시 로그인해주세요.');
          }
          throw new Error(errorData.message || '녹화 삭제에 실패했습니다.');
        }

        await this.fetchRecordingHistory();
        this.$toast.success('녹화가 성공적으로 삭제되었습니다.');
        this.deleteDialog = false;
      } catch (error) {
        console.error('Error deleting recording:', error);
        this.$toast.error(error.message || '녹화 삭제 중 오류가 발생했습니다.');
      } finally {
        this.deleteLoading = false;
        this.selectedRecordingToDelete = null;
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

    playAllVideos() {
      // Implementation of playAllVideos method
    },
  }
};
</script>

<style lang="scss">
.recording-search {
  padding: 20px;

  .search-card {
    background-color: var(--cui-bg-gray-800) !important;
    border: 1px solid rgba(var(--cui-bg-nav-border-rgb));
    border-radius: 8px;
    
    .search-title {
      color: var(--cui-text-default) !important;
      background-color: var(--cui-bg-gray-800) !important;
      padding: 16px 20px;
      display: flex;
      align-items: center;
      
      .v-icon {
        margin-right: 8px;
      }
    }

    .search-content {
      background-color: var(--cui-bg-gray-800) !important;
      padding: 20px;
    }
  }

  .v-text-field {
    background-color: var(--cui-bg-gray-700) !important;
  }

  .v-text-field >>> .v-label {
    color: var(--cui-text-default) !important;
  }

  .v-text-field >>> .v-input__slot {
    background-color: var(--cui-bg-gray-700) !important;
    border-color: var(--cui-border-color) !important;
  }

  .v-text-field >>> input {
    color: var(--cui-text-default) !important;
  }

  .v-text-field >>> .v-icon {
    color: var(--cui-text-default) !important;
  }

  .v-select {
    background-color: var(--cui-bg-gray-700) !important;
  }

  .v-select >>> .v-label {
    color: var(--cui-text-default) !important;
  }

  .v-select >>> .v-input__slot {
    background-color: var(--cui-bg-gray-700) !important;
    border-color: var(--cui-border-color) !important;
  }

  .v-select >>> .v-select__selection {
    color: var(--cui-text-default) !important;
  }

  .v-select >>> .v-icon {
    color: var(--cui-text-default) !important;
  }

  .v-menu__content {
    background-color: var(--cui-bg-gray-700) !important;
    border: 1px solid var(--cui-border-color) !important;
  }

  .v-date-picker-table {
    background-color: var(--cui-bg-gray-700) !important;
  }

  .v-date-picker-table >>> .v-btn {
    color: var(--cui-text-default) !important;
  }

  .v-date-picker-table >>> .v-btn--active {
    background-color: var(--cui-primary) !important;
    color: white !important;
  }

  .v-chip {
    background-color: var(--cui-bg-gray-700) !important;
    color: var(--cui-text-default) !important;
  }

  .v-chip >>> .v-icon {
    color: var(--cui-text-default) !important;
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
        max-width: 576px;
        width: 100%;
        margin: 0 auto;
        .v-card {
          background: var(--cui-bg-gray-800) !important;
          border: 1.5px solid var(--cui-border-color) !important;
          border-radius: 12px !important;
          box-shadow: 0 2px 12px rgba(0,0,0,0.12) !important;
        }
        .v-list-item-title, .v-list-item-subtitle {
          color: white !important;
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

  .v-card-title {
    color: var(--cui-text-default) !important;
    font-size: 1.25rem;
    font-weight: 500;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(var(--cui-bg-nav-border-rgb));
  }

  .v-btn {
    color: var(--cui-text-default) !important;
    
    &.v-btn--icon {
      background-color: var(--cui-bg-gray-700);
      border-radius: 4px;
      padding: 8px;
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

  .custom-play-btn {
    background: #222e50 !important;
    color: #fff !important;
    border-radius: 8px !important;
    font-weight: bold !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    min-width: 120px;
    min-height: 40px;
  }

  .custom-play-btn:hover {
    background: #1a1f3c !important;
    color: #ffd700 !important;
  }

  .video-player video {
    width: 480px !important;
    height: 270px !important;
    background: #000;
  }

  .icon-btn.rounded-circle {
    border-radius: 50% !important;
    min-width: 40px !important;
    min-height: 40px !important;
    background: rgba(255,255,255,0.08) !important;
    color: #fff !important;
    transition: background 0.2s;
  }

  .icon-btn.rounded-circle:hover {
    background: var(--cui-primary) !important;
    color: #fff !important;
  }
}
</style> 
