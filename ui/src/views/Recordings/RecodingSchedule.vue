<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.recordings-manager
  v-container(fluid)
    v-row
      v-col(cols="12")
        .tw-flex.tw-justify-between.tw-items-center.tw-mb-4.tw-px-1
          span.tw-text-xl.tw-font-semibold.tw-text-white-800 녹화 스케줄 관리
          v-btn.add-schedule-btn(
            elevation="1"
            @click="openAddDialog"
            color="white"
            outlined
          )
            v-icon.tw-mr-2(size="20") {{ icons['mdiPlus'] }}
            span 스케줄 추가

        v-card.tw-mt-2
          v-data-table(
            :headers="headers"
            :items="formattedSchedules"
            :loading="loading"
            :items-per-page="10"
            class="elevation-1"
          )
            template(#[`item.formattedDays`]="{ item }")
              span {{ item.formattedDays }}
            
            template(#[`item.isActive`]="{ item }")
              v-switch(
                :input-value="item.isActive"
                @change="handleToggleStatus(item)"
                inset
                dense
              )
            
            template(#[`item.actions`]="{ item }")
              .tw-flex.tw-items-center.tw-gap-2
                v-btn.edit-btn(
                  color="white"
                  @click="editSchedule(item)"
                  outlined
                )
                  v-icon(left size="20") {{ icons['mdiPencil'] }}
                  span 수정
                v-btn.delete-btn(
                  color="error"
                  @click="deleteScheduleConfirm(item)"
                  outlined
                )
                  v-icon(left size="20") {{ icons['mdiDelete'] }}
                  span 삭제

    // 스케줄 추가/수정 다이얼로그
  v-dialog(
      v-model="dialog"
      max-width="600px"
    persistent
  )
      v-card
        v-card-title.pb-0.tw-flex.tw-items-center.tw-gap-2
          v-icon(v-if="isEdit" color="primary") {{ icons['mdiPencil'] }}
          v-icon(v-else color="primary") {{ icons['mdiPlus'] }}
          span.text-h5 {{ isEdit ? '스케줄 수정' : '새 스케줄 추가' }}
        v-card-text
          v-form.dialog-form-halfwidth(
            ref="form"
            v-model="valid"
          )
            v-select.dialog-field(
              v-model="editedItem.cameraName"
              :items="cameras"
              item-text="name"
              item-value="name"
              label="카메라"
              :rules="[v => !!v || '카메라를 선택해주세요']"
              required
              class="mt-4"
              @change="onCameraChange"
            )
            v-row
              v-col(cols="12" sm="6")
                v-text-field.dialog-field(
                  v-model="editedItem.startTime"
                  label="시작 시간"
                  type="time"
                  :rules="[v => !!v || '시작 시간을 입력해주세요']"
                  required
                )
              v-col(cols="12" sm="6")
                v-text-field.dialog-field(
                  v-model="editedItem.endTime"
                  label="종료 시간"
                  type="time"
                  :rules="[v => !!v || '종료 시간을 입력해주세요']"
                  required
                )
            v-select.dialog-field(
              v-model="editedItem.days"
              :items="daysOptions"
              item-text="text"
              item-value="value"
              label="요일 선택"
              multiple
              chips
              :rules="[v => v.length > 0 || '최소 하나의 요일을 선택해주세요']"
              required
            )
            v-select.dialog-field(
              v-model="editedItem.recordingType"
              :items="recordingTypes"
              label="녹화 유형"
              disabled
              :rules="[v => !!v || '녹화 유형을 선택해주세요']"
              required
            )
            v-select.dialog-field(
              v-model="editedItem.bitrate"
              :items="bitrateOptions"
              label="영상 Bitrate"
              :rules="[v => !!v || 'Bitrate를 선택해주세요']"
              required
            )
        v-card-actions
          .actions-wrapper
            v-btn.cancel-btn(@click="closeDialog") 취소
            v-btn.save-btn(:loading="saving" :disabled="!valid" @click="saveSchedule") {{ isEdit ? '수정' : '저장' }}

  v-dialog.delete-dialog(
      v-model="deleteDialog"
      max-width="400px"
    )
      v-card
        v-card-title.error--text.tw-flex.tw-items-center.tw-gap-2
          v-icon(color="error") {{ icons['mdiAlert'] }}
          span 스케줄 삭제
        v-card-text.tw-py-4
          .tw-mb-2.tw-font-medium.tw-text-white 다음 스케줄을 삭제하시겠습니까?
          .tw-bg-gray-50.tw-p-3.tw-rounded.tw-mb-4(v-if="selectedSchedule")
            .tw-mb-1
              span.tw-font-semibold 카메라: 
              span {{ selectedSchedule.cameraName }}
            .tw-mb-1
              span.tw-font-semibold 시간: 
              span {{ selectedSchedule.formattedStartTime }} - {{ selectedSchedule.formattedEndTime }}
            .tw-mb-1
              span.tw-font-semibold 요일: 
              span {{ selectedSchedule.formattedDays }}
          .tw-text-red-600 이 작업은 되돌릴 수 없습니다.
        v-card-actions
          .actions-wrapper
            v-btn.cancel-btn(@click="deleteDialog = false") 취소
            v-btn.save-btn(
              color="error"
              :loading="deleting"
              @click="deleteSchedule"
            ) 삭제
</template>

<script>
import { getCameras } from '@/api/cameras.api';
import { 
  mdiPlus,
  mdiPencil,
  mdiDelete,
  mdiAlert,
  mdiContentSave,
  mdiClose
} from '@mdi/js';
import {
  getSchedules,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  toggleSchedule
} from '@/api/recordingSchedule.api';

export default {
  name: 'RecodingsManager',

  data: () => ({
    icons: {
      mdiPlus,
      mdiPencil,
      mdiDelete,
      mdiAlert,
      mdiContentSave,
      mdiClose
    },
    loading: false,
    saving: false,
    deleting: false,
    dialog: false,
    deleteDialog: false,
    valid: true,
    isEdit: false,
    schedules: [],
    cameras: [],

    headers: [
      { text: '카메라', value: 'cameraName' },
      { text: '시작 시간', value: 'formattedStartTime' },
      { text: '종료 시간', value: 'formattedEndTime' },
      { text: '요일', value: 'formattedDays' },
      { text: '녹화 유형', value: 'recordingType' },
      { text: 'Bitrate', value: 'bitrate' },
      { text: '상태', value: 'isActive' },
      { text: '작업', value: 'actions', sortable: false, align: 'center' }
    ],

    editedItem: {
      id: null,
      cameraName: '',
      startTime: '',
      endTime: '',
      days: [],
      recordingType: 'Video',
      isActive: true,
      source: '',
      bitrate: '1024k'
    },

    defaultItem: {
      id: null,
      cameraName: '',
      startTime: '',
      endTime: '',
      days: [],
      recordingType: 'Video',
      isActive: true,
      source: '',
      bitrate: '1024k'
    },

    daysOptions: [
      { text: '일요일', value: 0 },
      { text: '월요일', value: 1 },
      { text: '화요일', value: 2 },
      { text: '수요일', value: 3 },
      { text: '목요일', value: 4 },
      { text: '금요일', value: 5 },
      { text: '토요일', value: 6 },
    ],

    recordingTypes: ['Video'],
    selectedSchedule: null,
    bitrateOptions: ['512k', '1024k', '2000k'],
  }),

  async mounted() {
    await this.loadCameras();
    await this.initialize();
  },

  methods: {
    async initialize() {
      this.loading = true;
      try {
        const response = await getSchedules();
        // Transform the data to match the expected format
        this.schedules = response.data.map(schedule => ({
          id: schedule.id,
          cameraName: schedule.cameraName,
          startTime: schedule.start_time || schedule.startTime,
          endTime: schedule.end_time || schedule.endTime,
          days: schedule.days_of_week || schedule.days || [],
          recordingType: schedule.recording_type || schedule.recordingType,
          isActive: schedule.isActive !== undefined ? schedule.isActive : true,
          source:schedule.source,
          bitrate: schedule.bitrate || '1024k'
        }));
      } catch (error) {
        console.error('Failed to fetch schedules:', error);
        this.$toast.error('스케줄 목록을 불러오는데 실패했습니다.');
      } finally {
      this.loading = false;
      }
    },

    async loadCameras() {
      try {
        const response = await getCameras();
        if (Array.isArray(response.data)) {
          this.cameras = response.data.map(camera => ({
            name: camera.name,
            source:camera.videoConfig.source,
            id:camera.id
          }));
        } else if (response.data && response.data.result) {
          this.cameras = response.data.result.map(camera => ({
            name: camera.name,
            source:camera.videoConfig.source,
            id:camera.id
          }));
        } else {
          console.error('Unexpected camera data format:', response.data);
          this.$toast.error('카메라 데이터 형식이 올바르지 않습니다.');
        }
        if (this.cameras.length === 0) {
          this.$toast.warning('등록된 카메라가 없습니다.');
        }
      } catch (error) {
        console.error('Failed to load cameras:', error);
        this.$toast.error('카메라 목록을 불러오는데 실패했습니다.');
      }
    },

    async openAddDialog() {
      this.isEdit = false;
      
      if (this.cameras.length === 0) {
        await this.loadCameras();
      }
      
      // 현재 시간 계산
      const now = new Date();
      const oneHourLater = new Date(now.getTime() + (60 * 2 * 1000));
      
      // HH:mm 형식으로 시간 포맷팅
      const formatTime = (date) => {
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
      };

      // 오늘 요일 가져오기 (0: 일요일, 6: 토요일)
      const today = now.getDay();
      this.editedItem = {
        id: null,
        cameraName: this.cameras.length > 0 ? this.cameras[0].name : '',
        startTime: formatTime(now),
        endTime: formatTime(oneHourLater),
        days: [today],
        recordingType: 'Video',
        isActive: true,
        source:this.cameras.length > 0 ? this.cameras[0].source : '',
        fk_camera_id:this.cameras.length > 0 ? this.cameras[0].id : '',
        bitrate: '1024k'
      };

      // 폼 초기화
      if (this.$refs.form) {
        this.$refs.form.resetValidation();
      }
      
      this.dialog = true;
    },

    async editSchedule(item) {
      this.isEdit = true;
      if (this.cameras.length === 0) {
        await this.loadCameras();
      }
      
      // 기존 데이터를 editedItem에 복사
      this.editedItem = {
        id: item.id,
        cameraName: item.cameraName,
        startTime: item.startTime || item.start_time,
        endTime: item.endTime || item.end_time,
        days: item.days || item.days_of_week || [],
        recordingType: item.recordingType || item.recording_type || 'Video',
        isActive: item.isActive !== undefined ? item.isActive : true,
        source: item.source,
        fk_camera_id: item.fk_camera_id,
        bitrate: item.bitrate || '1024k'
      };

      
      
      this.dialog = true;
      
      // 다음 틱에서 폼 유효성 검사 실행
      this.$nextTick(() => {
        if (this.$refs.form) {
          this.$refs.form.validate();
        }
      });
    },

    async saveSchedule() {
      if (this.$refs.form.validate()) {
        this.saving = true;
        try {
          // 데이터 유효성 검사 및 기본값 설정
          if (!this.editedItem.cameraName) {
            throw new Error('카메라를 선택해주세요.');
          }
          if (!Array.isArray(this.editedItem.days) || this.editedItem.days.length === 0) {
            throw new Error('요일을 선택해주세요.');
          }
          if (!this.editedItem.startTime) {
            throw new Error('시작 시간을 입력해주세요.');
          }
          if (!this.editedItem.endTime) {
            throw new Error('종료 시간을 입력해주세요.');
          }

          const scheduleData = {
            cameraName: this.editedItem.cameraName,
            days: this.editedItem.days,
            startTime: this.editedItem.startTime,
            endTime: this.editedItem.endTime,
            recordingType: this.editedItem.recordingType || 'Video',
            isActive: this.editedItem.isActive !== undefined ? this.editedItem.isActive : true,
            source:this.editedItem.source,
            fk_camera_id:this.editedItem.fk_camera_id,
            bitrate: this.editedItem.bitrate || '1024k'
          };
          console.log('Saving schedule with data:', scheduleData); // 디버깅용 로그

          let response;
          if (this.isEdit && this.editedItem.id) {
            response = await updateSchedule(this.editedItem.id, scheduleData);
            console.log('Update schedule response:', response); // 디버깅용 로그
            this.$toast.success('스케줄이 수정되었습니다.');
          } else {
            response = await createSchedule(scheduleData);
            console.log('Create schedule response:', response); // 디버깅용 로그
            this.$toast.success('새 스케줄이 추가되었습니다.');
          }
          
          await this.initialize();
          this.closeDialog();
        } catch (error) {
          console.error('Failed to save schedule:', error);
          this.$toast.error(error.response?.data?.error || error.message || '스케줄 저장에 실패했습니다.');
        } finally {
          this.saving = false;
        }
      } else {
        console.log('Form validation failed:', this.editedItem); // 디버깅용 로그
        this.$toast.error('입력값을 확인해주세요.');
      }
    },

    deleteScheduleConfirm(item) {
      this.selectedSchedule = item;
      this.deleteDialog = true;
    },

    async deleteSchedule() {
      if (this.selectedSchedule) {
        this.deleting = true;
        try {
          await deleteSchedule(this.selectedSchedule.id);
          this.$toast.success('스케줄이 삭제되었습니다.');
          await this.initialize();
          this.deleteDialog = false;
          this.selectedSchedule = null;
        } catch (error) {
          console.error('Failed to delete schedule:', error);
          this.$toast.error('스케줄 삭제에 실패했습니다.');
        } finally {
          this.deleting = false;
        }
      }
    },

    closeDialog() {
      this.dialog = false;
      if (this.$refs.form) {
        this.$refs.form.resetValidation();
      }
      this.editedItem = { ...this.defaultItem };
    },

    async handleToggleStatus(schedule) {
      const scheduleIndex = this.schedules.findIndex(s => s.id === schedule.id);
      if (scheduleIndex === -1) return;

      const currentSchedule = this.schedules[scheduleIndex];
      const newStatus = !currentSchedule.isActive;
      
      try {
        await toggleSchedule(schedule.id, newStatus);
        this.$set(this.schedules[scheduleIndex], 'isActive', newStatus);
        this.$toast.success(`스케줄이 ${newStatus ? '활성화' : '비활성화'} 되었습니다.`);
      } catch (error) {
        console.error('Failed to toggle schedule:', error);
        this.$toast.error('스케줄 상태 변경에 실패했습니다.');
        this.$set(this.schedules[scheduleIndex], 'isActive', !newStatus);
      }
    },

    // UI 이벤트 핸들러
    formatDateTime(time) {
      if (!time) return '';
      const now = new Date();
      const [hours, minutes] = time.split(':');
      const date = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hours, minutes);
      return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    },

    formatDays(days) {
      if (!Array.isArray(days)) return '';
      const dayNames = ['일', '월', '화', '수', '목', '금', '토'];
      return days.map(day => dayNames[day]).join(', ');
    },

    onCameraChange(cameraName) {
      // 선택된 카메라의 source 찾기
      const selectedCamera = this.cameras.find(camera => camera.name === cameraName);
      if (selectedCamera) {
        this.editedItem.source = selectedCamera.source;
        this.editedItem.fk_camera_id = selectedCamera.id;
        console.log('Camera source updated:', selectedCamera.source);
      }
    },
  },

  computed: {
    formattedSchedules() {
      return this.schedules.map(schedule => {
        const days = this.formatDays(schedule.days);
        return {
          ...schedule,
          formattedDays: days,
          formattedStartTime: this.formatDateTime(schedule.startTime),
          formattedEndTime: this.formatDateTime(schedule.endTime)
        };
      });
    }
  },
};
</script>

<style scoped>
.recordings-manager {
  padding: 20px;
}

.v-data-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.v-card {
  margin-bottom: 20px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
}

.add-schedule-btn {
  height: 36px !important;
  min-width: 90px !important;
  border: 2px solid var(--cui-border-color) !important;
  text-transform: none !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  letter-spacing: normal !important;
  border-radius: 8px !important;
  color: var(--cui-text-default) !important;
  background: var(--cui-bg-card) !important;
  transition: all 0.2s ease !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
}

.add-schedule-btn:hover {
  background: var(--cui-bg-card-hover) !important;
  border-color: var(--cui-border-color-hover) !important;
  color: var(--cui-text-default) !important;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15) !important;
}

.add-schedule-btn:hover .v-icon {
  color: var(--cui-text-default) !important;
}

.add-schedule-btn:active {
  background: var(--cui-bg-card-hover) !important;
  transform: translateY(1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
}

.add-schedule-btn .v-icon {
  margin-right: 4px !important;
  color: var(--cui-text-default) !important;
}

.edit-btn {
  height: 36px !important;
  min-width: 90px !important;
  border: 2px solid var(--cui-border-color) !important;
  text-transform: none !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  letter-spacing: normal !important;
  border-radius: 8px !important;
  color: var(--cui-text-default) !important;
  background: var(--cui-bg-card) !important;
  transition: all 0.2s ease !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
}

.edit-btn:hover {
  background: var(--cui-bg-card-hover) !important;
  border-color: var(--cui-border-color-hover) !important;
  color: var(--cui-text-default) !important;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15) !important;
}

.edit-btn:hover .v-icon {
  color: var(--cui-text-default) !important;
}

.edit-btn:active {
  background: var(--cui-bg-card-hover) !important;
  transform: translateY(1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
}

.edit-btn .v-icon {
  margin-right: 4px !important;
  color: var(--cui-text-default) !important;
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
  border-color: var(--cui-danger-hover) !important;
  color: white !important;
  box-shadow: 0 4px 6px rgba(239, 68, 68, 0.2) !important;
}

.delete-btn:hover .v-icon {
  color: white !important;
}

.delete-btn:active {
  background: var(--cui-danger-hover) !important;
  transform: translateY(1px);
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.1) !important;
}

.delete-btn .v-icon {
  margin-right: 4px !important;
  color: var(--cui-danger) !important;
}

.v-dialog .v-card,
.v-dialog .v-card-text {
  background: #232323 !important;
  color: #e0e0e0 !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 32px rgba(0,0,0,0.45) !important;
}
.dialog-form-halfwidth {
  width: 50% !important;
  min-width: 320px;
  margin: 0 auto;
}
.dialog-field {
  background: #232323 !important;
  color: #e0e0e0 !important;
  border-radius: 8px !important;
  margin-bottom: 18px !important;
  border: none !important;
  box-shadow: none !important;
}
.dialog-field .v-label {
  font-weight: 500 !important;
  color: #bfc4d1 !important;
  opacity: 0.95;
  padding-left: 8px !important;
  margin-bottom: 6px !important;
}
.dialog-field .v-input__slot,
.dialog-field input,
.dialog-field .v-select__selection {
  color: #e0e0e0 !important;
  background: #232323 !important;
  padding-left: 14px !important;
  padding-right: 14px !important;
}
.v-select__selections .v-chip {
  background: #444 !important;
  color: #e0e0e0 !important;
  font-weight: 500;
}
.v-select__selections .v-chip .v-chip__content {
  color: #e0e0e0 !important;
}
.v-select__selections .v-chip .v-icon {
  color: #e0e0e0 !important;
}
.v-input--is-focused .dialog-field .v-input__slot {
  border: 1.5px solid #6c63ff !important;
}
.cancel-btn {
  background: #232323 !important;
  color: #bfc4d1 !important;
  border-radius: 8px !important;
  font-weight: 500 !important;
  border: 1px solid #444 !important;
  margin-right: 12px !important;
  box-shadow: none !important;
}
.cancel-btn:hover {
  background: #444 !important;
  color: #fff !important;
  border: 1.5px solid #fff !important;
}
.save-btn {
  background: #232323 !important;
  color: #e0e0e0 !important;
  border-radius: 8px !important;
  font-weight: 500 !important;
  border: 1px solid #6c63ff !important;
  box-shadow: none !important;
}
.save-btn:hover {
  background: #444 !important;
  color: #ffd700 !important;
  border: 1.5px solid #ffd700 !important;
}
.v-card-title {
  color: #e0e0e0 !important;
  font-size: 1.3rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  background: transparent !important;
  border-bottom: 1px solid #333 !important;
  padding: 24px 32px 32px 32px !important;
}
.v-card-text {
  padding: 0 32px 12px 32px !important;
}
.v-card-actions {
  padding: 16px 32px 24px 32px !important;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  text-align: center;
}
.cancel-btn, .save-btn {
  min-width: 120px !important;
  max-width: 240px;
  width: auto !important;
}

.v-dialog.delete-dialog .v-card,
.v-dialog.delete-dialog .v-card-title {
  background: #181818 !important;
}
.v-dialog.delete-dialog .v-card-text .tw-bg-gray-50 {
  background: #232323 !important;
  background-color: #232323 !important;
  color: #fff !important;
}
.v-dialog.delete-dialog .v-card-text .tw-bg-gray-50 span,
.v-dialog.delete-dialog .v-card-text .tw-bg-gray-50 {
  color: #fff !important;
}

.actions-wrapper {
  width: 100%;
  text-align: center;
}
.actions-wrapper > * {
  margin: 0 8px;
  display: inline-block;
}
</style>
