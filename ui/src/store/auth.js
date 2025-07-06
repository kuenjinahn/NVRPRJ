import { login, logout } from '@/api/auth.api';
import socket from '@/common/socket-instance';
import SerializeService from '@/common/serialize-token';

const user = JSON.parse(localStorage.getItem('user'));
const userImg = localStorage.getItem('userImg');
const serializedUser = SerializeService.serialize(user);

const initialState = user
  ? {
    status: { loggedIn: true },
    user: {
      ...serializedUser,
      photo: userImg ? userImg : serializedUser.photo,
    },
  }
  : { status: { loggedIn: false }, user: null };

const unsubscribeUser = () => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then((reg) => {
      reg.pushManager.getSubscription().then((subscription) => {
        if (subscription) {
          subscription.unsubscribe();
        }
      });
    });
  }
};

export const auth = {
  namespaced: true,
  state: initialState,
  actions: {
    async login({ commit }, user) {
      try {
        const response = await login(user);
        commit('loginSuccess', response.data);
        return Promise.resolve();
      } catch (error) {
        commit('loginFailure');
        return Promise.reject(error);
      }
    },
    async logout({ commit }) {
      try {
        await logout();
      } catch (err) {
        console.log(err);
      }
      commit('logout');
      return Promise.resolve();
    },
    updateUserImg({ commit }, imgPath) {
      commit('updateImg', imgPath);
    },
  },
  mutations: {
    loginSuccess(state, user) {
      if (user.permissionLevel && !Array.isArray(user.permissionLevel)) {
        user.permissionLevel = [user.permissionLevel];
      }
      if (!user.permissionLevel) {
        user.permissionLevel = [];
      }
      // 모든 주요 권한 자동 부여
      const ALL_PERMISSIONS = [
        'cameras:access',
        'camview:access',
        'dashboard:access',
        'notifications:access',
        'recordings:access',
        'settings:access',
        'settings:cameras:access',
        'settings:camview:access',
        'settings:dashboard:access',
        'settings:general:access',
        'settings:profile:access',
        'notifications:edit',
        'recordings:edit',
        'settings:edit',
        'settings:cameras:edit',
        'settings:camview:edit',
        'settings:dashboard:edit',
        'settings:general:edit',
        'settings:notifications:edit',
        'settings:profile:edit',
        'settings:recordings:edit',
        'admin',
        'users:edit'
      ];
      ALL_PERMISSIONS.forEach((perm) => {
        if (!user.permissionLevel.includes(perm)) {
          user.permissionLevel.push(perm);
        }
      });
      console.log('loginSuccess user:', user);
      if (!user.access_token) {
        throw new Error('로그인 응답에 access_token이 없습니다. 백엔드 응답 구조를 확인하세요.');
      }
      localStorage.setItem('user', JSON.stringify(user));
      state.status.loggedIn = true;
      state.user = SerializeService.serialize(user);
    },
    loginFailure(state) {
      localStorage.removeItem('user');
      localStorage.removeItem('userImg');
      localStorage.removeItem('lastPage');
      state.status.loggedIn = false;
      state.user = null;

      socket.close();
      unsubscribeUser();
    },
    logout(state) {
      localStorage.removeItem('user');
      localStorage.removeItem('userImg');
      localStorage.removeItem('lastPage');
      state.status.loggedIn = false;
      state.user = null;

      socket.close();
      unsubscribeUser();
    },
    updateImg(state, imgPath) {
      localStorage.setItem('userImg', imgPath);
      state.user.photo = imgPath;
    },
  },
  getters: {
    loggedIn: (state) => {
      return state.status.loggedIn;
    },
    user: (state) => {
      return state.user;
    },
  },
};
