<template lang="pug">
.tw-flex.tw-flex-col.tw-overflow-y-auto.main-navi.main-navi-show
  .tw-flex.tw-flex-row.tw-justify-center.tw-items-center
    .logo.tw-cursor-pointer.tw-flex.tw-items-center.tw-justify-center(@click="$router.push('/dashboard')")
      img.tw-w-full.tw-h-full.tw-object-contain(:src="require('@/assets/img/logo.png')" title="NVR" alt="camera.ui")
  
  .tw-flex.tw-flex-col.tw-h-full.tw-items-center.tw-pt-6(key="nav")
    .tw-flex.tw-items-center.tw-justify-center.sidebar-nav-items(v-for="menu in additionalMenus" :key="menu.name")
      v-btn.tw-justify-center.sidebar-nav-item(
        @click="handleMenuClick(menu)"
        :class="menu.route && $route.path.startsWith(menu.route) ? 'sidebar-nav-item-active v-btn--active' : ''"
        plain 
        block 
        tile
      )
        v-icon(height="28px" width="28px") {{ icons[menu.icon] }}
        span.sidebar-nav-item-text {{ menu.name }}
    
    .tw-mt-auto.tw-mb-4.tw-flex.tw-justify-center.tw-w-full
      v-btn.tw-justify-center.sidebar-nav-item.logout-btn(@click="signout" plain block tile)
        v-icon(height="28px" width="28px") {{ icons['mdi-logout'] }}
        span.sidebar-nav-item-text {{ $t('signout') }}

  v-dialog(
    v-model="dialog"
    max-width="400"
    persistent
  )
    v-card.preparing-dialog
      v-card-title.dialog-title
        v-icon.mr-2(color="var(--cui-primary)" size="28") {{ icons['mdi-alert-circle'] }}
        span 준비중
      v-card-text.dialog-content
        .message-text 현재 기능 준비중입니다.
        .sub-message-text 빠른 시일 내에 서비스하도록 하겠습니다.
      v-card-actions.dialog-actions
        v-spacer
        v-btn(
          color="var(--cui-primary)"
          text
          @click="dialog = false"
        ) 확인
</template>

<script>
import { mdiViewDashboard, mdiLogoutVariant, mdiCctv, mdiVideo, mdiRuler, mdiBell, mdiAccountGroup } from '@mdi/js';
import { bus } from '@/main';
import { routes } from '@/router';

export default {
  name: 'Sidebar',

  data() {
    return {
      icons: {
        'mdi-view-dashboard': mdiViewDashboard,
        'mdi-logout': mdiLogoutVariant,
        'mdi-video': mdiCctv,
        'mdi-record': mdiVideo,
        'mdi-ruler': mdiRuler,
        'mdi-alert': mdiBell,
        'mdi-account': mdiAccountGroup,
      },
      dialog: false,
      additionalMenus: [
        { name: '대시보드', icon: 'mdi-view-dashboard', route: '/dashboard' },
        { name: '영상관리', icon: 'mdi-video', route: '/cameras' },
        { name: '녹화관리', icon: 'mdi-record', route: '/recordings' },
        { name: '계측관리', icon: 'mdi-ruler', route: '/events' },
        { name: '경보관리', icon: 'mdi-alert', route: '/alerts' },
        { name: '사용자관리', icon: 'mdi-account', route: '/user-management' },
      ],
      navigation: routes
        .map((route) => {
          if (route.meta.navigation) {
            return {
              name: route.name,
              to: route.path,
              redirect: route.meta.redirectTo,
              ...route.meta.navigation,
              ...route.meta.auth,
            };
          }
        })
        .filter((route) => route),
    };
  },

  computed: {
    filteredNavigation() {
      return this.navigation.filter(item => item.name === 'carames').map(item => ({
        ...item,
        name: '영상관리'
      }));
    },
  },

  methods: {
    hideNavi() {
      bus.$emit('showOverlay', false);
      bus.$emit('extendSidebar', true);
    },
    async signout() {
      await this.$store.dispatch('auth/logout');
      this.$router.push('/');
    },
    showPreparingMessage() {
      this.dialog = true;
    },
    handleMenuClick(menu) {
      const preparingMenus = [];
      if (preparingMenus.includes(menu.name)) {
        this.showPreparingMessage();
      } else if (menu.route) {
        this.$router.push(menu.route);
      }
    },
  },
};
</script>

<style scoped>
.main-navi {
  background: rgba(var(--cui-bg-nav-rgb));
  border-right: 1px solid rgba(var(--cui-bg-nav-border-rgb));
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  width: 227px;
  min-width: 227px;
  max-width: 227px;
  transition: 0.2s all;
  z-index: 999;
  scrollbar-width: none;
  -ms-overflow-style: none;
  padding-top: 10px;
}

.main-navi::-webkit-scrollbar {
  width: 0px;
  display: none;
}

.main-navi-show {
  width: 227px;
  min-width: 227px;
  margin-left: 0 !important;
  transform: translateX(0);
}

.logo {
  width: 187px;
  height: 78px;
  transition: 0.2s all;
  padding: 8px;
  display: flex;
  justify-content: center;
}

.sidebar-nav-items {
  height: 80px !important;
  width: 100%;
  display: flex;
  justify-content: flex-start;
  padding-left: 20px;
}

.sidebar-nav-item {
  color: rgba(255, 255, 255, 0.6);
  transition: 0.2s all;
  border-radius: 12px !important;
  height: 80px !important;
  width: 191px !important;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  flex-direction: row;
  padding: 0 20px;
  margin-left: 0 !important;
}

.sidebar-nav-item-active,
.sidebar-nav-item:hover {
  color: rgba(255, 255, 255, 1);
}

.sidebar-nav-item-text {
  font-weight: 600 !important;
  font-size: 16px !important;
  text-transform: none !important;
  letter-spacing: normal !important;
  margin-left: 12px;
}

.sidebar-nav-item v-icon {
  font-size: 28px !important;
}

.logout-btn {
  margin-top: auto;
  color: rgba(255, 255, 255, 0.6) !important;
  width: 191px !important;
  height: 80px !important;
  flex-direction: row;
  padding: 0 20px;
}

.logout-btn:hover {
  color: rgba(255, 255, 255, 1) !important;
}

.tw-mt-auto.tw-mb-4.tw-flex.tw-justify-center.tw-w-full {
  padding-left: 20px;
  justify-content: flex-start !important;
}

@media (max-width: 960px) {
  .main-navi {
    transform: translateX(-227px);
  }

  .main-navi-show {
    transform: translateX(0);
  }
}

.preparing-dialog {
  border-radius: 12px !important;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1) !important;
}

.dialog-title {
  background-color: #f8f9fa;
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
  padding: 20px 24px !important;
  font-size: 1.25rem !important;
  font-weight: 600 !important;
  color: #2c3e50;
}

.dialog-content {
  padding: 24px !important;
}

.message-text {
  font-size: 1.1rem;
  font-weight: 500;
  color: #2c3e50;
  margin-bottom: 8px;
}

.sub-message-text {
  font-size: 0.95rem;
  color: #6c757d;
}

.dialog-actions {
  padding: 16px 24px !important;
  border-top: 1px solid #edf2f7;
}

.v-btn {
  text-transform: none !important;
  font-weight: 600 !important;
  font-size: 0.95rem !important;
  padding: 0 20px !important;
}
</style>
