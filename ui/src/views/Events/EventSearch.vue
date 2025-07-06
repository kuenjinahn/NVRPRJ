<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.recording-search
  v-container(fluid)
    v-row
      v-col(cols="12")
        v-card.search-card.mb-4
          v-card-title.search-title
            v-icon.mr-2(color="primary") {{ icons.mdiMagnify }}
            span 이벤트 이력 조회
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
                  v-model="searchFilters.eventType"
                  label="감지 대상"
                  prepend-inner-icon="mdi-camera"
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
              <!-- v-col(cols="12" sm="4")
                v-chip-group(
                  v-if="activeFiltersCount > 0"
                  column
                )
                  v-chip(
                    v-if="searchFilters.eventType"
                    color="secondary"
                    small
                    close
                    @click:close="searchFilters.eventType = ''"
                  )
                    v-icon(left small) {{ icons.mdiCamera }}
                    | {{ searchFilters.eventType }}
                  v-chip(
                    v-if="searchFilters.dateRange.length === 2"
                    color="secondary"
                    small
                    close
                    @click:close="clearDateRange"
                  )
                    v-icon(left small) {{ icons.mdiCalendar }}
                    | {{ searchFilters.dateRangeText }} -->
    v-row
      v-col(cols="12")
        v-card
          v-data-table(
            :headers="headers"
            :items="events"
            :server-items-length="totalItems"
            :page.sync="page"
            :items-per-page.sync="pageSize"
            :loading="loading"
            loading-text="데이터를 불러오는 중..."
            no-data-text="데이터가 없습니다"
            class="elevation-1"
            @update:page="val => { page = val; }"
            @update:items-per-page="val => { pageSize = val; page = 1; }"
          )
            template(#item.status="{ item }")
              v-chip(
                :color="getStatusColor(item.status)"
                small
                label
              ) {{ item.status }}
            
            template(#item.liveView="{ item }")
              v-btn(
                small
                color="secondary"
                @click="goToLiveView(item)"
              )
                v-icon(left small) {{ icons.mdiPlay }}
                live
            
            template(#item.recordingView="{ item }")
              v-btn(
                small
                color="secondary"
                @click="goToRecording(item)"
              )
                v-icon(left small) {{ icons.mdiVideo }}
                recoding
            
            template(#item.event_accur_time="{ item }")
              span {{ formatDateTime(item.event_accur_time) }}
            template(#item.event_type="{ item }")
              span {{ getEventTypeText(item.event_type) }}
            template(#item.event_data_json="{ item }")
              span {{ getLabelsFromEventData(item.event_data_json) }}
            template(#item.fk_detect_zone_id="{ item }")
              span {{ getDetectZoneText(item.fk_detect_zone_id) }}
            template(#item.detected_image_url="{ item }")
              v-btn(
                small
                color="secondary"
                @click="showImageDialog(item)"
                v-if="item.detected_image_url"
              ) 이미지 보기
            
            template(#item.create_date="{ item }")
              span {{ formatDateTime(item.create_date) }}
            template(#no-data)
              .text-center.pa-4
                v-icon(color="grey" size="40") {{ icons.mdiAlert }}
                .mt-2 이벤트 기록이 없습니다.

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
          @click="closeVideoDialog"
        )
          v-icon {{ icons.mdiClose }}
      v-divider
      v-card-text.pa-0
        .video-container.tw-flex.tw-gap-4(style="position:relative;")
          .video-player.tw-flex-1
            video(
              ref="videoPlayer"
              controls
              :src="videoUrl"
              @error="handleVideoError"
              crossorigin="anonymous"
              preload="metadata"
              controlsList="nodownload"
              width="480"
              height="270"
              style="background:#000;"
            )
          .video-info.mt-4
            v-row
              v-col(cols="12" sm="6")
                v-list-item(dense)
                  v-list-item-icon
                    v-icon {{ icons.mdiCamera }}
                  v-list-item-content
                    v-list-item-title 카메라
                    v-list-item-subtitle {{ selectedVideo ? selectedVideo.cameraName : '' }}
              v-col(cols="12" sm="6")
                v-list-item(dense)
                  v-list-item-icon
                    v-icon {{ icons.mdiCalendar }}
                  v-list-item-content
                    v-list-item-title 녹화 시작
                    v-list-item-subtitle {{ selectedVideo ? selectedVideo.formattedStartTime : '' }}
              v-col(cols="12" sm="6")
                v-list-item(dense)
                  v-list-item-icon
                    v-icon {{ icons.mdiClockOutline }}
                  v-list-item-content
                    v-list-item-title 녹화 종료
                    v-list-item-subtitle {{ selectedVideo ? selectedVideo.formattedEndTime : '' }}
              v-col(cols="12" sm="6")
                v-list-item(dense)
                  v-list-item-icon
                    v-icon {{ icons.mdiFile }}
                  v-list-item-content
                    v-list-item-title 파일명
                    v-list-item-subtitle {{ selectedVideo ? selectedVideo.filename : '' }}
        .error-container.pa-4(v-if="videoError")
          v-alert(
            type="error"
            text
            dense
          ) {{ videoError }}
      v-card-actions.pa-4
        v-spacer
        v-btn.close-btn(
          color="secondary"
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
        | 선택한 녹화를 삭제하시겠습니까?
        .mt-2.grey--text.text--darken-1 {{ selectedRecordingToDelete ? selectedRecordingToDelete.filename : '' }}
      v-card-actions
        v-spacer
        v-btn(
          text
          @click="deleteDialog = false"
        ) 취소
        v-btn(
          color="error"
          @click="executeDelete"
          :loading="deleteLoading"
        ) 삭제

  // 이미지 팝업
  v-dialog(
    v-model="imageDialog"
    max-width="600"
  )
    v-card
      v-card-title 감지 이미지
      v-card-text
        img(:src="imageDialogUrl" style="max-width:100%;max-height:500px;" v-if="imageDialogUrl")
      v-card-actions
        v-spacer
        v-btn(color="white" text @click="imageDialog=false") 닫기
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
import { getEventHistory } from '@/api/eventHistory.api.js';

export default {
  name: 'EventSearch',

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
    eventHistory: [],
    thumbnails: {},
    dateMenu: false,
    searchFilters: {
      eventType: '',
      dateRange: [],
      dateRangeText: ''
    },
    eventTypeOptions: [
      { text: '객체', value: 'OBJECT' },
      { text: '온도', value: 'TEMP' }
    ],
    headers: [
      { text: 'ID', value: 'id' },
      { text: '카메라명', value: 'camera_name' },
      { text: '이벤트시각', value: 'event_accur_time', align: 'center' },
      { text: '타입', value: 'event_type', align: 'center' },
      { text: '감지대상', value: 'event_data_json', align: 'center' },
      { text: '감지영역', value: 'fk_detect_zone_id', align: 'center' },
      { text: '이미지', value: 'detected_image_url', align: 'center' },
      { text: '등록일시', value: 'create_date', align: 'center' }
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
    events: [],
    imageDialog: false,
    imageDialogUrl: null,
    page: 1,
    pageSize: 10,
    totalItems: 0,
  }),

  computed: {
    formattedEventHistory() {
      return this.eventHistory.map((record) => ({
        ...record,
        formattedStartTime: this.formatDateTime(record.event_accur_time),
        formattedEndTime: this.formatDateTime(record.event_accur_time)
      }));
    },

    hasActiveFilters() {
      return !!this.searchFilters.eventType || this.searchFilters.dateRange.length === 2;
    },

    activeFiltersCount() {
      let count = 0
      if (this.searchFilters.eventType) count++
      if (this.searchFilters.dateRange.length === 2) count++
      return count
    },

    filteredEventHistory() {
      return this.formattedEventHistory.filter((record) => {
        const matchType = !this.searchFilters.eventType ||
          record.eventType === this.searchFilters.eventType

        let matchDate = true
        if (this.searchFilters.dateRange.length === 2) {
          const recordDate = new Date(record.event_accur_time)
          const startDate = new Date(this.searchFilters.dateRange[0])
          const endDate = new Date(this.searchFilters.dateRange[1])
          endDate.setHours(23, 59, 59, 999)
          matchDate = recordDate >= startDate && recordDate <= endDate
        }

        return matchType && matchDate
      })
    }
  },

  watch: {
    page() {
      this.loadEvents();
    },
    pageSize() {
      this.page = 1;
      this.loadEvents();
    }
  },

  created() {
    // Vue 개발자 도구에서 thumbnails 객체를 쉽게 확인할 수 있도록 전역 변수로 할당
    if (process.env.NODE_ENV === 'development') {
      window.$thumbnails = this.thumbnails;
    }
  },

  mounted() {
    this.loadEvents();
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
    async loadEvents() {
      this.loading = true;
      try {
        const filters = {
          page: this.page,
          pageSize: this.pageSize
        };
        if (this.searchFilters.eventType) filters.label = this.searchFilters.eventType;
        if (this.searchFilters.dateRange.length === 2) {
          filters.startDate = this.searchFilters.dateRange[0];
          filters.endDate = this.searchFilters.dateRange[1];
        }
        const response = await getEventHistory(filters);
        this.events = response.result;
        this.totalItems = response.pagination?.totalItems || 0;
      } catch (error) {
        console.error('이벤트 이력 조회 실패:', error);
        this.$toast?.error('이벤트 이력을 불러오는 중 오류가 발생했습니다.');
      } finally {
        this.loading = false;
      }
    },

    async handleSearch() {
      // 검색 조건이 변경될 때마다 필터링된 결과가 자동으로 업데이트됩니다
      // computed 속성인 filteredEventHistory가 처리합니다
      await this.loadEvents();
      console.log('handleSearch', this.searchFilters)
    },

    async handleDateRangeChange(range) {
      if (range.length === 2) {
        this.dateMenu = false;
        this.searchFilters.dateRange = range;
        this.searchFilters.dateRangeText = `${this.formatDateTime(range[0])} ~ ${this.formatDateTime(range[1])}`;
        await this.loadEvents();
      }
    },

    clearDateRange() {
      this.searchFilters.dateRange = [];
      this.searchFilters.dateRangeText = '';
    },

    formatDateTime(dateString) {
      if (!dateString) return '-';
      
      // UTC 시간을 한국 시간(KST)으로 변환
      const date = new Date(dateString)
      
      // UTC에 9시간(KST 오프셋)을 더함
      const kstTime = new Date(date.getTime())
      
      return kstTime.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      })
    },

    getStatusColor(status) {
      switch (status) {
        case '미처리':
          return 'error'
        case '대기':
          return 'warning'
        case '처리':
          return 'success'
        default:
          return 'grey'
      }
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
      this.searchFilters = { eventType: '', dateRange: [], dateRangeText: '' };
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
        // stream API를 녹화 id로 요청
        const host = process.env.VUE_APP_STREAM_HOST;
        this.videoUrl = `http://${host}:9091/api/recordings/stream/${record.id}`;
        
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

        const host = process.env.VUE_APP_STREAM_HOST;
        const response = await fetch(`http://${host}:9091/api/recordings/${this.selectedRecordingToDelete.id}`, {
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

        await this.loadEvents();
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

    goToLiveView(item) {
      // 라이브 영상으로 이동하는 로직
      console.log('Go to live view:', item)
      // TODO: 라이브 영상 페이지로 이동하는 로직 구현
    },

    goToRecording(item) {
      // 녹화 영상으로 이동하는 로직
      console.log('Go to recording:', item)
      // TODO: 녹화 영상 페이지로 이동하는 로직 구현
    },

    getEventTypeText(type) {
      switch (type) {
        case 'E001': return '객체검출';
        case 'E002': return '누수';
        case 'E003': return '균열';
        default: return type;
      }
    },

    getLabelsFromEventData(jsonStr) {
      try {
        const arr = JSON.parse(jsonStr);
        return arr.map(obj => obj.label).join(', ');
      } catch {
        return '';
      }
    },

    getDetectZoneText(id) {
      return id === 0 ? '전체' : id;
    },

    async showImageDialog(item) {
      try {
        const host = process.env.VUE_APP_STREAM_HOST;
        const url = `http://${host}:9091/api/image`;
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: item.detected_image_url })
        });
        const blob = await res.blob();
        this.imageDialogUrl = URL.createObjectURL(blob);
        this.imageDialog = true;
      } catch (e) {
        this.$toast && this.$toast.error('이미지를 불러올 수 없습니다.');
      }
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
}
</style> 
