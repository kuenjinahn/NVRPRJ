<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.recording-mgr
  v-container(fluid)
    v-row
      v-col(cols="12")
        .tw-flex.tw-justify-between.tw-items-center
          .tw-flex.tw-items-center
            .tab-bar-container.tw-flex.tw-rounded-lg
              v-btn.tab-btn(
                :color="currentTab === 'setting' ? 'var(--cui-primary)' : 'var(--cui-text-muted)'"
                @click="changeTab('setting')"
                text
                height="75"
                width="200"
              )
                v-icon.tw-mr-2(size="24") {{ icons['mdiFormatListBulleted'] }}
                span 시스템 설정
        router-view
</template>

<script>
import { 
  mdiPlayCircle, 
  mdiFormatListBulleted, 
  mdiChartLine,
  mdiFileDocument,
  mdiMapMarkerRadius
} from '@mdi/js';

export default {
  name: 'EventgMgr',

  data: () => ({
    icons: {
      mdiPlayCircle,
      mdiFormatListBulleted,
      mdiChartLine,
      mdiFileDocument,
      mdiMapMarkerRadius
    },
    currentTab: 'setting'
  }),

  async mounted() {
    // 현재 라우트에 따라 탭 설정
    const path = this.$route.path.split('/').pop();
    if (path) {
      this.currentTab = path;
    }
  },

  methods: {
    changeTab(tab) {
      this.currentTab = tab;
      this.$router.push(`/events/${tab}`);
    }
  },

  watch: {
    '$route'(to) {
      const path = to.path.split('/').pop();
      if (path) {
        this.currentTab = path;
      }
    }
  }
};
</script>

<style lang="scss" scoped>
.recording-mgr {
  padding: 20px;
}

.tab-bar-container {
  border: 1px solid var(--cui-border-color);
  background: var(--cui-bg-card);
  padding: 4px;
  border-radius: 12px;
  display: flex;
  gap: 4px;
}

.tab-btn {
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 16px !important;
  letter-spacing: normal !important;
  transition: all 0.2s ease !important;

  &:hover {
    background: rgba(var(--cui-primary-rgb), 0.1) !important;
  }

  &.v-btn--active {
    background: rgba(var(--cui-primary-rgb), 0.15) !important;
    
    .v-icon {
      color: var(--cui-primary) !important;
    }
  }

  .v-icon {
    transition: color 0.2s ease;
  }
}
</style> 
