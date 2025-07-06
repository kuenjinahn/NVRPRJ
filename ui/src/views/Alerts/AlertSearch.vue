<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.alert-search
  v-card
    .search-bar.tw-p-4
      .tw-flex.tw-items-center.tw-gap-4
        .search-field-container.tw-flex-1
          v-text-field(
            v-model="search"
            prepend-inner-icon="mdi-magnify"
            placeholder="검색어를 입력하세요"
            hide-details
            dense
            class="search-field"
            @input="handleSearch"
            filled
            background-color="var(--cui-bg-card)"
          )
        .tw-flex.tw-items-center.tw-gap-2
          v-select(
            v-model="statusFilter"
            :items="statusOptions"
            label="상태"
            dense
            filled
            hide-details
            class="filter-select"
            @change="handleFilter"
            background-color="var(--cui-bg-card)"
          )
          v-select(
            v-model="levelFilter"
            :items="levelOptions"
            label="위험도"
            dense
            filled
            hide-details
            class="filter-select"
            @change="handleFilter"
            background-color="var(--cui-bg-card)"
          )
          v-menu(
            ref="dateMenu"
            v-model="dateMenu"
            :close-on-content-click="false"
            transition="scale-transition"
            offset-y
            min-width="auto"
          )
            template(v-slot:activator="{ on, attrs }")
              v-text-field(
                v-model="dateRangeText"
                label="기간"
                prepend-inner-icon="mdi-calendar"
                readonly
                v-bind="attrs"
                v-on="on"
                dense
                filled
                hide-details
                class="filter-select"
                background-color="var(--cui-bg-card)"
              )
            v-date-picker(
              v-model="dates"
              range
              no-title
              scrollable
              @input="handleDateChange"
            )
    
    v-data-table(
      :headers="headers"
      :items="alerts"
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
      template(v-slot:item="{ item }")
        tr(:class="{'alert-level-3': Number(item.alert_level) >= 3, 'alert-level-4': Number(item.alert_level) >= 4, 'alert-level-5': Number(item.alert_level) >= 5}")
          td.text-center {{ item.id }}
          td.text-center {{ item.fk_camera_id }}
          td.text-center {{ item.alert_accur_time }}
          td.text-center {{ getTypeText(item.alert_type) }}
          td.text-center
            v-chip(:color="getLevelColor(item.alert_level)" small label) {{ getLevelText(item.alert_level) }}
          td.text-center
            v-chip(:color="getStatusColor(item.alert_status)" small label) {{ getStatusText(item.alert_status) }}
          td.text-center
            v-chip(:color="getStatusColor(item.fk_detect_zone_id)" small label) {{ item.fk_detect_zone_id + '구역' }}
          td.text-center {{ getAlertDescription(item) }}
          //td.text-center
          //  .tw-flex.tw-gap-2.tw-justify-center
          //    v-btn(
          //      v-if="item.alert_status !== 'P002'"
          //      color="secondary"
          //      small
          //      @click="handleProcess(item)"
          //      ) 처리
          //    v-btn(
          //      color="error"
          //      small
          //      @click="handleDelete(item)"
          //    ) 삭제
</template>

<script>
import { getAlerts, updateAlertStatus, removeAlert } from '@/api/alerts.api'

export default {
  name: 'AlertSearch',

  data: () => ({
    search: '',
    statusFilter: null,
    levelFilter: null,
    dateMenu: false,
    dates: [],
    page: 1,
    pageSize: 10,
    loading: false,
    alerts: [],
    totalItems: 0,
    headers: [
      { text: 'ID', value: 'id', align: 'center', width: '80px' },
      { text: '카메라 ID', value: 'fk_camera_id', align: 'center' },
      { text: '발생 시간', value: 'alert_accur_time', align: 'center' },
      { text: '알림 유형', value: 'alert_type', align: 'center' },
      { text: '위험도', value: 'alert_level', align: 'center' },
      { text: '상태', value: 'alert_status', align: 'center' },
      { text: '감지 구역', value: 'fk_detect_zone_id', align: 'center' },
      { text: '설명', value: 'alert_description', align: 'center' }
      // { text: '작업', value: 'actions', align: 'center', sortable: false, width: '150px' }
    ],
    statusOptions: [
      { text: '전체', value: null },
      { text: '신규', value: 'P001' },
      { text: '처리중', value: 'P002' },
      { text: '완료', value: 'P003' },
      { text: '무시', value: 'P004' }
    ],
    levelOptions: [
      { text: '전체', value: null },
      { text: '낮음', value: 'L001' },
      { text: '보통', value: 'L002' },
      { text: '높음', value: 'L003' },
      { text: '위험', value: 'L004' }
    ]
  }),

  computed: {
    dateRangeText() {
      return this.dates.length === 2
        ? `${this.dates[0]} ~ ${this.dates[1]}`
        : '기간 선택'
    },
    filteredAlerts() {
      return this.alerts.filter(alert => {
        const matchesSearch = !this.search || 
          alert.alert_description?.toLowerCase().includes(this.search.toLowerCase()) ||
          String(alert.fk_camera_id).includes(this.search)
        
        const matchesStatus = !this.statusFilter || alert.alert_status === this.statusFilter
        const matchesLevel = !this.levelFilter || alert.alert_level === this.levelFilter
        
        const matchesDate = this.dates.length !== 2 || (
          new Date(alert.alert_accur_time) >= new Date(this.dates[0]) &&
          new Date(alert.alert_accur_time) <= new Date(this.dates[1])
        )
        
        return matchesSearch && matchesStatus && matchesLevel && matchesDate
      })
    }
  },

  async mounted() {
    await this.loadAlerts()
  },

  watch: {
    page() {
      this.loadAlerts();
    },
    pageSize() {
      this.page = 1;
      this.loadAlerts();
    }
  },

  methods: {
    async loadAlerts() {
      this.loading = true;
      try {
        // Build query string for pagination and filters
        let params = `?page=${this.page}&pageSize=${this.pageSize}`;
        if (this.statusFilter) params += `&status=${this.statusFilter}`;
        if (this.levelFilter) params += `&level=${this.levelFilter}`;
        if (this.search) params += `&search=${encodeURIComponent(this.search)}`;
        if (this.dates.length === 2) params += `&startDate=${this.dates[0]}&endDate=${this.dates[1]}`;
        const response = await getAlerts(params);
        this.alerts = response.data.result.map(alert => ({
          ...alert,
          alert_accur_time: this.formatDate(alert.alert_accur_time),
          alert_process_time: alert.alert_process_time ? this.formatDate(alert.alert_process_time) : '-'
        }));
        this.totalItems = response.data.pagination?.totalItems || 0;
      } catch (error) {
        console.error('알림 조회 실패:', error)
        this.$toast?.error('알림을 불러오는 중 오류가 발생했습니다.')
      } finally {
        this.loading = false
      }
    },

    formatDate(dateString) {
      if (!dateString) return '-'
      
      // UTC 시간을 로컬 시간으로 변환
      const date = new Date(dateString)
      
      // 시간대 오프셋을 고려하여 올바른 시간 계산
      const utcTime = date.getTime() + (date.getTimezoneOffset() * 60000)
      const localDate = new Date(utcTime)
      
      return localDate.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      })
    },

    getLevelText(level) {
      const levels = {
        '1': '주의',
        '2': '경고',
        '3': '위험',
        '4': '심각',
        '5': '비상'
      }
      return levels[level] || level
    },

    getLevelColor(level) {
      const colors = {
        'L001': 'success',
        'L002': 'warning',
        'L003': 'orange',
        'L004': 'error'
      }
      return colors[level] || 'grey'
    },

    getStatusText(status) {
      const statuses = {
        'P001': '신규',
        'P002': '처리중',
        'P003': '완료',
        'P004': '무시'
      }
      return statuses[status] || status
    },

    getStatusColor(status) {
      const colors = {
        'P001': 'info',
        'P002': 'warning',
        'P003': 'success',
        'P004': 'grey'
      }
      return colors[status] || 'grey'
    },

    getTypeText(type) {
      const types = {
        'A001': '누수 감지',
        'A002': '움직임 감지',
        'A003': '얼굴 인식',
        'A004': '차량 감지'
      }
      return types[type] || type
    },

    getAlertDescription(item) {
      try {
        if (!item.alert_info_json) {
          return item.alert_description || '-'
        }
        const alertInfo = JSON.parse(item.alert_info_json)
        return alertInfo.temperature_diff_desc || item.alert_description || '-'
      } catch (e) {
        console.error('알림 설명 파싱 오류:', e)
        return item.alert_description || '-'
      }
    },

    async handleProcess(alert) {
      try {
        // 처리 확인 다이얼로그
        const confirmed = await this.$confirm('이 알림을 처리하시겠습니까?')
        if (!confirmed) return

        // 현재 로그인한 사용자 ID 가져오기 (auth store에서)
        const userId = this.$store.getters['auth/user']?.id || 1
        
        await updateAlertStatus(alert.id, 'P002', userId)
        
        this.$toast.success('알림이 처리되었습니다.')
        await this.loadAlerts()
      } catch (error) {
        console.error('알림 처리 실패:', error)
        this.$toast.error('알림 처리 중 오류가 발생했습니다.')
      }
    },

    async handleDelete(alert) {
      try {
        const confirmed = await this.$confirm('이 알림을 삭제하시겠습니까?')
        if (!confirmed) return

        await removeAlert(alert.id)
        
        this.$toast.success('알림이 삭제되었습니다.')
        await this.loadAlerts()
      } catch (error) {
        console.error('알림 삭제 실패:', error)
        this.$toast.error('알림 삭제 중 오류가 발생했습니다.')
      }
    },

    handleSearch() {
      // 필터링은 computed의 filteredAlerts에서 자동 처리
    },

    handleFilter() {
      // 필터링은 computed의 filteredAlerts에서 자동 처리
    },

    handleDateChange() {
      this.dateMenu = false
    }
  }
}
</script>

