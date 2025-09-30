<template>
  <div class="sidebar-container">
    <v-navigation-drawer
      v-model="drawer"
      app
      :width="sidebarWidth"
      class="dashboard-sidebar"
      elevation="0"
      :permanent="true"
      style="max-height: 100vh !important;"
    >
   
    <!-- Header with Logo -->
    <div class="sidebar-header">
      <div class="logo-container">
        <v-img
          src="@/assets/img/logo.png"
          alt="Welcome to SDMS "
          width="30"
          height="65"
          class="logo-image"
          @click="moveFirstStart"
        />
        <span class="logo-text"></span>
      </div>
    </div>

    <!-- User Profile Section -->
    <div class="user-profile-section">
      <v-card class="user-card" elevation="0">
        <v-card-text class="pa-4">
          <div class="d-flex align-center">
            <v-avatar size="30" class="mr-3">
              <v-img src="@/assets/img/no_user.png" />
            </v-avatar>
            <div class="user-info">
              <div class="user-name">{{ userName }} 님</div>
            </div>
            <v-spacer />
                  <v-btn
                    @click="logout"
                    class="logout-btn"
                  >
                    <v-icon>{{ icons.mdiLogoutVariant }}</v-icon>
                  </v-btn>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Location Display -->
    <div class="location-section">
      <v-card class="location-card" elevation="0">
        <v-card-text class="pa-3 text-center">
          <div class="location-text">{{ weather.location }}</div>
        </v-card-text>
      </v-card>
      
    </div>

    <!-- Navigation Menu -->
    <v-list class="navigation-menu" dense>
      <v-list-item
        v-for="item in filteredNavigationItems"
        :key="item.name"
        :to="item.path"
        class="nav-item"
        active-class="nav-item-active"
      >
        <v-list-item-icon class="mr-3">
          <v-icon>{{ item.icon }}</v-icon>
        </v-list-item-icon>
        <v-list-item-content>
          <v-list-item-title>{{ item.title }}</v-list-item-title>
        </v-list-item-content>
      </v-list-item>
    </v-list>

    <!-- Footer Section -->
    <v-spacer />
    <div class="sidebar-footer">
      <div class="social-icons">
        <v-btn icon small class="social-btn">
          <v-icon>mdi-instagram</v-icon>
        </v-btn>
        <v-btn icon small class="social-btn">
          <v-icon>mdi-blog</v-icon>
        </v-btn>
        <v-btn
          v-if="showAdminButton"
          small
          outlined
          class="admin-btn"
          @click="goToAdmin"
        >
          <v-icon left>{{ icons.mdiAccount }}</v-icon>
          Admin
        </v-btn>
      </div>
      
      <div class="contact-info">
        <div class="contact-title">시스템문의</div>
        <div class="contact-detail">Tel. 000-0000-0000</div>
        <div class="contact-detail">E-Mail. 0000@daum.com</div>
      </div>
      
      <div class="copyright">
        Copyright © 0000. All rights reserved.
      </div>
    </div>
  </v-navigation-drawer>
    
    <!-- Sidebar Toggle Button - Outside sidebar -->
    <v-btn
      @click="toggleSidebar"
      :class="['sidebar-toggle-btn', { 'sidebar-closed': !drawer }]"
      icon
      fab
      small
      elevation="4"
    >
      <v-icon>{{ drawer ? icons.mdiChevronLeftCircle : icons.mdiChevronRightCircle }}</v-icon>
    </v-btn>
  </div>
</template>

<script>
import { getUser } from '@/api/users.api.js';
import { bus } from '@/main';
import { mdiChevronLeftCircle, mdiChevronRightCircle, mdiLogoutVariant, mdiAccount } from '@mdi/js';

