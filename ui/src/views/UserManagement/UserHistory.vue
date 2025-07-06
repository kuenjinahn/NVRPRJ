<template lang="pug">
.user-history
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
      :items="filteredHistory"
      :items-per-page="10"
      :page.sync="page"
      :server-items-length="totalItems"
      :loading="loading"
      loading-text="데이터를 불러오는 중..."
      no-data-text="데이터가 없습니다"
      class="elevation-1"
    )
      template(v-slot:item.access_type="{ item }")
        v-chip(
          :color="getStatusColor(item.access_type)"
          small
          label
        ) {{ getAccessTypeText(item.access_type) }}
</template>

<script>
import { getUserAccessHistory } from '@/api/users.api'

export default {
  name: 'UserHistory',

  data: () => ({
    search: '',
    statusFilter: null,
    dateMenu: false,
    dates: [],
    page: 1,
    totalItems: 0,
    loading: false,
    headers: [
      { text: 'No', value: 'id', align: 'center', width: '80px' },
      { text: '아이디', value: 'userId', align: 'center' },
      { text: '이름', value: 'userName', align: 'center' },
      { text: '접속 시간', value: 'login_time', align: 'center' },
      { text: 'IP주소', value: 'ip_address', align: 'center' },
      { text: '접속 유형', value: 'access_type', align: 'center' },
      { text: '로그아웃 시간', value: 'logout_time', align: 'center' }
    ],
    statusOptions: [
      { text: '전체', value: null },
      { text: '로그인', value: 1 },
      { text: '로그아웃', value: 2 }
    ],
    history: []
  }),

  computed: {
    dateRangeText() {
      return this.dates.length === 2
        ? `${this.dates[0]} ~ ${this.dates[1]}`
        : '기간 선택'
    },
    filteredHistory() {
      return this.history.filter(record => {
        const matchesSearch = !this.search || 
          record.userId.toLowerCase().includes(this.search.toLowerCase()) ||
          record.userName.toLowerCase().includes(this.search.toLowerCase()) ||
          record.ip_address.toLowerCase().includes(this.search.toLowerCase())
        
        const matchesStatus = !this.statusFilter || record.access_type === this.statusFilter
        
        const matchesDate = this.dates.length !== 2 || (
          new Date(record.login_time) >= new Date(this.dates[0]) &&
          new Date(record.login_time) <= new Date(this.dates[1])
        )
        
        return matchesSearch && matchesStatus && matchesDate
      })
    }
  },

  async mounted() {
    await this.loadAccessHistory()
  },

  methods: {
    async loadAccessHistory() {
      this.loading = true
      try {
        console.log('Loading access history...')
        const response = await getUserAccessHistory('', '')
        console.log('API Response:', response)
        
        // 원본 데이터를 그대로 사용하되, 날짜만 포맷팅
        this.history = response.data.map(item => ({
          ...item,
          login_time: this.formatDate(item.login_time),
          logout_time: item.logout_time ? this.formatDate(item.logout_time) : '-',
          access_type_text: this.getAccessTypeText(item.access_type),
          // 원본 access_type 값도 유지 (필터링용)
          access_type: item.access_type
        }))
        
        console.log('Processed history:', this.history)
        this.totalItems = this.history.length
      } catch (error) {
        console.error('접속 이력 조회 실패:', error)
        this.$toast?.error('접속 이력을 불러오는 중 오류가 발생했습니다.')
      } finally {
        this.loading = false
      }
    },

    formatDate(dateString) {
      if (!dateString) return '-'
      const date = new Date(dateString)
      return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      })
    },

    getAccessTypeText(accessType) {
      const types = {
        1: '로그인',
        2: '로그아웃'
      }
      return types[accessType] || '알 수 없음'
    },

    handleSearch() {
      // 필터링은 computed의 filteredHistory에서 자동 처리
    },

    handleFilter() {
      // 필터링은 computed의 filteredHistory에서 자동 처리
    },

    handleDateChange() {
      this.dateMenu = false
    },

    getStatusColor(status) {
      const colors = {
        1: 'success',
        2: 'error'
      }
      return colors[status] || 'grey'
    }
  }
}
</script>

<style lang="scss" scoped>
.user-history {
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
    }
  }
}
</style> 
