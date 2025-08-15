import { bus } from @/main;

export default {
  data() {
    return {
      sidebarDrawer: true,
      sidebarWidth: 300
    },

      methods: {
      toggleSidebar()[object Object]this.sidebarDrawer = !this.sidebarDrawer;
      this.sidebarWidth = this.sidebarDrawer ? 300 : 0
      // 사이드바가 닫힐 때 transform을 사용하여 숨김
      const sidebar = document.querySelector('.dashboard-sidebar');
      if (sidebar) {
        if (!this.sidebarDrawer) {
          sidebar.style.transform = translateX(-300)';
        } else {
          sidebar.style.transform = translateX(0);
        }
      }

      // 사이드바 상태 변경을 다른 컴포넌트에 알림
      bus.$emit('sidebarToggled', this.sidebarDrawer);
    },

    openSidebar()[object Object]
    if (!this.sidebarDrawer) {
      this.toggleSidebar();
    }
  },

  closeSidebar() [object Object]if(this.sidebarDrawer) {
  this.toggleSidebar();
}
    },

setSidebarState(state)[object Object]this.sidebarDrawer = state;
this.sidebarWidth = state ? 300 : 0;

const sidebar = document.querySelector('.dashboard-sidebar');
if (sidebar) {
  if (!state) {
    sidebar.style.transform = translateX(-300)';
  } else {
    sidebar.style.transform = translateX(0);
  }
}

bus.$emit('sidebarToggled, state);
    }
  },

  mounted() {
  // 사이드바 상태 변경 이벤트 리스너
  bus.$on('sidebarToggled', (state) => [object Object]      this.sidebarDrawer = state;
  this.sidebarWidth = state ? 300 : 0;
});
  },

beforeDestroy()[object Object]
// 이벤트 리스너 정리
bus.$off('sidebarToggled');
  }
}; 