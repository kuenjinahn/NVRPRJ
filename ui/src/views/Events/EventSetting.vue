<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.event-setting
  v-container.setting-container(fluid)
    v-row(no-gutters)
      // 왼쪽 메뉴
      v-col(cols="3")
        v-navigation-drawer.setting-menu(permanent dark)
          v-list(nav dense)
            v-list-item(
              v-for="(menu, index) in menus"
              :key="index"
              @click="menu.title ? currentMenu = menu.id : null"
              :class="{ 'selected-menu': currentMenu === menu.id }"
            )
              v-list-item-icon
                v-icon {{ menu.icon }}
              v-list-item-content
                v-list-item-title {{ menu.title }}
                v-list-item-subtitle.menu-subtitle {{ menu.subtitle }}

      // 오른쪽 컨텐츠
      v-col(cols="9")
        v-card.content-card
          v-card-title.content-title
            span {{ getCurrentMenuTitle }}
            v-spacer
            v-btn(color="secondary" @click="saveSettings") 저장
          v-card-text.content-body
            // 온도 설정
            div(v-if="currentMenu === 'temperature'")
              v-row
                v-col(cols="12" md="6")
                  label.form-input-label 기준 온도 설정
                  v-text-field(
                    v-model="settings.temperature.threshold"
                    type="number"
                    suffix="°C"
                    prepend-inner-icon="mdi-thermometer"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted {{ icons['mdiThermometer'] }}

                v-col(cols="12" md="6")
                  label.form-input-label 알림 유형
                  v-select(
                    v-model="settings.temperature.alertType"
                    :items="alertTypes"
                    prepend-inner-icon="mdi-bell"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted {{ icons['mdiBell'] }}

                v-col(cols="12" md="6")
                  label.form-input-label 측정 간격
                  v-text-field(
                    v-model="settings.temperature.interval"
                    type="number"
                    suffix="초"
                    prepend-inner-icon="mdi-timer"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted {{ icons['mdiTimer'] }}

                v-col(cols="12" md="6")
                  label.form-input-label 감지 민감도
                  v-select(
                    v-model="settings.temperature.sensitivity"
                    :items="sensitivityLevels"
                    prepend-inner-icon="mdi-tune"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted {{ icons['mdiTune'] }}

                v-col(cols="12" md="6")
                  .tw-flex.tw-justify-between.tw-items-center
                    label.form-input-label 자동 알림
                    v-switch(
                      v-model="settings.temperature.autoAlert"
                      color="var(--cui-primary)"
                    )

            // 객체 설정
            div(v-if="currentMenu === 'object'")
              v-row
                v-col(cols="12" md="6")
                  label.form-input-label 감지 대상
                  v-select(
                    v-model="settings.object.detectionType"
                    :items="detectionTypes"
                    prepend-inner-icon="mdi-account-group"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted {{ icons['mdiAccountGroup'] }}

                v-col(cols="12" md="6")
                  label.form-input-label 감지 정확도
                  v-select(
                    v-model="settings.object.accuracy"
                    :items="accuracyLevels"
                    prepend-inner-icon="mdi-target"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted {{ icons['mdiTarget'] }}

                v-col(cols="12" md="6")
                  .tw-flex.tw-justify-between.tw-items-center
                    label.form-input-label 객체 추적 사용
                    v-switch(
                      v-model="settings.object.enableTracking"
                      color="var(--cui-primary)"
                    )

            // 현장정보 입력
            div(v-if="currentMenu === 'system'")
              v-row
                v-col(cols="12" md="6")
                  label.form-input-label 현장명
                  v-text-field(
                    v-model="settings.system.location_info"
                    placeholder="예: 수자원공사 광동댐"
                    prepend-inner-icon="mdi-domain"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted mdi-domain
                v-col(cols="12" md="6")
                  label.form-input-label 현장위치
                  v-text-field(
                    v-model="settings.system.address"
                    placeholder="예: 강원특별자치도 강릉시 연곡면 삼산리 산1-1"
                    prepend-inner-icon="mdi-map-marker"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted mdi-map-marker
                              
                v-col(cols="12" md="6")
                  label.form-input-label 지도 이미지 추가
                  v-file-input(
                    v-model="mapImageFile"
                    accept="image/*"
                    prepend-inner-icon="mdi-map"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                    hide-details
                    @change="handleMapImageChange"
                    placeholder="지도 이미지를 선택하세요"
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted mdi-map
                
                v-col(cols="12" v-if="mapImagePreview")
                  .map-preview-container
                    label.form-input-label 선택된 지도 이미지 미리보기
                    v-img(
                      :src="mapImagePreview"
                      max-height="200"
                      contain
                      class="map-preview-image"
                    )
                    v-btn(
                      color="error"
                      small
                      @click="removeMapImage"
                      class="mt-2"
                    ) 이미지 제거
</template>

<script>
import { 
  mdiThermometer, 
  mdiBell,
  mdiBellRing,
  mdiAccountGroup,
  mdiCog,
  mdiTimer,
  mdiTimerSand,
  mdiTune,
  mdiPriorityHigh,
  mdiRepeat,
  mdiResize,
  mdiTarget,
  mdiDatabase,
  mdiCalendar,
  mdiBackupRestore,
  mdiHarddisk,
  mdiDomain,
  mdiMapMarker,
  mdiPhone,
  mdiAccount,
  mdiVideo,
  mdiDeleteClock
} from '@mdi/js'
import { getEventSetting, updateEventSetting, createEventSetting } from '@/api/eventSetting.api.js'

export default {
  name: 'EventSetting',

  data: () => ({
    icons: {
      mdiThermometer,
      mdiBell,
      mdiBellRing,
      mdiAccountGroup,
      mdiCog,
      mdiTimer,
      mdiTimerSand,
      mdiTune,
      mdiPriorityHigh,
      mdiRepeat,
      mdiResize,
      mdiTarget,
      mdiDatabase,
      mdiCalendar,
      mdiBackupRestore,
      mdiHarddisk,
      mdiDomain,
      mdiMapMarker,
      mdiPhone,
      mdiAccount,
      mdiVideo,
      mdiDeleteClock
    },
    currentMenu: 'system',
    mapImageFile: null,
    mapImagePreview: null,
    menus: [
      // {
      //   id: 'temperature',
      //   title: '온도 설정',
      //   subtitle: '온도 감지 및 알림 설정',
      //   icon: mdiThermometer
      // },
      {
        id: 'system',
        title: '시스템',
        subtitle: '시스템 설정',
        icon: mdiCog
      },
      {
        id: 'empty1',
        title: '',
        subtitle: '',
        icon: ''
      },
      {
        id: 'empty2',
        title: '',
        subtitle: '',
        icon: ''
      },
      {
        id: 'empty3',
        title: '',
        subtitle: '',
        icon: ''
      },
      {
        id: 'empty4',
        title: '',
        subtitle: '',
        icon: ''
      },
      {
        id: 'empty5',
        title: '',
        subtitle: '',
        icon: ''
      }
    ],
    settings: {
      temperature: {
        threshold: 20,
        alertType: '알림',
        interval: 30,
        sensitivity: '중간',
        autoAlert: true
      },
      alert: {
        notificationType: '팝업',
        delay: 5,
        priority: '높음',
        repeatInterval: 15,
        useSound: true
      },
      object: {
        detectionType: '전체',
        minSize: 100,
        accuracy: '높음',
        trackingDuration: 10,
        enableTracking: true
      },
              system: {
          location_info: '',
          address: '',
          recodingBitrate: '1024k',
          recodingFileDeleteDays: 30,
          map: null
        },
      site: {
        name: '',
        location: '',
        manager: '',
        contact: ''
      }
    },
    // 드롭다운 옵션들
    alertTypes: ['알림', '경고', '긴급'],
    sensitivityLevels: ['낮음', '중간', '높음'],
    notificationTypes: ['팝업', '이메일', 'SMS', '전체'],
    priorityLevels: ['낮음', '중간', '높음', '긴급'],
    detectionTypes: ['사람', '차량', '동물', '전체'],
    accuracyLevels: ['낮음', '중간', '높음'],
    storageTypes: ['local', 'cloud', 'hybrid'],
    backupSchedules: ['사용안함', '매일', '매주', '매월']

  }),

  computed: {
    getCurrentMenuTitle() {
      const menu = this.menus.find(m => m.id === this.currentMenu)
      return menu ? menu.title : ''
    }
  },

  async mounted() {
    try {
      const data = await getEventSetting()
      const temp = data.temperature_json ? JSON.parse(data.temperature_json) : {};
      const alert = data.alert_json ? JSON.parse(data.alert_json) : {};
      const object = data.object_json ? JSON.parse(data.object_json) : {};
      const system = data.system_json ? JSON.parse(data.system_json) : {};

      // 저장된 지도 이미지가 있으면 미리보기 설정
      if (system.map) {
        this.mapImagePreview = system.map;
      }

      this.settings = {
        temperature: {
          threshold: temp.threshold ?? 20,
          alertType: temp.alertType ?? '알림',
          interval: temp.interval ?? 30,
          sensitivity: temp.sensitivity ?? '중간',
          autoAlert: temp.autoAlert ?? true
        },
        alert: {
          notificationType: alert.notificationType ?? '팝업',
          delay: alert.delay ?? 5,
          priority: alert.priority ?? '높음',
          repeatInterval: alert.repeatInterval ?? 15,
          useSound: alert.useSound ?? true
        },
        object: {
          detectionType: object.detectionType ?? '전체',
          minSize: object.minSize ?? 100,
          accuracy: object.accuracy ?? '높음',
          trackingDuration: object.trackingDuration ?? 10,
          enableTracking: object.enableTracking ?? true
        },
        system: {
          location_info: system.location_info ?? '',
          address: system.address ?? '',
          recodingBitrate: system.recodingBitrate ?? '1024k',
          recodingFileDeleteDays: system.recodingFileDeleteDays ?? 30,
          map: system.map ?? null
        },
        site: {
          name: '',
          location: '',
          manager: '',
          contact: ''
        }
      }
    } catch (e) {
      // 데이터가 없으면(404 등) 초기화
      this.settings = {
        temperature: {
          threshold: 20,
          alertType: '알림',
          interval: 30,
          sensitivity: '중간',
          autoAlert: true
        },
        alert: {
          notificationType: '팝업',
          delay: 5,
          priority: '높음',
          repeatInterval: 15,
          useSound: true
        },
        object: {
          detectionType: '전체',
          minSize: 100,
          accuracy: '높음',
          trackingDuration: 10,
          enableTracking: true
        },
        system: {
          location_info: '',
          address: '',
          recodingBitrate: '1024k',
          recodingFileDeleteDays: 30,
          map: null
        },
        site: {
          name: '',
          location: '',
          manager: '',
          contact: ''
        }
      }
    }
  },

  methods: {
    handleMapImageChange(file) {
      if (file) {
        // 파일 크기 체크 (16MB 제한)
        const maxSize = 16 * 1024 * 1024; // 16MB
        if (file.size > maxSize) {
          this.$toast && this.$toast.error('파일 크기가 16MB를 초과합니다. 더 작은 이미지를 선택해주세요.');
          this.mapImageFile = null;
          return;
        }

        // 이미지 파일 타입 체크
        if (!file.type.startsWith('image/')) {
          this.$toast && this.$toast.error('이미지 파일만 선택할 수 있습니다.');
          this.mapImageFile = null;
          return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
          // Base64 인코딩된 이미지 데이터
          const base64Data = e.target.result;
          this.mapImagePreview = base64Data;
          this.settings.system.map = base64Data;
          
          console.log('이미지 Base64 인코딩 완료:', {
            fileName: file.name,
            fileSize: file.size,
            fileType: file.type,
            base64Length: base64Data.length
          });
        };
        
        reader.onerror = () => {
          this.$toast && this.$toast.error('이미지 파일 읽기에 실패했습니다.');
          this.mapImageFile = null;
        };
        
        // Base64로 인코딩
        reader.readAsDataURL(file);
      }
    },

    removeMapImage() {
      this.mapImageFile = null;
      this.mapImagePreview = null;
      this.settings.system.map = null;
    },

    async saveSettings() {
      try {
        // 1. 현재 DB에 설정이 있는지 확인
        const data = await getEventSetting();
        const id = data && data.id;

        // 2. 각 메뉴별 JSON 항목을 문자열로 변환
        const payload = {
          temperature_json: JSON.stringify(this.settings.temperature),
          alert_json: JSON.stringify(this.settings.alert),
          object_json: JSON.stringify(this.settings.object),
          system_json: JSON.stringify(this.settings.system)
        };

        // 3. 있으면 update, 없으면 create
        if (id) {
          await updateEventSetting(id, payload);
          this.$toast && this.$toast.success('설정이 수정되었습니다.');
        } else {
          await createEventSetting(payload);
          this.$toast && this.$toast.success('설정이 저장되었습니다.');
        }
      } catch (e) {
        this.$toast && this.$toast.error('설정 저장에 실패했습니다.');
      }
    }
  }
}
</script>

<style lang="scss">
.event-setting {
  height: 100%;
  background-color: var(--cui-bg-default);
  padding-top: 20px;

  .setting-container {
    height: 100%;
    padding: 0;
  }

  .setting-menu {
    background-color: var(--cui-bg-nav);
    border-right: 1px solid var(--cui-border-color);
    height: 100%;
    width: 100% !important;
    padding: 5px 0;

    .v-list {
      padding: 0;
      height: 100%;
      background-color: var(--cui-bg-nav);
      overflow-y: hidden !important;
    }

    :deep(.v-navigation-drawer__content) {
      height: 100% !important;
      background-color: var(--cui-bg-nav);
      overflow-y: hidden !important;
    }

    :deep(.v-navigation-drawer__content::-webkit-scrollbar) {
      display: none;
    }

    :deep(.v-navigation-drawer__content) {
      -ms-overflow-style: none;
      scrollbar-width: none;
    }

    .v-list-item {
      margin: 4px 20px;
      border-radius: 8px;
      transition: all 0.3s ease;
      min-height: 80px;
      padding: 12px 0;

      &:not([title=""]) {
        &:hover {
          background-color: rgba(var(--cui-primary-rgb), 0.1);
        }

        &.selected-menu {
          background-color: rgba(var(--cui-primary-rgb), 0.2);
        }
      }

      .v-list-item__title {
        font-weight: 500;
        color: var(--cui-text-default);
        font-size: 1.1rem;
        line-height: 1.5;
      }

      .menu-subtitle {
        font-size: 0.9rem;
        color: var(--cui-text-muted);
        line-height: 1.4;
      }

      .v-list-item__icon {
        margin-right: 16px;
        .v-icon {
          font-size: 24px;
        }
      }
    }
  }

  .content-card {
    height: calc(100% - 20px);
    margin: 0 16px;
    background-color: var(--cui-bg-card);
    border-radius: 12px;
    border: 1px solid var(--cui-border-color);

    .content-title {
      padding: 20px 24px;
      font-size: 1.25rem;
      font-weight: 500;
      color: var(--cui-text-default);
      border-bottom: 1px solid var(--cui-border-color);
    }

    .content-body {
      padding: 24px;
    }
  }
}

.form-input-label {
  font-weight: 500;
  font-size: 0.875rem;
  line-height: 2;
  color: var(--cui-text-default);
}

.v-text-field, .v-select {
  margin-bottom: 16px;

  .v-input__slot {
    background-color: var(--cui-bg-card) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;

    &:hover {
      border-color: rgba(255, 255, 255, 0.24) !important;
    }

    &.v-input--is-focused {
      border-color: var(--cui-primary) !important;
      border-width: 2px !important;
    }
  }

  .v-label {
    color: rgba(255, 255, 255, 0.7) !important;
  }

  input, .v-select__selection {
    color: rgba(255, 255, 255, 0.87) !important;
  }

  .v-input__append-inner {
    .v-icon {
      color: rgba(255, 255, 255, 0.54) !important;
    }
  }
}

.v-switch {
  margin-top: 8px;
  
  .v-input--selection-controls__input {
    margin-right: 8px;
  }

  .v-label {
    color: rgba(255, 255, 255, 0.87) !important;
  }
}

.v-menu__content {
  background-color: var(--cui-bg-card) !important;
  
  .v-list {
    background-color: var(--cui-bg-card) !important;
    
    .v-list-item {
      color: rgba(255, 255, 255, 0.87) !important;
      
      &:hover {
        background-color: rgba(255, 255, 255, 0.05) !important;
      }
      
      &.v-list-item--active {
        background-color: rgba(var(--cui-primary-rgb), 0.2) !important;
        color: var(--cui-primary) !important;
      }
    }
  }
}

.map-preview-container {
  margin-top: 16px;
  
  .map-preview-image {
    border: 1px solid var(--cui-border-color);
    border-radius: 8px;
    margin-top: 8px;
  }
}

.v-file-input {
  margin-bottom: 16px;
  
  .v-input__slot {
    background-color: var(--cui-bg-card) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;

    &:hover {
      border-color: rgba(255, 255, 255, 0.24) !important;
    }

    &.v-input--is-focused {
      border-color: var(--cui-primary) !important;
      border-width: 2px !important;
    }
  }

  .v-label {
    color: rgba(255, 255, 255, 0.7) !important;
  }

  input {
    color: rgba(255, 255, 255, 0.87) !important;
  }

  .v-input__append-inner {
    .v-icon {
      color: rgba(255, 255, 255, 0.54) !important;
    }
  }
}
</style>
