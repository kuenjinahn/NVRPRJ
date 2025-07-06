<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.event-setting
  v-container.setting-container(fluid)
    // 로딩 표시
    v-overlay(:value="isLoading")
      v-progress-circular(indeterminate size="64" color="primary")
    
    v-row(no-gutters v-if="settings")
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
            v-btn(color="secondary" @click="saveSettings" :loading="isLoading" :disabled="isLoading") 저장
          v-card-text.content-body
            
            // 기본 경보 설정
            div(v-if="currentMenu === 'alert'")
              v-row
                v-col(cols="12")
                  .tw-flex.tw-justify-between.tw-items-center
                    label.form-input-label 경보 사용 유무
                    v-switch(
                      v-model="settings.alert.enabled"
                      color="var(--cui-primary)"
                    )
                
                v-col(cols="12" md="6")
                  label.form-input-label 알림 방식
                  v-select(
                    v-model="settings.alert.notificationType"
                    :items="notificationTypes"
                    prepend-inner-icon="mdi-bell-ring"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted {{ icons['mdiBellRing'] }}

                v-col(cols="12" md="6")
                  label.form-input-label 알림 지연 시간
                  v-text-field(
                    v-model="settings.alert.delay"
                    type="number"
                    suffix="초"
                    prepend-inner-icon="mdi-timer-sand"
                    background-color="var(--cui-bg-card)"
                    color="var(--cui-text-default)"
                    solo
                  )
                    template(v-slot:prepend-inner)
                      v-icon.text-muted {{ icons['mdiTimerSand'] }}
                
               

            // 경보 단계 설정
            div(v-if="currentMenu === 'alarm-levels'")
              v-card.mb-4
                v-card-title 경보 단계별 기준값 설정
                v-card-text
                  // 누수판단 시나리오 선택
                  label.form-input-label 누수판단 시나리오 선택
                  v-radio-group(
                    v-model="settings.alert.scenario"
                    row
                  )
                    v-radio(
                      label="시나리오 1"
                      value="scenario1"
                    )
                    v-radio(
                      label="시나리오 2"
                      value="scenario2"
                    )
                    v-radio(
                      label="시나리오 3"
                      value="scenario3"
                    )
                  v-alert(
                    type="info"
                    outlined
                    class="mt-2"
                    v-if="settings.alert.scenario"
                  ) {{ scenarioDescriptions[settings.alert.scenario] }}

                  // 기준값 표
                  v-simple-table
                    thead
                      tr
                        th 시나리오 종류
                        th 1단계 기준(주의)
                        th 2단계 기준(경고)
                        th 3단계 기준(위험)
                        th 4단계 기준(심각)
                    tbody
                      tr.alarm-level-table-row
                        td 시나리오1 : 온도차이(℃) 기준
                        td(v-for="(val, idx) in settings.alarmLevels.scenario1" :key="'s1-'+idx")
                          v-text-field(
                            v-model.number="settings.alarmLevels.scenario1[idx]"
                            type="number"
                            suffix="℃"
                            dense
                            filled
                            outlined
                            color="primary"
                            :label="(idx+1)+'단계'"
                            hide-details
                            class="alarm-level-input"
                            style="max-width:120px; margin:0 4px;"
                          )
                      tr.alarm-level-table-row
                        td 시나리오2 : 온도변화량(%) 기준
                        td(v-for="(val, idx) in settings.alarmLevels.scenario2" :key="'s2-'+idx")
                          v-text-field(
                            v-model.number="settings.alarmLevels.scenario2[idx]"
                            type="number"
                            suffix="%"
                            dense
                            filled
                            outlined
                            color="primary"
                            :label="(idx+1)+'단계'"
                            hide-details
                            class="alarm-level-input"
                            style="max-width:120px; margin:0 4px;"
                          )
                      tr.alarm-level-table-row
                        td 시나리오3 : 온도차이2(℃) 기준
                        td(v-for="(val, idx) in settings.alarmLevels.scenario3" :key="'s3-'+idx")
                          v-text-field(
                            v-model.number="settings.alarmLevels.scenario3[idx]"
                            type="number"
                            suffix="℃"
                            dense
                            filled
                            outlined
                            color="primary"
                            :label="(idx+1)+'단계'"
                            hide-details
                            class="alarm-level-input"
                            style="max-width:120px; margin:0 4px;"
                          )

            // 알림 발송 설정
            div(v-if="currentMenu === 'notification'")
              v-row
                v-col(cols="12" md="6")
                  v-card(outlined)
                    v-card-title 이메일 알림 설정
                    v-card-text
                      .tw-flex.tw-justify-between.tw-items-center
                        label.form-input-label 이메일 알림 사용
                        v-switch(
                          v-model="settings.notification.emailEnabled"
                          color="var(--cui-primary)"
                        )
                      
                      v-text-field(
                        v-model="settings.notification.emailAddress"
                        label="알림 수신 이메일"
                        :disabled="!settings.notification.emailEnabled"
                        prepend-inner-icon="mdi-email"
                        background-color="var(--cui-bg-card)"
                        color="var(--cui-text-default)"
                        placeholder="example@domain.com"
                        solo
                      )
                        template(v-slot:prepend-inner)
                          v-icon.text-muted {{ icons['mdiEmail'] }}
                      
                      v-select(
                        v-model="settings.notification.emailAlarmLevel"
                        :items="alarmLevelOptions"
                        label="이메일 알림 발송 단계"
                        :disabled="!settings.notification.emailEnabled"
                        prepend-inner-icon="mdi-alert"
                        background-color="var(--cui-bg-card)"
                        color="var(--cui-text-default)"
                        solo
                      )
                        template(v-slot:prepend-inner)
                          v-icon.text-muted {{ icons['mdiAlert'] }}

                v-col(cols="12" md="6")
                  v-card(outlined)
                    v-card-title 문자 알림 설정
                    v-card-text
                      .tw-flex.tw-justify-between.tw-items-center
                        label.form-input-label 문자 알림 사용
                        v-switch(
                          v-model="settings.notification.smsEnabled"
                          color="var(--cui-primary)"
                        )
                      
                      v-text-field(
                        v-model="settings.notification.phoneNumber"
                        label="알림 수신 전화번호"
                        :disabled="!settings.notification.smsEnabled"
                        prepend-inner-icon="mdi-phone"
                        background-color="var(--cui-bg-card)"
                        color="var(--cui-text-default)"
                        placeholder="010-1234-5678"
                        solo
                      )
                        template(v-slot:prepend-inner)
                          v-icon.text-muted {{ icons['mdiPhone'] }}
                      
                      v-select(
                        v-model="settings.notification.smsAlarmLevel"
                        :items="alarmLevelOptions"
                        label="문자 알림 발송 단계"
                        :disabled="!settings.notification.smsEnabled"
                        prepend-inner-icon="mdi-alert"
                        background-color="var(--cui-bg-card)"
                        color="var(--cui-text-default)"
                        solo
                      )
                        template(v-slot:prepend-inner)
                          v-icon.text-muted {{ icons['mdiAlert'] }}
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
  mdiEmail,
  mdiPhone,
  mdiAlert
} from '@mdi/js'
import { getAlertSettings, getDefaultAlertSettings, saveAlertSettings } from '@/api/alerts.api'

