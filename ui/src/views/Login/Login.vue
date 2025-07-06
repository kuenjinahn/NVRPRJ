<template lang="pug">
.tw-w-full.tw-flex.tw-flex-col.tw-justify-center.tw-items-center(style="min-height: 100vh")
 
  .login
    .tw-flex.tw-flex-col.tw-p-0
      .login-header.tw-flex.tw-justify-between.tw-items-center
        .tw-block
          h2.tw-leading-10.tw-font-black {{ $t('스마트댐 모니터링 시스템') }}
          span.subtitle.tw-font-medium {{ $t(' ') }} 
            strong.text-primary
        .tw-ml-auto

      v-form.login-content.tw-mt-5(ref="form" v-model="valid" lazy-validation @submit.prevent="signin")
        
        span.login-input-label {{ $t('아이디') }}
        v-text-field.tw-mb-0.login-input.tw-text-white(
          required 
          v-model="user.userId" 
          :rules="rules.userId" 
          solo 
          background-color="rgba(var(--cui-menu-default-rgb), 1)" 
          color="var(--cui-primary)" 
          :label="$t('user')"
        )

        span.login-input-label {{ $t('패스워드') }}
        v-text-field.tw-mb-0.login-input(
          required 
          autocomplete="current-password" 
          v-model="user.password" 
          :rules="rules.password" 
          solo 
          background-color="rgba(var(--cui-menu-default-rgb), 1)" 
          color="var(--cui-primary)" 
          :label="$t('password')" 
          type="password"
        )
        
        v-btn.login-btn.tw-text-white.tw-mt-2(
          block 
          depressed 
          color="var(--cui-primary)" 
          height="48px" 
          type="submit"
        ) {{ $t('로그인') }}
              
  span.tw-text-xs.text-muted {{ $t('수자원공사') }} - v{{ $t('1.0') }}
</template>

<script>
import { version } from '../../../../package.json';
import { mdiEye, mdiEyeOff } from '@mdi/js';

import { getConfig } from '@/api/config.api';

export default {
  name: 'Login',

  data() {
    return {
      loading: false,
      loadRestart: false,

      icons: {
        mdiEye,
        mdiEyeOff,
      },

      showPassword: false,

      rules: {
        userId: [(v) => !!v || this.$t('userId_is_required')],
        password: [(v) => !!v || this.$t('password_is_required')],
      },

      user: {
        userId: 'akj',
        password: 'test123',
      },

      valid: true,

      moduleName: 'camera.ui',
      version: version,
    };
  },

  computed: {
    restarted() {
      return Boolean(localStorage.getItem('restarted') === 'true');
    },
    updated() {
      return Boolean(localStorage.getItem('updated') === 'true');
    },
    uiConfig() {
      return this.$store.state.config.ui;
    },
  },

  created() {
    this.loadRestart = this.restarted;

    this.moduleName = this.uiConfig?.env?.moduleName || 'camera.ui';
    this.version = this.uiConfig.version || version;
  },

  mounted() {
    if (this.restarted) {
      localStorage.setItem('restarted', false);
      window.location.reload(true);
    }
  },

  methods: {
    async signin() {
      this.loading = true;

      const valid = this.$refs.form.validate();

      if (valid) {
        try {
          await this.$store.dispatch('auth/login', { ...this.user });

          await getConfig();

          this.$router.push('/dashboard');
        } catch (err) {
          this.loading = false;
          console.log(err);

          if (err.response && (err.response.status === 401 || err.response.status === 403)) {
            this.$toast.error(this.$t('cannot_login'));
          } else {
            this.$toast.error(err.message);
          }
        }
      } else {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.login {
  width: 100%;
  max-width: 350px;
  margin: 10px;
  background: rgb(var(--cui-bg-card-rgb));
  border-radius: 4px;
  padding: 2rem;
}

.login-btn {
  text-transform: none;
  text-indent: unset;
  letter-spacing: unset;
  border-radius: 4px;
}

.login-input-label {
  font-size: 0.85rem;
  font-weight: 600;
}

@media (max-width: 400px) {
  .login {
    width: 90%;
    max-width: unset;
  }
}

@media (max-height: 500px) {
  .logo {
    display: none;
  }

  .login-header {
    margin-top: 0 !important;
  }

  .subtitle {
    display: none;
  }
}
</style>
