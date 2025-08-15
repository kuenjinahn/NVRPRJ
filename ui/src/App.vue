<template lang="pug">
v-app.app(:style="$route.name === 'Camview' ? 'background: #121212 !important' : ''")

  audio#soundFx
    source(src="@/assets/sounds/notification.mp3" type="audio/mpeg")

  button.add-button(style="display: none;") {{ $t('add_to_homescreen') }}
  
  transition(name='fade' mode='out-in')
    Loader(v-if="loading")

    div(v-else)
      BackToTop
      
      .tw-flex
        Sidebar(v-if="$route.meta.config && $route.meta.config.showSidebar")
        
        .overlay(v-if="showOverlay")

        v-main.tw-relative(:class="getMainClasses()")
          .router-container.tw-relative(:class="$route.meta.config && $route.meta.config.fixedNavbar ? 'fixed-navbar' : ''")
            transition(name='fade' mode='out-in')
              router-view

      Footer(v-if="$route.meta.config && $route.meta.config.showFooter")
      
</template>

<script>
import { bus } from '@/main';

import BackToTop from '@/components/backtotop.vue';
import Footer from '@/components/footer.vue';
import Navbar from '@/components/navbar.vue';
import Sidebar from '@/components/sidebar.vue';

import update from '@/mixins/update';

export default {
  name: 'App',

  components: {
    BackToTop,
    Footer,
    Navbar,
    Sidebar,
  },

  mixins: [update],

  data: () => ({
    extendSidebar: false,
    loading: true,
    showOverlay: false,
    sidebarOpen: true,
  }),

  watch: {
    '$route.path': {
      handler() {
        this.showOverlay = false;
      },
    },
  },

  mounted() {
    bus.$on('showOverlay', this.triggerOverlay);
    bus.$on('extendSidebar', this.triggerSidebar);
    bus.$on('sidebarToggled', this.handleSidebarToggle);

    setTimeout(() => {
      this.loading = false;
    }, 2250);
  },

  beforeDestroy() {
    bus.$off('showOverlay', this.triggerOverlay);
    bus.$off('extendSidebar', this.triggerSidebar);
    bus.$off('sidebarToggled', this.handleSidebarToggle);
  },

  updated() {
    bus.$emit('extendSidebarQuery');
  },

  methods: {
    triggerSidebar(state) {
      this.extendSidebar = state;
    },
    triggerOverlay(state) {
      this.showOverlay = state;
    },
    handleSidebarToggle(isOpen) {
      this.sidebarOpen = isOpen;
    },
    getMainClasses() {
      const classes = [];
      
      if (this.$route.name !== 'Login' && this.$route.name !== 'Start' && this.$route.name !== '404' && 
          (this.$route.meta.config && !this.$route.meta.config.showMinifiedNavbar && this.$route.meta.config.showSidebar)) {
        classes.push('content');
      }
      
      if (this.extendSidebar) {
        classes.push('extended-sidebar');
      }
      
      if (!this.sidebarOpen) {
        classes.push('sidebar-closed');
      }
      
      return classes.join(' ');
    },
  },
};
</script>

<style>
.page-loading {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
}

.Vue-Toastification__toast {
  margin-bottom: calc(env(safe-area-inset-top, -5px) + 5px) !important;
}

@media (max-width: 600px) {
  .Vue-Toastification__toast {
    width: 80% !important;
    margin: 0 auto !important;
    margin-bottom: clamp(1rem, env(safe-area-inset-bottom, 1rem), env(safe-area-inset-bottom, 1rem)) !important;
  }
}
</style>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition-duration: 0.1s;
  transition-property: all;
  transition-timing-function: ease-in-out;
  transition-delay: 0;
}

.fade-enter,
.fade-leave-active {
  opacity: 0;
}

.app {
  color: rgba(var(--cui-text-default-rgb)) !important;
  background: rgba(var(--cui-bg-default-rgb)) !important;
}

.content {
  margin-left: 300px;
  width: calc(100vw - 300px);
  min-width: calc(100vw - 300px);
  max-width: calc(100vw - 300px);
  padding-left: 0 !important;
  transition: margin-left 0.3s ease, width 0.3s ease, min-width 0.3s ease, max-width 0.3s ease;
}

.content.sidebar-closed {
  margin-left: 0 !important;
  width: 100vw !important;
  min-width: 100vw !important;
  max-width: 100vw !important;
}

.overlay {
  background-color: #000 !important;
  border-color: #000 !important;
  opacity: 0.6;
  z-index: 100;
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  display: none;
}

.router-container {
  width: 100%;
  min-height: calc(100vh - 64px - 44px - env(safe-area-inset-top, 0px));
}

.extended-sidebar {
  margin-left: 300px;
  width: calc(100vw - 300px);
  min-width: calc(100vw - 300px);
  max-width: calc(100vw - 300px);
  padding-left: 0 !important;
}

.fixed-navbar {
  margin-top: 0px;
}

.add-button {
  position: fixed;
  bottom: 50px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--cui-primary);
  padding: 10px;
  border-radius: 10px;
  color: #ffffff;
  z-index: 1;
}

div>>>.vib-hideable {
  transition: opacity 0.1s ease;
}

div>>>.vib-hidden {
  opacity: 10;
}

div>>>.vib-content {
  width: 100%;
  max-width: 800px;
  padding-left: 0.75rem !important;
  padding-right: 0.75rem !important;
}

div>>>.vib-close {
  margin-top: env(safe-area-inset-top, 0px);
  margin-right: env(safe-area-inset-right, 0px);
}

div>>>.vib-arrow-right {
  margin-right: env(safe-area-inset-right, 0px);
}

div>>>.vib-arrow-left {
  margin-left: env(safe-area-inset-left, 0px);
}

div>>>.vib-footer {
  margin-bottom: env(safe-area-inset-bottom, 6px);
  padding-right: clamp(10px, env(safe-area-inset-right, 10px), env(safe-area-inset-right, 10px));
  padding-left: clamp(10px, env(safe-area-inset-right, 10px), env(safe-area-inset-right, 10px));
}

@media (max-width: 960px) {
  .overlay {
    display: block;
  }

  .content {
    margin-left: 0 !important;
    width: 100vw;
    min-width: 100vw;
    max-width: 100vw;
  }

  .extended-sidebar {
    margin-left: 0 !important;
    width: 100vw;
    min-width: 100vw;
    max-width: 100vw;
  }
}
</style>
