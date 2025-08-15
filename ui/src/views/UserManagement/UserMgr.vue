<template lang="pug">
.user-management
  v-container(fluid)
    v-row
      v-col(cols="12")
        .tw-flex.tw-justify-between.tw-items-center
          .tw-flex.tw-items-center
            .tab-bar-container.tw-flex.tw-rounded-lg
              v-btn.tab-btn(
                :color="activeView === 'list' ? 'var(--cui-primary)' : 'var(--cui-text-muted)'"
                @click="activeView = 'list'"
                text
                height="75"
                width="200"
              )
                v-icon.tw-mr-2(size="24") {{ icons['mdiAccountGroup'] }}
                span 사용자 리스트

    
    v-row
      v-col(cols="12")
        transition(name="fade" mode="out-in")
          component(
            :is="activeView === 'list' ? 'UserList' : 'UserHistory'"
            :key="activeView"
          )
</template>

<script>
import UserList from './UserList.vue'
import UserHistory from './UserHistory.vue'
import { 
  mdiAccountGroup, 
  mdiHistory, 
  mdiPlus
} from '@mdi/js';
export default {
  name: 'UserMgr',
  
  components: {
    UserList,
    UserHistory
  },

  data: () => ({
    icons: {
      mdiAccountGroup,
      mdiHistory,
      mdiPlus
    },
    activeView: 'list'
  }),

  methods: {
    openAddUserDialog() {
      // 사용자 추가 다이얼로그 로직
      console.log('Open add user dialog')
    }
  }
}
</script>

<style lang="scss" scoped>
.user-management {
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

  .add-user-btn {
    margin-right: 16px;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style> 