export default {
  name: 'AlertSetting',

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
      mdiEmail,
      mdiPhone,
      mdiAlert
    },
    currentMenu: 'alarm-levels',
    menus: [
      // {
      //   id: 'alert',
      //   title: '기본 경보 설정',
      //   subtitle: '경보 기본 설정',
      //   icon: mdiBell
      // },
      {
        id: 'alarm-levels',
        title: '경보 단계 설정',
        subtitle: '단계별 온도 기준 설정',
        icon: mdiThermometer
      },
      // {
      //   id: 'notification',
      //   title: '알림 발송 설정',
      //   subtitle: '이메일/문자 알림 설정',
      //   icon: mdiBellRing
      // },
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
    settings: null,
    isLoading: false,
    // 드롭다운 옵션들
    notificationTypes: ['팝업', '이메일', 'SMS', '전체'],
    alarmLevelOptions: [
      { text: '주의 (5%)', value: 'L001', threshold: 5 },
      { text: '경고 (10%)', value: 'L002', threshold: 10 },
      { text: '위험 (15%)', value: 'L003', threshold: 15 },
      { text: '심각 (20%)', value: 'L004', threshold: 20 },
      { text: '비상 (25%)', value: 'L005', threshold: 25 }
    ],
    scenarioDescriptions: {
      scenario1: '최대-최소 온도차 10℃ 이상 & 2m 이상 구간 즉시 누수판단',
      scenario2: '온도차 변화 25% 이상 & 1m 이상 구간 즉시 누수판단',
      scenario3: 'Pixel별 1시간 평균온도 C2M distance 5℃ 이상(95% 신뢰구간) 시 누수판단'
    },
  }),

  computed: {
    getCurrentMenuTitle() {
      const menu = this.menus.find(m => m.id === this.currentMenu)
      return menu ? menu.title : ''
    }
  },

  created() {
    this.loadSettings()
  },

  methods: {
    async loadSettings() {
      try {
        this.isLoading = true
        console.log('---------- loadSettings 시작 ----------')

        // 서버에서 설정 불러오기
        console.log('API 호출: getAlertSettings')
        const response = await getAlertSettings()
        console.log('API 응답:', response)
        
        if (response && response.result) {
         
          const data = response.result
          
          // DB에 저장된 alert_setting_json 파싱
          if (data.alert_setting_json) {
            console.log('alert_setting_json 값 확인:', data.alert_setting_json)
            
            try {
              const parsedSettings = JSON.parse(data.alert_setting_json)
              console.log('JSON 파싱 결과:', parsedSettings)
              
              this.settings = await this.mergeSettings(parsedSettings)
              console.log('최종 병합된 설정:', this.settings)
            } catch (e) {
              console.error('JSON 파싱 오류:', e)
              await this.setDefaultSettings()
            }
          } else {
            console.log('alert_setting_json 필드가 없거나 빈 값입니다. 기본 설정을 사용합니다.')
            await this.setDefaultSettings()
          }
        } else {
          console.log('API 응답이 유효하지 않습니다. 기본 설정을 사용합니다.')
          await this.setDefaultSettings()
        }
        
        console.log('최종 설정 값:', this.settings)
        console.log('---------- loadSettings 종료 ----------')
      } catch (error) {
        console.error('설정 불러오기 오류:', error)
        await this.setDefaultSettings()
      } finally {
        this.isLoading = false
      }
    },

    // 기본 설정값 사용
    async setDefaultSettings() {
      try {
        this.settings = await getDefaultAlertSettings()
        if (!this.settings.alert) this.settings.alert = {}
        if (!this.settings.alert.scenario) this.settings.alert.scenario = 'scenario1'
        // alarmLevels 기본값 구조 변경
        if (!this.settings.alarmLevels || typeof this.settings.alarmLevels !== 'object') {
          this.settings.alarmLevels = {
            scenario1: [3, 5, 8, 10],
            scenario2: [10, 15, 20, 25],
            scenario3: [2, 3, 4, 5]
          }
        }
        // scenario1 보정
        const defaultAlarmLevels = {
          scenario1: [3, 5, 8, 10],
          scenario2: [10, 15, 20, 25],
          scenario3: [2, 3, 4, 5]
        }
        if (!Array.isArray(this.settings.alarmLevels.scenario1) || this.settings.alarmLevels.scenario1.length !== 4) {
          this.settings.alarmLevels = { ...defaultAlarmLevels, ...this.settings.alarmLevels }
        }
      } catch (error) {
        console.error('기본 설정 불러오기 오류:', error)
        this.settings = {
          alert: {
            enabled: true,
            notificationType: '팝업',
            delay: 5,
            priority: '높음',
            repeatInterval: 15,
            useSound: true,
            leakThreshold: 5,
            scenario: 'scenario1'
          },
          alarmLevels: {
            scenario1: [3, 5, 8, 10],
            scenario2: [10, 15, 20, 25],
            scenario3: [2, 3, 4, 5]
          },
          notification: {
            emailEnabled: false,
            emailAddress: '',
            emailAlarmLevel: 3,
            smsEnabled: false,
            phoneNumber: '',
            smsAlarmLevel: 4
          }
        }
      }
    },

    // DB에서 로드한 설정과 기본 설정을 병합
    async mergeSettings(loadedSettings) {
      const defaultSettings = await getDefaultAlertSettings()
      const merged = { ...defaultSettings }
      if (loadedSettings.alert) {
        merged.alert = { ...defaultSettings.alert, ...loadedSettings.alert }
      }
      // alarmLevels 구조 병합
      if (loadedSettings.alarmLevels && typeof loadedSettings.alarmLevels === 'object') {
        merged.alarmLevels = {
          scenario1: Array.isArray(loadedSettings.alarmLevels.scenario1) ? loadedSettings.alarmLevels.scenario1.slice(0,4) : defaultSettings.alarmLevels.scenario1,
          scenario2: Array.isArray(loadedSettings.alarmLevels.scenario2) ? loadedSettings.alarmLevels.scenario2.slice(0,4) : defaultSettings.alarmLevels.scenario2,
          scenario3: Array.isArray(loadedSettings.alarmLevels.scenario3) ? loadedSettings.alarmLevels.scenario3.slice(0,4) : defaultSettings.alarmLevels.scenario3
        }
        // scenario1 보정
        const defaultAlarmLevels = {
          scenario1: [3, 5, 8, 10],
          scenario2: [10, 15, 20, 25],
          scenario3: [2, 3, 4, 5]
        }
        if (!Array.isArray(merged.alarmLevels.scenario1) || merged.alarmLevels.scenario1.length !== 4) {
          merged.alarmLevels = { ...defaultAlarmLevels, ...merged.alarmLevels }
        }
      }
      if (loadedSettings.notification) {
        merged.notification = { ...defaultSettings.notification, ...loadedSettings.notification }
      }
      return merged
    },

    async saveSettings() {
      try {
        this.isLoading = true
        
        // 현재 설정을 JSON으로 변환
        const settingsJSON = JSON.stringify(this.settings)
        
        // 서버에 저장 요청
        await saveAlertSettings({
          alert_setting_json: settingsJSON,
          fk_user_id: this.$store.state.auth.user?.id || 1 // 현재 로그인한 사용자 ID 또는 기본값
        })
        this.$toast.success('설정이 성공적으로 저장되었습니다.')
      } catch (error) {
        console.error('설정 저장 오류:', error)
        this.$toast.error('설정 저장 중 오류가 발생했습니다.')
      } finally {
        this.isLoading = false
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

.scenario-desc {
  display: block;
  margin-left: 32px;
  color: #aaa;
  font-size: 0.95em;
  margin-bottom: 8px;
}

.alarm-level-input {
  background: #232323 !important;
  color: #fff !important;
  border-radius: 6px !important;
  .v-input__slot, .v-input__control {
    background: transparent !important;
    color: #fff !important;
    border: 1.5px solid #4fc3f7 !important;
    border-radius: 6px !important;
  }
  input {
    color: #fff !important;
    font-weight: 500;
    letter-spacing: 0.5px;
  }
  .v-label {
    color: #b0bec5 !important;
  }
  .v-input__append-inner .v-icon {
    color: #b0bec5 !important;
  }
  &:hover, &.v-input--is-focused {
    .v-input__slot, .v-input__control {
      border-color: #1976d2 !important;
    }
  }
}

.alarm-level-table-row {
  height: 64px;
  min-height: 64px;
}
</style>