export default {
  name: 'Sidebar',
  data() {
    return {
      drawer: true,
      sidebarWidth: 300,
      userName: 'system',
      userPermissionLevel: 2, // 기본값은 일반 사용자
      weather: {
        location: '수자원공사 섬진강댐'
      },
      icons: {
        mdiChevronLeftCircle,
        mdiChevronRightCircle,
        mdiLogoutVariant,
        mdiAccount
      },
      allNavigationItems: [
        {
          name: 'dashboard',
          title: '열화상카메라 모니터링',
          path: '/dashboard',
          icon: 'mdi-view-dashboard',
          permissionRequired: null // 모든 사용자 접근 가능
        },
        {
          name: 'alert-status',
          title: '열화상이미지 분석결과',
          path: '/alerts/status',
          icon: 'mdi-view-dashboard',
          permissionRequired: null // 모든 사용자 접근 가능
        },
        {
          name: 'recordings',
          title: '녹화영상관리',
          path: '/recordings',
          icon: 'mdi-record',
          permissionRequired: null // 모든 사용자 접근 가능
        },
        {
          name: 'cameras',
          title: '카메라 관리',
          path: '/cameras',
          icon: 'mdi-cctv',
          permissionRequired: 1 // 관리자만 접근 가능
        },
        {
          name: 'users',
          title: '사용자관리',
          path: '/user-management',
          icon: 'mdi-account-group',
          permissionRequired: 1 // 관리자만 접근 가능
        },
        {
          name: 'events',
          title: '설정',
          path: '/events',
          icon: 'mdi-account-group',
          permissionRequired: 1 // 관리자만 접근 가능
        }
      ]
    };
  },
  computed: {
    filteredNavigationItems() {
      return this.allNavigationItems.filter(item => {
        // permissionRequired가 null이면 모든 사용자 접근 가능
        if (item.permissionRequired === null) {
          return true;
        }
        // permissionRequired가 있으면 해당 권한 레벨 이상만 접근 가능
        return this.userPermissionLevel == item.permissionRequired;
      });
    },
    showAdminButton() {
      return this.userPermissionLevel === 1;
    }
  },
  
  async mounted() {
    await this.loadUserInfo();
    await this.loadWeatherLocation();
    // 사이드바 표시 상태 설정
    this.drawer = true;

    // bus 이벤트 리스너 등록
    bus.$on('sidebarOpen', this.openSidebar);
    bus.$on('sidebarClose', this.closeSidebar);
    bus.$on('sidebarToggle', this.toggleSidebar);
    bus.$on('sidebarSetState', this.setSidebarState);
  },
  methods: {
    moveFirstStart() {
      this.$router.push('/first-start');
    },
    async loadUserInfo() {
      // 사용자 정보 로드 로직
      const user = await getUser(this.$store.state.auth.user.id);
      if (user.data) {
        this.userName = user.data.userName || 'system';
        this.userPermissionLevel = user.data.permissionLevel || 2;
      }
    },
    async loadWeatherLocation() {
      try {
        // 기존 날씨 위치 정보 로드 로직 활용
        const { getEventSetting } = await import('@/api/eventSetting.api.js');
        const data = await getEventSetting();
        if (data && data.system_json) {
          const system = JSON.parse(data.system_json);
          this.weather.location = system.location_info || system.address || '수자원공사 섬진강댐';
        }
      } catch (error) {
        console.error('위치 정보를 불러오는데 실패했습니다:', error);
        this.weather.location = '수자원공사 섬진강댐';
      }
    },
    async logout() {
      await this.$store.dispatch('auth/logout');
      this.$router.push('/');
    },
    goToAdmin() {
      this.$router.push('/admin-result');
    },
    toggleSidebar() {
      this.drawer = !this.drawer;
      this.sidebarWidth = this.drawer ? 300 : 0;
      
      // 사이드바가 닫힐 때 transform을 사용하여 숨김
      const sidebar = document.querySelector('.dashboard-sidebar');
      if (sidebar) {
        if (!this.drawer) {
          sidebar.style.transform = 'translateX(-300px)';
        } else {
          sidebar.style.transform = 'translateX(0)';
        }
      }
      
      // 사이드바 상태 변경을 다른 컴포넌트에 알림
      bus.$emit('sidebarToggled', this.drawer);
    },
    
    // 글로벌 함수들
    openSidebar() {
      if (!this.drawer) {
        this.toggleSidebar();
      }
    },
    
    closeSidebar() {
      if (this.drawer) {
        this.toggleSidebar();
      }
    },
    
    setSidebarState(state) {
      this.drawer = state;
      this.sidebarWidth = state ? 300 : 0;
      
      const sidebar = document.querySelector('.dashboard-sidebar');
      if (sidebar) {
        if (!state) {
          sidebar.style.transform = 'translateX(-300px)';
        } else {
          sidebar.style.transform = 'translateX(0)';
        }
      }
      
      bus.$emit('sidebarToggled', state);
    }
  }
};
</script>

<style lang="scss" scoped>
.sidebar-container {
  position: relative;
}

