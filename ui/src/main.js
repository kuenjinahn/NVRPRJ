import Vue from 'vue';
import App from '@/App.vue';
import router from '@/router';
import store from '@/store';
import vuetify from '@/plugins/vuetify';
import '@/registerServiceWorker';

import '@/assets/css/tailwind.css';
import '@/assets/css/theme.css';
import '@/assets/css/main.css';

import 'vue-toastification/dist/index.css';
import 'xterm/css/xterm.css';

import permission from '@/mixins/permission.mixin';

import { i18n } from '@/i18n';
import Loader from '@/components/loader.vue';

import Toast from 'vue-toastification';
import ToastOptions from '@/common/toast.defaults.js';

import socket from '@/common/socket-instance';
import VueSocketIOExt from 'vue-socket.io-extended';

import ECharts from 'vue-echarts';
import 'echarts';

Vue.component('v-chart', ECharts);

Vue.use(Toast, ToastOptions);
Vue.use(VueSocketIOExt, socket, { store });

Vue.component('Loader', Loader);

Vue.mixin(permission);

// 글로벌 사이드바 함수들
Vue.prototype.$sidebar = {
  open() { bus.$emit('sidebarOpen'); },
  close() { bus.$emit('sidebarClose'); },
  toggle() { bus.$emit('sidebarToggle'); },
  setState(state) { bus.$emit('sidebarSetState', state); }
};

Vue.config.productionTip = false;

const bus = new Vue();

const app = new Vue({
  router,
  store,
  vuetify,
  i18n: i18n,
  render: (h) => h(App),
}).$mount('#app');

export { app, bus };
