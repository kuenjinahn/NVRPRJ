<!-- eslint-disable vue/multi-word-component-names -->
<template lang="pug">
.recording-mgr
  v-container(fluid)
    v-row
      v-col(cols="12")
        
        .tw-flex.tw-justify-between.tw-items-center
          .tab-bar-container.tw-flex.tw-rounded-lg.tw-bg-gray-800.tw-p-1
            .tab-item.tw-px-4.tw-py-2.tw-cursor-pointer.tw-flex.tw-items-center.tw-transition-all(
              :class="currentTab === 'compare' ? 'tw-bg-gray-700 tw-shadow-sm tw-text-gray-200' : 'tw-text-gray-400'"
              @click="changeTab('compare')"
            )
              v-icon.tw-mr-2(size="24") {{ icons['mdiPlayCircle'] }}
              span 녹화비교
            .tab-item.tw-px-4.tw-py-2.tw-cursor-pointer.tw-flex.tw-items-center.tw-transition-all(
              :class="currentTab === 'schedule' ? 'tw-bg-gray-700 tw-shadow-sm tw-text-gray-200' : 'tw-text-gray-400'"
              @click="changeTab('schedule')"
            )
              v-icon.tw-mr-2(size="24") {{ icons['mdiFormatListBulleted'] }}
              span 녹화스케줄관리
        component(:is="currentComponent")
</template>

<script>
import { mdiPlayCircle, mdiFormatListBulleted, mdiCompareHorizontal } from '@mdi/js';
import RecodingSchedule from './RecodingSchedule.vue';
import RecodingCompare from './RecodingCompare.vue';
export default {
  name: 'RecodingMgr',

  components: {
    RecodingSchedule,
    RecodingCompare
  },

  data: () => ({
    icons: {
      mdiPlayCircle,
      mdiFormatListBulleted,
      mdiCompareHorizontal
    },
    currentTab: 'compare'
  }),

  async mounted() {
    // 컴포넌트가 마운트된 후 실행될 코드
  },

  methods: {
    changeTab(tab) {
      this.currentTab = tab;
    }
  },

  computed: {
    currentComponent() {
      return this.currentTab === 'schedule' ? 'RecodingSchedule' : 'RecodingCompare';
    }
  }
};
</script>

<style scoped>
.recording-mgr {
  padding: 20px;
}

.tab-bar-container {
  border: 1px solid rgba(var(--cui-bg-nav-border-rgb));
  width: 600px;
  background: var(--cui-bg-gray-800);
  padding: 1px;
  border-radius: 0.5rem;
}

.tab-item {
  border-radius: 6px;
  width: 300px;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 500;
  display: flex;
  align-items: center;
  height: 75px;
  padding: 12px 16px;
}

.tab-item.tw-bg-white {
  color: var(--cui-primary);
  background-color: var(--cui-bg-gray-700);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tab-item:hover {
  opacity: 0.9;
}

.tw-text-primary {
  color: var(--cui-primary) !important;
}

.tw-text-gray-600 {
  color: var(--cui-text-gray-400);
}

.v-icon {
  font-size: 20px;
  margin-right: 8px;
}
</style> 
