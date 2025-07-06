<!-- eslint-disable vue/multi-word-component-names -->
<template>
  <div class="event-report">
    <v-container>
      <v-card>
        <v-card-title>보고서 생성</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6">
              <v-select
                v-model="selectedVideo"
                :items="videoOptions"
                label="영상 선택"
                outlined
                dense
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="selectedPeriod"
                :items="periodOptions"
                label="기간 선택"
                outlined
                dense
              />
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" class="text-center">
              <v-btn
                color="secondary"
                @click="openReportPopup"
              >
                보고서 생성
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <v-dialog
        v-model="showReportDialog"
        width="1000"
        persistent
      >
        <v-card class="report-popup">
          <v-card-title class="report-title">
            <span>수자원공사 댐 현황 보고서</span>
            <v-spacer></v-spacer>
            <v-btn
              icon
              @click="showReportDialog = false"
            >
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-card-title>
          
          <v-card-text class="report-content">
            <div class="report-data">
              <h2>{{ selectedVideo }} 분석 보고서</h2>
              <p>기간: {{ getReportPeriod }}</p>
            </div>
          </v-card-text>

          <v-card-actions class="report-actions">
            <v-spacer></v-spacer>
            <v-btn
              color="grey"
              text
              class="mr-3"
              @click="showReportDialog = false"
            >
              <v-icon left>mdi-close</v-icon>
              닫기
            </v-btn>
            <v-btn
              color="secondary"
              @click="printReport"
            >
              <v-icon left>mdi-printer</v-icon>
              <span>보고서 출력</span>
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-container>
  </div>
</template>

<script>
export default {
  name: 'EventReport',
  data() {
    return {
      selectedVideo: '영상1',
      selectedPeriod: '일별',
      showReportDialog: false,
      videoOptions: ['영상1', '영상2', '영상3', '영상4'],
      periodOptions: ['일별', '주별', '월별']
    }
  },

  computed: {
    getReportPeriod() {
      const today = new Date()
      let startDate = new Date()
      
      switch (this.selectedPeriod) {
        case '일별':
          return today.toLocaleDateString()
        case '주별':
          startDate.setDate(today.getDate() - 7)
          return `${startDate.toLocaleDateString()} ~ ${today.toLocaleDateString()}`
        case '월별':
          startDate.setMonth(today.getMonth() - 1)
          return `${startDate.toLocaleDateString()} ~ ${today.toLocaleDateString()}`
        default:
          return today.toLocaleDateString()
      }
    }
  },

  methods: {
    openReportPopup() {
      this.showReportDialog = true
    },

    printReport() {
      window.print()
    }
  }
}
</script>

<style lang="scss" scoped>
.event-report {
  padding: 20px;

  .report-popup {
    background-color: white !important;
    color: #333;

    .report-title {
      background-color: #f5f5f5;
      border-bottom: 1px solid #ddd;
      padding: 16px;
      font-size: 1.5rem;
      font-weight: bold;
    }

    .report-content {
      padding: 24px;
      min-height: 600px;

      .report-data {
        h2 {
          color: #333;
          margin-bottom: 20px;
        }

        p {
          color: #666;
          margin-bottom: 16px;
        }
      }
    }

    .report-actions {
      border-top: 1px solid #ddd;
      padding: 16px;
    }
  }
}

@media print {
  .v-btn,
  .v-card-actions {
    display: none !important;
  }

  .report-content {
    padding: 20px !important;
  }

  .report-popup {
    box-shadow: none !important;
  }
}
</style> 