.dashboard-sidebar {
  background: #f3f5f6 !important;
  border-right: none !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  height: 100vh !important;
  z-index: 999 !important;
  transform: translateX(0) !important;
  transition: all 0.3s ease !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
  
  .sidebar-header {
    padding: 20px;
    border-bottom: 1px solid #f3f5f6;
    
    .logo-container {
      display: flex;
      align-items: center;
      transform: scale(0.8);
      transform-origin: center center;
      .logo-image {
        border-radius: 10%;
        background: #f3f5f6;
        padding: 8px;
      }
      
      .logo-text {
        margin-left: 12px;
        font-size: 18px;
        font-weight: 600;
        color: #232323;
      }
    }
  }
  
  .user-profile-section {
    padding: 0 16px 30px;
    width: 100% !important;
    .user-card {
      background-color: #ffffff !important;
      border-radius: 8px;
      
      .user-info {
        .user-name {
          font-weight: 500;
          color: #333;
        }
      }
      
      .logout-btn {
        color: #333 !important;
        background-color: transparent !important;
        min-width: 36px !important;
        min-height: 36px !important;
      
        &:hover {
          color: #1976d2 !important;
          background-color: rgba(25, 118, 210, 0.1) !important;
        }
        
        .v-icon {
          color: #333 !important;
          font-size: 20px !important;
        }
        
        &::before {
          background-color: transparent !important;
        }
      }
    }
  }
  
  .location-section {
    padding: 0 16px 30px;
    border-bottom: 1px solid #e0e0e0;
    
    .location-card {
      background-color: #3ac343 !important;
      border-radius: 8px;
      
      .location-text {
        font-weight: 500;
        color: #ffffff;
        font-size: 14px;
      }
    }
  }
  
  .navigation-menu {
    padding: 0 8px 120px 8px;
    background: #f3f5f6 !important;
    flex: 1 !important;
    .nav-item {
      margin: 4px 0;
      border-radius: 8px;
      color: #363636 !important;
      &:hover {
        background: #f5f5f5;
      }
      
      &.nav-item-active {
        background: #e3f2fd;
        color: #363636 !important;
        
        .v-icon {
          color: #1976d2;
        }
      }
      
      .v-list-item__icon {
        margin-right: 12px;
      }
      
      .v-list-item__title {
        font-size: 14px;
        font-weight: 500;
      }
    }
  }
  
  .sidebar-footer {
    padding: 16px;
    border-top: 1px solid #e0e0e0;
    position: absolute !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    background: #f3f5f6 !important;
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
    
    .social-icons {
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 16px;
      flex-direction: column;
      
      .social-btn {
        margin: 0 4px;
        color: #666;
        
        &:hover {
          color: #1976d2;
        }
      }
      
      .admin-btn {
          font-size: 12px;
          height: 28px;
          text-align: center;
          margin-top: 8px;
        }
    }
    
    .contact-info {
      text-align: left;
      margin-bottom: 12px;
      
      .contact-title {
        font-weight: 600;
        color: #333;
        font-size: 14px;
        margin-bottom: 4px;
      }
      
      .contact-detail {
        color: #666;
        font-size: 12px;
        line-height: 1.4;
      }
    }
    
    .copyright {
      text-align: left;
      color: #999;
      font-size: 11px;
      line-height: 1.3;
      margin-bottom: 0 !important;
      padding-bottom: 16px !important;
    }
  }
}

// 반응형 디자인
@media (max-width: 960px) {
  .dashboard-sidebar {
    transform: translateX(-300px);
  }
  
  .dashboard-sidebar.show {
    transform: translateX(0);
  }
  
  .sidebar-toggle-btn {
    left: 0 !important;
    border-radius: 0 24px 24px 0 !important;
  }
  
  .sidebar-toggle-btn.sidebar-closed {
  left: 0 !important;
  border-radius: 0 24px 24px 0 !important;
}

// 사이드바가 닫힐 때 메인 콘텐츠 영역 조정
:global(.content) {
  transition: margin-left 0.3s ease !important;
}

:global(.content.sidebar-closed) {
  margin-left: 0 !important;
  width: 100vw !important;
  min-width: 100vw !important;
  max-width: 100vw !important;
}
}

@media (max-width: 768px) {
  .dashboard-sidebar {
    width: 280px !important;
  }
}

@media (max-width: 480px) {
  .dashboard-sidebar {
    width: 260px !important;
  }
}

.sidebar-toggle-btn {
  position: fixed !important;
  left: 300px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  z-index: 1000 !important;
  background: white !important;
  color: #666 !important;
  transition: left 0.3s ease !important;
  width: 24px !important;
  height: 48px !important;
  min-width: 24px !important;
  min-height: 48px !important;
  border-radius: 0 24px 24px 0 !important;
  box-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2) !important;
  border: none !important;
  
  &:hover {
    background: #f5f5f5 !important;
    color: #333 !important;
  }
  
  .v-icon {
    font-size: 16px !important;
    color: #666 !important;
  }
  
  &:hover .v-icon {
    color: #333 !important;
  }
}

.sidebar-toggle-btn.sidebar-closed {
  left: 0 !important;
}
</style>