<style lang="scss" scoped>
.alert-search {
  .v-card {
    background-color: var(--cui-bg-dark);
    border-radius: 8px;
  }

  .search-bar {
    background-color: var(--cui-bg-darker);
    border-bottom: 1px solid var(--cui-border-color);
    border-radius: 8px 8px 0 0;
  }

  .search-field-container {
    max-width: 400px;
  }

  .search-field {
    ::v-deep {
      .v-input__slot {
        background-color: var(--cui-bg-card) !important;
        border-radius: 4px !important;
        min-height: 40px !important;

        &:before,
        &:after {
          display: none;
        }

        .v-input__prepend-inner {
          margin-top: 8px;
          margin-right: 8px;
          
          .v-icon {
            color: var(--cui-text-muted);
            font-size: 20px;
          }
        }

        input {
          color: var(--cui-text);
          font-size: 14px;

          &::placeholder {
            color: var(--cui-text-muted);
          }
        }
      }
    }
  }

  .filter-select {
    min-width: 120px;
    
    ::v-deep {
      .v-input__slot {
        background-color: var(--cui-bg-card) !important;
        border-radius: 4px !important;
        min-height: 40px !important;

        &:before,
        &:after {
          display: none;
        }
      }
      
      .v-select__slot,
      .v-text-field__slot {
        font-size: 14px;
        
        .v-label {
          top: 10px;
          color: var(--cui-text-muted);
          font-size: 14px;
        }
        
        input {
          color: var(--cui-text);
        }
      }
      
      .v-icon {
        color: var(--cui-text-muted);
        font-size: 20px;
      }
    }
  }

  .v-data-table {
    background: transparent;
    
    ::v-deep {
      .v-data-table__wrapper {
        border-radius: 0 0 8px 8px;
      }
      
      th {
        font-weight: bold;
        background-color: var(--cui-bg-darker);
        color: var(--cui-text);
      }
      
      td {
        padding: 8px 16px;
        color: var(--cui-text);
      }

      .v-chip {
        font-weight: 500;
      }

      tr {
        &.alert-level-3 {
          animation: blink-amber 1s infinite;
        }
        &.alert-level-4 {
          animation: blink-orange 1s infinite;
        }
        &.alert-level-5 {
          animation: blink-red 1s infinite;
        }
      }
    }
  }

  .v-btn {
    color: var(--cui-text-default) !important;
    
    &.v-btn--icon {
      background-color: var(--cui-bg-gray-700);
      border-radius: 4px;
      padding: 8px;
    }
  }

  // 아이콘 색상 설정
  .v-icon {
    color: white !important;
    
    .v-icon__svg {
      color: white !important;
      fill: white !important;
    }
  }

  // 페이지네이션 아이콘 특별 처리
  .v-data-table ::v-deep {
    .v-data-footer {
      .v-icon {
        color: white !important;
        
        .v-icon__svg {
          color: white !important;
          fill: white !important;
        }
      }
    }
  }

  // 모든 아이콘에 대한 전역 설정
  ::v-deep .v-icon {
    color: white !important;
    
    .v-icon__svg {
      color: white !important;
      fill: white !important;
    }
  }

  // 비활성화된 버튼의 아이콘은 어두운색으로 유지
  .v-btn--disabled .v-icon {
    color: var(--cui-text-muted) !important;
    
    .v-icon__svg {
      color: var(--cui-text-muted) !important;
      fill: var(--cui-text-muted) !important;
    }
  }

  // 페이지네이션에서 비활성화된 버튼의 아이콘
  .v-data-table ::v-deep {
    .v-data-footer {
      .v-btn--disabled .v-icon {
        color: var(--cui-text-muted) !important;
        
        .v-icon__svg {
          color: var(--cui-text-muted) !important;
          fill: var(--cui-text-muted) !important;
        }
      }
    }
  }

  // 전역적으로 비활성화된 버튼의 아이콘
  ::v-deep .v-btn--disabled .v-icon {
    color: var(--cui-text-muted) !important;
    
    .v-icon__svg {
      color: var(--cui-text-muted) !important;
      fill: var(--cui-text-muted) !important;
    }
  }
}

@keyframes blink-amber {
  0% { background-color: var(--cui-bg-card); }
  50% { background-color: rgba(255, 193, 7, 0.2); }
  100% { background-color: var(--cui-bg-card); }
}

@keyframes blink-orange {
  0% { background-color: var(--cui-bg-card); }
  50% { background-color: rgba(255, 152, 0, 0.2); }
  100% { background-color: var(--cui-bg-card); }
}

@keyframes blink-red {
  0% { background-color: var(--cui-bg-card); }
  50% { background-color: rgba(244, 67, 54, 0.2); }
  100% { background-color: var(--cui-bg-card); }
}
</style> 
